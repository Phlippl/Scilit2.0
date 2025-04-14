# Backend/services/pdf_processor.py
import os
import re
import logging
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time
import pytesseract
from PIL import Image
import io
import numpy as np
import gc
import psutil
from typing import Dict, List, Any, Optional, Union, Callable

# PyMuPDF import with error handling
try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF nicht gefunden. Bitte installieren: pip install PyMuPDF")

# spaCy import with lazy loading to improve startup time
nlp = None

def get_nlp():
    """Lazy-load spaCy model only when needed"""
    global nlp
    if nlp is None:
        import spacy
        try:
            nlp = spacy.load("de_core_news_sm")
            logging.info("Loaded spaCy model: de_core_news_sm")
        except OSError:
            try:
                nlp = spacy.load("en_core_web_sm")
                logging.info("Loaded spaCy model: en_core_web_sm")
            except OSError:
                logging.warning("No spaCy language model found. Using blank model.")
                nlp = spacy.blank("en")
    return nlp

# Configure logging
logger = logging.getLogger(__name__)

class PDFProcessor:
    """Optimierte Klasse für PDF-Verarbeitung mit verbesserter Performance und Fehlerbehandlung"""
    
    def __init__(self, max_workers=4, ocr_max_workers=2):
        # Thread-Pool für parallele Verarbeitung
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # OCR-Pool (Tesseract ist CPU-intensiv)
        self.ocr_executor = ThreadPoolExecutor(max_workers=ocr_max_workers)
        # Cache für bereits extrahierten Text
        self._text_cache = {}
        # Cache für bereits extrahierte Identifikatoren
        self._identifier_cache = {}
    
    def __del__(self):
        """Cleanup thread pools on deletion"""
        self.executor.shutdown(wait=False)
        self.ocr_executor.shutdown(wait=False)
    
    def extract_text_from_pdf(self, pdf_file, max_pages=0, perform_ocr=False, progress_callback=None):
        """
        Text aus einer PDF-Datei extrahieren mit verbessertem Page-Tracking und parallelem OCR
        
        Args:
            pdf_file: PDF-Datei (Dateipfad oder Bytes)
            max_pages: Maximale Seitenzahl (0 = alle)
            perform_ocr: OCR für Seiten mit wenig Text durchführen
            progress_callback: Optionale Callback-Funktion für Fortschrittsupdates
        
        Returns:
            dict: Ergebnis mit Text und detaillierten Seiteninformationen
        """
        # Check if we have this file in cache
        file_hash = None
        if isinstance(pdf_file, str) and os.path.exists(pdf_file):
            file_hash = f"{os.path.getsize(pdf_file)}_{os.path.getmtime(pdf_file)}"
            if file_hash in self._text_cache:
                logger.info(f"Using cached text for {pdf_file}")
                return self._text_cache[file_hash]
        
        try:
            # Create temporary file for bytes input
            if isinstance(pdf_file, bytes):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_file.write(pdf_file)
                temp_file.close()
                pdf_path = temp_file.name
            else:
                pdf_path = pdf_file
            
            # Open PDF
            doc = fitz.open(pdf_path)
            
            # Prepare result object
            result = {
                'text': '',
                'pages': [],
                'totalPages': len(doc),
                'processedPages': min(len(doc), max_pages) if max_pages > 0 else len(doc)
            }
            
            # Limit maximum paragraph size to prevent memory issues
            MAX_PARAGRAPH_SIZE = 10000  # 10K characters

            # Number of pages to process
            pages_to_process = result['processedPages']
            
            # List for OCR candidate pages (pages with little text)
            ocr_page_numbers = []
            
            # Process pages in batches for better memory management
            BATCH_SIZE = 10  # Process 10 pages at a time
            
            for batch_start in range(0, pages_to_process, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, pages_to_process)
                
                # Extract text from each page in batch
                for i in range(batch_start, batch_end):
                    page = doc[i]
                    
                    # Report progress
                    if progress_callback:
                        progress_callback(f"Processing page {i+1}/{pages_to_process}", 
                                        int(i/pages_to_process * 100))
                    
                    # Page metadata with page number
                    page_info = {
                        'pageNumber': i + 1,
                        'width': page.rect.width,
                        'height': page.rect.height,
                        'text': '',
                        'startPosition': len(result['text']), # Start position in total text
                    }
                    
                    # Extract text
                    page_text = page.get_text()
                    
                    # Split extremely large extracted text blocks
                    if len(page_text) > MAX_PARAGRAPH_SIZE:
                        # Use natural breaks like double newlines to split text
                        split_texts = re.split(r'\n\s*\n', page_text)
                        page_text = '\n\n'.join(split_texts)
                        
                    page_info['text'] = page_text
                    page_info['length'] = len(page_text)
                    
                    # Add to total text
                    result['text'] += page_text + ' '
                    
                    # Update end position
                    page_info['endPosition'] = len(result['text']) - 1
                    
                    # Check if page has little text -> OCR candidate
                    if perform_ocr and len(page_text.strip()) < 100:
                        ocr_page_numbers.append(i)
                    
                    result['pages'].append(page_info)
                
                # Force garbage collection after each batch
                gc.collect()

            # Perform OCR for pages with little text using thread pool
            if perform_ocr and ocr_page_numbers:
                if progress_callback:
                    progress_callback(f"Performing OCR on {len(ocr_page_numbers)} pages", 50)
                
                # Process OCR in parallel (max 5 pages at once to limit memory usage)
                for i in range(0, len(ocr_page_numbers), 5):
                    batch = ocr_page_numbers[i:i+5]
                    
                    # Process OCR for batch
                    ocr_futures = []
                    for page_num in batch:
                        future = self.ocr_executor.submit(self._perform_ocr_on_page, doc, page_num, 300)
                        ocr_futures.append(future)
                    
                    # Collect OCR results for this batch
                    for j, future in enumerate(ocr_futures):
                        try:
                            page_num, ocr_text = future.result()
                            # Convert from 0-based to 1-based page number for index
                            idx = page_num - 1
                            if idx < len(result['pages']):
                                # Update text
                                orig_text = result['pages'][idx]['text']
                                if not orig_text.strip():
                                    result['pages'][idx]['text'] = ocr_text
                                    # Update total text
                                    result['text'] = result['text'].replace(orig_text, ocr_text)
                                else:
                                    # Add text if original exists
                                    result['pages'][idx]['text'] += ' ' + ocr_text
                                    result['text'] += ' ' + ocr_text
                            
                            # Report progress
                            if progress_callback:
                                progress_callback(f"OCR processing: {i+j+1}/{len(ocr_page_numbers)}", 
                                                50 + int((i+j+1)/len(ocr_page_numbers) * 45))
                        except Exception as e:
                            logger.error(f"Error in OCR process: {e}")
                    
                    # Force garbage collection after each OCR batch
                    gc.collect()
            
            # Clean up
            doc.close()
            if isinstance(pdf_file, bytes) and os.path.exists(pdf_path):
                os.unlink(pdf_path)
            
            # Cache the result if we have a file hash
            if file_hash:
                self._text_cache[file_hash] = result
            
            # Final progress report
            if progress_callback:
                progress_callback("Text extraction complete", 100)
            
            return result
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            # Clean up on error
            if isinstance(pdf_file, bytes) and 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.unlink(pdf_path)
            raise
    
    @staticmethod
    def _perform_ocr_on_page(doc, page_idx, dpi=300):
        """
        OCR für eine einzelne Seite durchführen
        
        Args:
            doc: Offenes PyMuPDF-Dokument
            page_idx: Seitenindex (0-basiert)
            dpi: DPI für das Rendering
        
        Returns:
            tuple: (page_number, ocr_text)
        """
        try:
            if page_idx < 0 or page_idx >= len(doc):
                return page_idx + 1, ""
            
            # Seite rendern
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            
            # Als Bild speichern
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # OCR durchführen
            ocr_text = pytesseract.image_to_string(img)
            
            # Seitennummer (1-basiert) für das Ergebnis
            return page_idx + 1, ocr_text
        except Exception as e:
            logger.error(f"Error performing OCR on page {page_idx + 1}: {e}")
            return page_idx + 1, ""
    
    def extract_identifiers(self, text, cache_key=None):
        """
        DOI und ISBN aus Text extrahieren mit Caching
        
        Args:
            text: Text zum Durchsuchen
            cache_key: Optional key for caching
            
        Returns:
            dict: Gefundene Identifikatoren
        """
        # Check cache first
        if cache_key and cache_key in self._identifier_cache:
            return self._identifier_cache[cache_key]
            
        # Extract DOI and ISBN
        doi = self.extract_doi(text)
        isbn = self.extract_isbn(text)
        
        result = {'doi': doi, 'isbn': isbn}
        
        # Cache result if we have a key
        if cache_key:
            self._identifier_cache[cache_key] = result
            
        return result
    
    @staticmethod
    def extract_doi(text):
        """
        DOI aus Text mit Regex extrahieren
        
        Args:
            text: Text zum Durchsuchen
        
        Returns:
            str: Gefundene DOI oder None
        """
        if not text:
            return None
        
        # DOI Patterns (verbessert für besseres Matching)
        # Format: 10.XXXX/XXXXX
        doi_patterns = [
            r'\b(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b',
            r'\bDOI:\s*(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b',
            r'\bdoi\.org\/(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b'
        ]
        
        for pattern in doi_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches and matches.group(1):
                return matches.group(1)
        
        return None
    
    @staticmethod
    def extract_isbn(text):
        """
        ISBN aus Text mit Regex extrahieren
        
        Args:
            text: Text zum Durchsuchen
        
        Returns:
            str: Gefundene ISBN oder None
        """
        if not text:
            return None
        
        # ISBN Patterns für ISBN-10 und ISBN-13
        isbn_patterns = [
            r'\bISBN(?:-13)?[:\s]*(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # ISBN-13
            r'\bISBN(?:-10)?[:\s]*(\d[- ]?(?:\d[- ]?){8}[\dX])\b',   # ISBN-10
            r'\b(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # Bare ISBN-13
            r'\b(\d[- ]?(?:\d[- ]?){8}[\dX])\b'    # Bare ISBN-10
        ]
        
        for pattern in isbn_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches and matches.group(1):
                # Bindestriche und Leerzeichen entfernen
                return matches.group(1).replace('-', '').replace(' ', '')
        
        return None
    
    def chunk_text_with_pages(self, text, pages_info, chunk_size=1000, overlap_size=200):
        """
        Text in Chunks aufteilen mit Seitenverfolgung und Überlappung
        
        Args:
            text: Vollständiger Text
            pages_info: Liste mit Seiteninformationen einschließlich Start- und Endpositionen
            chunk_size: Zielchunkgröße in Zeichen
            overlap_size: Überlappungsgröße in Zeichen
        
        Returns:
            list: Liste von Textchunks mit Seitenzuweisungen
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # Wenn Text kleiner als chunk_size ist, als einzelnen Chunk zurückgeben
        if len(text) <= chunk_size:
            # Seitennummer bestimmen
            page_number = None
            for page in pages_info:
                if 0 >= page['startPosition'] and len(text) <= page['endPosition']:
                    page_number = page['pageNumber']
                    break
            
            return [{'text': text, 'page_number': page_number or 1}]
        
        # Mapping von Textposition zu Seitennummer erstellen
        pos_to_page = {}
        for page in pages_info:
            for pos in range(page['startPosition'], page['endPosition'] + 1):
                pos_to_page[pos] = page['pageNumber']
        
        # Text in semantisch sinnvolle Chunks aufteilen mit Memory-Tracking
        try:
            initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
            
            # Für große Texte ein einfacheres Chunking verwenden
            if len(text) > 100000:  # 100K ist ein guter Schwellenwert
                semantic_chunks = self.chunk_text(text, chunk_size, overlap_size)
            else:
                semantic_chunks = self.chunk_text_semantic(text, chunk_size, overlap_size)
                
            current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            memory_used = current_memory - initial_memory
            
            # Wenn zu viel Speicher verwendet wurde, GC erzwingen
            if memory_used > 200:  # Wenn mehr als 200MB verwendet wurden
                logger.warning(f"High memory usage in chunking: {memory_used:.2f} MB, forcing GC")
                gc.collect()
        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}, falling back to simple chunking")
            semantic_chunks = self.chunk_text(text, chunk_size, overlap_size)
        
        # Für jeden Chunk die Seitennummer bestimmen
        current_pos = 0
        for chunk in semantic_chunks:
            # Position des Chunks im ursprünglichen Text finden
            chunk_start = text.find(chunk, current_pos)
            if chunk_start == -1:
                # Fallback, wenn exakte Position nicht gefunden wird
                chunk_start = current_pos
            
            chunk_end = min(chunk_start + len(chunk), len(text) - 1)
            current_pos = chunk_end - overlap_size if overlap_size > 0 else chunk_end
            
            # Seiten für diesen Chunk zählen
            page_counts = {}
            for pos in range(chunk_start, chunk_end + 1):
                if pos in pos_to_page:
                    page_number = pos_to_page[pos]
                    page_counts[page_number] = page_counts.get(page_number, 0) + 1
            
            # Häufigste Seitennummer für diesen Chunk
            most_common_page = None
            max_count = 0
            for page_num, count in page_counts.items():
                if count > max_count:
                    max_count = count
                    most_common_page = page_num
            
            chunks.append({
                'text': chunk,
                'page_number': most_common_page or 1  # Default zu Seite 1, wenn keine Zuordnung gefunden
            })
        
        return chunks
    
    @staticmethod
    def chunk_text(text, chunk_size=1000, overlap_size=200):
        """
        Text in kleinere Chunks aufteilen mit konfigurierbarer Größe und Überlappung
        
        Args:
            text: Zu chunkender Text
            chunk_size: Zielchunkgröße in Zeichen
            overlap_size: Überlappungsgröße in Zeichen
        
        Returns:
            list: Liste von Textchunks
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # Wenn Text kleiner als chunk_size ist, als einzelnen Chunk zurückgeben
        if len(text) <= chunk_size:
            return [text]
        
        start_index = 0
        
        while start_index < len(text):
            # Endindex basierend auf Chunkgröße berechnen
            end_index = min(start_index + chunk_size, len(text))
            
            # Natürlichen Breakpoint finden
            if end_index < len(text):
                # Nach Absatzende oder Satzende im Bereich um end_index suchen
                search_start = max(0, end_index - 100)
                search_end = min(len(text), end_index + 100)
                
                paragraph_end = text.find('\n\n', search_start, search_end)
                sentence_end = -1
                
                # Nach Satzende suchen (Punkt gefolgt von Leerzeichen oder Zeilenumbruch)
                for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    search_start = max(0, end_index - 50)
                    search_end = min(len(text), end_index + 50)
                    pos = text.find(punct, search_start, search_end)
                    if pos != -1 and (sentence_end == -1 or pos < sentence_end):
                        sentence_end = pos + len(punct) - 1
                
                # Nächstgelegenen natürlichen Breakpoint verwenden
                if paragraph_end != -1 and (sentence_end == -1 or abs(paragraph_end - end_index) < abs(sentence_end - end_index)):
                    end_index = paragraph_end + 2  # +2 für '\n\n'
                elif sentence_end != -1:
                    end_index = sentence_end + 1  # +1 für Leerzeichen nach Punkt
            
            # Chunk extrahieren
            chunk = text[start_index:end_index]
            chunks.append(chunk)
            
            # Startindex für nächsten Chunk berechnen (mit Überlappung)
            start_index = end_index - overlap_size
            
            # Sicherstellen, dass wir nicht rückwärts gehen
            if start_index <= 0 or start_index >= end_index:
                start_index = end_index
        
        return chunks
    
    def chunk_text_semantic(self, text, chunk_size=1000, overlap_size=200):
        """
        Text in semantisch sinnvolle Chunks aufteilen mit spaCy und
        robuster Fehlerbehandlung und Performance-Schutzmaßnahmen
        """
        # Maximum Laufzeit und Textlängenlimits setzen
        MAX_TEXT_LENGTH = 500000  # 500K Zeichen max
        MAX_PARAGRAPHS = 2000  # Verhindert übermäßige Speichernutzung
        
        if not text or chunk_size <= 0:
            return []
        
        # Sehr lange Texte kürzen, um Speicherprobleme zu vermeiden
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {MAX_TEXT_LENGTH} chars")
            text = text[:MAX_TEXT_LENGTH]
        
        # Wenn Text kleiner als chunk_size ist, als einzelnen Chunk zurückgeben
        if len(text) <= chunk_size:
            return [text]
        
        # Für extrem große Texte zuerst in Segmente aufteilen
        if len(text) > 20000:
            logger.info(f"Text too large for single semantic chunking, processing in segments")
            segments = []
            # 10K Segmente mit 1K Überlappung für Kontext verarbeiten
            segment_size = 10000
            overlap = 1000
            
            for i in range(0, len(text), segment_size - overlap):
                end = min(i + segment_size, len(text))
                segment_text = text[i:end]
                
                # Jedes Segment mit einfacherem Chunking verarbeiten
                segment_chunks = self.chunk_text(segment_text, chunk_size, overlap_size)
                segments.extend(segment_chunks)
                
                # GC nach jedem Segment erzwingen
                gc.collect()
                
            return segments
        
        chunks = []
        
        try:
            # Text in Absätze aufteilen mit Schutzmaßnahmen
            paragraphs = re.split(r'\n\s*\n', text)
            
            # Limits anwenden, um übermäßige Ressourcennutzung zu verhindern
            if len(paragraphs) > MAX_PARAGRAPHS:
                logger.warning(f"Too many paragraphs ({len(paragraphs)}), limiting to {MAX_PARAGRAPHS}")
                paragraphs = paragraphs[:MAX_PARAGRAPHS]
            
            current_chunk = []
            current_size = 0
            
            # Variablen für Prozesszeit-Überwachung
            start_time = time.time()
            paragraph_count = 0
            
            # Lade spaCy-Modell nur wenn nötig
            spacy_nlp = get_nlp()
            
            for paragraph in paragraphs:
                # Auf übermäßige Verarbeitungszeit prüfen
                if paragraph_count % 100 == 0 and time.time() - start_time > 60:  # 1 Minute max
                    logger.warning("Semantic chunking taking too long, switching to simple chunking")
                    # Angesammelten Text hinzufügen und Rest mit einfachem Chunking verarbeiten
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    
                    # Schnelleres einfaches Chunking für verbleibende Absätze verwenden
                    remaining_text = ' '.join(paragraphs[paragraph_count:])
                    simple_chunks = self.chunk_text(remaining_text, chunk_size, overlap_size)
                    chunks.extend(simple_chunks)
                    return chunks
                
                paragraph_count += 1
                para_size = len(paragraph)
                
                # Wenn Absatz allein größer als chunk_size ist, unterteilen
                if para_size > chunk_size:
                    # Wenn wir bereits etwas im aktuellen Chunk haben, zuerst speichern
                    if current_size > 0:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    
                    # Großen Absatz in Sätze aufteilen mit spaCy mit Timeout-Schutz
                    sentence_splitting_start = time.time()
                    try:
                        # Timeout für spaCy-Verarbeitung setzen
                        if len(paragraph) > 20000:  # Sehr großer Absatz
                            logger.warning(f"Very large paragraph ({len(paragraph)} chars), using regex sentence splitting")
                            # Fallback zu Regex-Satzaufteilung für sehr große Absätze
                            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                        else:
                            # spaCy für bessere Satzaufteilung verwenden
                            nlp_timeout = 10  # 10 Sekunden max für NLP-Verarbeitung
                            if time.time() - sentence_splitting_start > nlp_timeout:
                                raise TimeoutError("NLP processing timeout")
                                
                            doc = spacy_nlp(paragraph)
                            sentences = [sent.text for sent in doc.sents]
                        
                    except Exception as e:
                        logger.warning(f"Error in spaCy sentence splitting: {e}, falling back to regex")
                        # Fallback zu Regex-Satzaufteilung
                        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    
                    # Sätze zu Chunks kombinieren
                    sentence_chunk = []
                    sentence_size = 0
                    
                    for sentence in sentences:
                        sent_size = len(sentence)
                        
                        # Prüfen, ob Satz in aktuellen Chunk passt
                        if sentence_size + sent_size <= chunk_size:
                            sentence_chunk.append(sentence)
                            sentence_size += sent_size
                        else:
                            # Aktuellen Satz-Chunk speichern, wenn nicht leer
                            if sentence_size > 0:
                                chunks.append(' '.join(sentence_chunk))
                            
                            # Wenn Satz selbst zu groß ist, direkt chunken
                            if sent_size > chunk_size:
                                # Einfaches Chunking für sehr große Sätze verwenden
                                sent_chunks = self.chunk_text(sentence, chunk_size, overlap_size)
                                chunks.extend(sent_chunks)
                            else:
                                # Neuen Chunk mit aktuellem Satz beginnen
                                sentence_chunk = [sentence]
                                sentence_size = sent_size
                    
                    # Verbleibenden Satz-Chunk speichern, falls vorhanden
                    if sentence_chunk:
                        chunks.append(' '.join(sentence_chunk))
                
                # Normalfall: Absatz passt potenziell in einen Chunk
                elif current_size + para_size <= chunk_size:
                    current_chunk.append(paragraph)
                    current_size += para_size
                else:
                    # Aktuellen Chunk abschließen und neuen beginnen
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [paragraph]
                    current_size = para_size
            
            # Letzten Chunk hinzufügen, falls vorhanden
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Überlappung falls nötig hinzufügen
            if overlap_size > 0 and len(chunks) > 1:
                chunks_with_overlap = [chunks[0]]
                for i in range(1, len(chunks)):
                    prev_chunk = chunks[i-1]
                    curr_chunk = chunks[i]
                    
                    # Überlappung hinzufügen
                    if len(prev_chunk) >= overlap_size:
                        overlap_text = prev_chunk[-overlap_size:]
                        chunks_with_overlap.append(overlap_text + curr_chunk)
                    else:
                        chunks_with_overlap.append(curr_chunk)
                
                chunks = chunks_with_overlap
            
            # Abschließende Prüfung, um sicherzustellen, dass wir keine leeren Chunks zurückgeben
            chunks = [chunk for chunk in chunks if chunk.strip()]
            return chunks
        
        except Exception as e:
            # Vollständige Fehlerdetails loggen
            logger.error(f"Error in semantic chunking: {str(e)}", exc_info=True)
            
            # Fallback zu einfacherer Chunking-Methode für Robustheit
            logger.warning("Falling back to simple chunking due to error")
            return self.chunk_text(text, chunk_size, overlap_size)
    
    def process_file(self, file_path, settings=None, progress_callback=None):
        """
        Eine PDF-Datei vollständig verarbeiten: Extraktion, Chunking, Metadaten
        mit verbesserter Dateigrößenvalidierung und Fehlerbehandlung
        
        Args:
            file_path: Pfad zur PDF-Datei
            settings: Verarbeitungseinstellungen (max_pages, chunk_size, etc.)
            progress_callback: Optionale Callback-Funktion für Fortschrittsupdates
        
        Returns:
            dict: Ergebnis mit Text, Chunks, Metadaten und Seitenzuweisungen
        """
        if settings is None:
            settings = {
                'maxPages': 0,
                'chunkSize': 1000,
                'chunkOverlap': 200,
                'performOCR': False
            }
        
        # Dateigröße-Limits definieren
        MAX_FILE_SIZE_MB = 50  # 50 MB maximale Dateigröße
        WARN_FILE_SIZE_MB = 25  # Warnschwelle
        
        # Dateigröße vor der Verarbeitung prüfen
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            
            if file_size_mb > MAX_FILE_SIZE_MB:
                error_msg = f"Datei zu groß: {file_size_mb:.1f} MB. Maximale erlaubte Größe ist {MAX_FILE_SIZE_MB} MB."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if file_size_mb > WARN_FILE_SIZE_MB:
                logger.warning(f"Große Datei erkannt: {file_size_mb:.1f} MB. Verarbeitung kann länger dauern.")
                # Benutzer über potenzielle lange Verarbeitungszeit informieren
                if progress_callback:
                    progress_callback(f"Warnung: Große Datei ({file_size_mb:.1f} MB). Verarbeitung kann länger dauern.", 0)
        except Exception as e:
            if "too large" in str(e):
                raise  # Größenlimit-Fehler erneut werfen
            logger.error(f"Fehler bei der Überprüfung der Dateigröße: {e}")
            # Verarbeitung fortsetzen, wenn der Fehler nicht mit der Dateigröße zusammenhängt
        
        # PDF-Datei-Format validieren
        try:
            with open(file_path, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    raise ValueError("Ungültiges PDF-Dateiformat. Datei beginnt nicht mit %PDF-")
        except Exception as e:
            logger.error(f"PDF-Validierungsfehler: {e}")
            raise ValueError(f"Ungültige oder beschädigte PDF-Datei: {str(e)}")
        
        # Fortschritts-Wrapper definieren, um Fortschritt auf Phasen aufzuteilen
        def progress_wrapper(stage, progress_func=None):
            if not progress_callback:
                return lambda msg, pct: None
            
            if stage == 'extraction':
                return lambda msg, pct: progress_callback(msg, pct * 0.6)
            elif stage == 'chunking':
                return lambda msg, pct: progress_callback(msg, 60 + pct * 0.3)
            elif stage == 'metadata':
                return lambda msg, pct: progress_callback(msg, 90 + pct * 0.1)
            else:
                return progress_callback
        
        try:
            # Text mit Fortschrittsberichterstattung und Memory-Überwachung extrahieren
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # Create a file hash for caching
            file_hash = f"{os.path.getsize(file_path)}_{os.path.getmtime(file_path)}"
            
            extraction_result = self.extract_text_from_pdf(
                file_path, 
                max_pages=settings.get('maxPages', 0),
                perform_ocr=settings.get('performOCR', False),
                progress_callback=progress_wrapper('extraction')
            )
            
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_used = current_memory - start_memory
            logger.info(f"Memory used for text extraction: {memory_used:.2f} MB")
            
            # Fortschrittsupdate
            if progress_callback:
                progress_callback("Extracting metadata", 60)
            
            # DOI, ISBN extrahieren
            extracted_text = extraction_result['text']
            identifiers = self.extract_identifiers(extracted_text, file_hash)
            
            # Fortschrittsupdate
            if progress_callback:
                progress_callback("Creating chunks with page tracking", 65)
            
            # Chunks mit Seitenverfolgung erstellen
            chunks_with_pages = self.chunk_text_with_pages(
                extracted_text,
                extraction_result['pages'],
                chunk_size=settings.get('chunkSize', 1000),
                overlap_size=settings.get('chunkOverlap', 200)
            )
            
            # Chunks validieren - sicherstellen, dass wir keine leeren Chunks haben
            chunks_with_pages = [chunk for chunk in chunks_with_pages if chunk.get('text', '').strip()]
            
            # Fortschrittsupdate
            if progress_callback:
                progress_callback("Processing complete", 100)
            
            # GC erzwingen, um Speicher freizugeben
            gc.collect()

            return {
                'text': extracted_text,
                'chunks': chunks_with_pages,
                'metadata': {
                    'doi': identifiers['doi'],
                    'isbn': identifiers['isbn'],
                    'totalPages': extraction_result['totalPages'],
                    'processedPages': extraction_result['processedPages']
                },
                'pages': extraction_result['pages']
            }
        except Exception as e:
            logger.error(f"Error in PDF processing: {str(e)}")
            
            # GC bei Fehler erzwingen
            gc.collect()
            
            # Mit mehr Kontext erneut werfen
            raise ValueError(f"Failed to process PDF: {str(e)}")