# Backend/services/pdf_processor.py
import os
import re
import logging
import tempfile
from pathlib import Path
import pytesseract
from PIL import Image
import io
import numpy as np

# PyMuPDF Importierung
try:
    import fitz  # PyMuPDF
except ImportError:
    try:
        import PyMuPDF as fitz
    except ImportError:
        raise ImportError("PyMuPDF nicht gefunden. Bitte installieren Sie es mit: pip install PyMuPDF")

# spaCy Importierung
try:
    import spacy
    logger = logging.getLogger(__name__)
    # Prüfen, ob Spacy-Modell installiert ist und laden
    try:
        nlp = spacy.load("de_core_news_sm")
        logger.info("Spacy model loaded: de_core_news_sm")
    except:
        try:
            nlp = spacy.load("en_core_web_sm")
            logger.info("Spacy model loaded: en_core_web_sm")
        except:
            logger.warning("No spacy language model found. Using blank model.")
            nlp = spacy.blank("en")
except ImportError:
    raise ImportError("Spacy nicht gefunden. Bitte installieren Sie es mit: pip install spacy")


class PDFProcessor:
    """Klasse zur Verarbeitung von PDF-Dateien"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_file, max_pages=0, perform_ocr=False):
        """
        Extrahiert Text aus einer PDF-Datei
        
        Args:
            pdf_file: PDF-Datei (Dateipfad oder Bytes)
            max_pages: Maximale Anzahl zu verarbeitender Seiten (0 = alle)
            perform_ocr: OCR für Seiten mit wenig Text durchführen
        
        Returns:
            dict: Ergebnis mit Text und Seiteninfos
        """
        try:
            # Temporäre Datei für Bytes-Input erstellen
            if isinstance(pdf_file, bytes):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_file.write(pdf_file)
                temp_file.close()
                pdf_path = temp_file.name
            else:
                pdf_path = pdf_file
            
            # PDF öffnen
            doc = fitz.open(pdf_path)
            
            # Ergebnisobjekt vorbereiten
            result = {
                'text': '',
                'pages': [],
                'totalPages': len(doc),
                'processedPages': min(len(doc), max_pages) if max_pages > 0 else len(doc)
            }
            
            # Anzahl zu verarbeitender Seiten berechnen
            pages_to_process = result['processedPages']
            
            # Seitenliste für OCR (Seiten mit wenig Text)
            ocr_page_numbers = []
            
            # Text aus jeder Seite extrahieren
            for i in range(pages_to_process):
                page = doc[i]
                
                # Seitenmetadaten
                page_info = {
                    'pageNumber': i + 1,
                    'width': page.rect.width,
                    'height': page.rect.height,
                    'text': ''
                }
                
                # Text extrahieren
                page_text = page.get_text()
                page_info['text'] = page_text
                result['text'] += page_text + ' '
                
                # Prüfen, ob die Seite wenig Text enthält -> OCR-Kandidat
                if perform_ocr and len(page_text.strip()) < 100:
                    ocr_page_numbers.append(i)
                
                result['pages'].append(page_info)
            
            # OCR für Seiten mit wenig Text durchführen
            if perform_ocr and ocr_page_numbers:
                ocr_results = PDFProcessor.perform_ocr_on_pages(doc, ocr_page_numbers)
                
                # OCR-Ergebnisse den Seiten hinzufügen
                for page_num, ocr_text in ocr_results.items():
                    # Original-Seitennummer (1-basiert) in Listenindex (0-basiert) umwandeln
                    idx = page_num - 1
                    if idx < len(result['pages']):
                        # Text aktualisieren oder hinzufügen
                        orig_text = result['pages'][idx]['text']
                        if not orig_text.strip():
                            result['pages'][idx]['text'] = ocr_text
                            # Gesamttext aktualisieren
                            result['text'] = result['text'].replace(orig_text, ocr_text)
                        else:
                            # Text hinzufügen, wenn bereits Text vorhanden ist
                            result['pages'][idx]['text'] += ' ' + ocr_text
                            result['text'] += ' ' + ocr_text
            
            # Aufräumen
            doc.close()
            if isinstance(pdf_file, bytes) and os.path.exists(pdf_path):
                os.unlink(pdf_path)
            
            return result
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            # Aufräumen bei Fehler
            if isinstance(pdf_file, bytes) and 'pdf_path' in locals() and os.path.exists(pdf_path):
                os.unlink(pdf_path)
            raise
    
    @staticmethod
    def perform_ocr_on_pages(doc, page_numbers, dpi=300):
        """
        Führt OCR für bestimmte Seiten durch
        
        Args:
            doc: Geöffnetes PyMuPDF-Dokument
            page_numbers: Liste der Seitennummern (0-basiert) für OCR
            dpi: DPI für Rendering
        
        Returns:
            dict: Ergebnisse als {seitennummer: text}
        """
        results = {}
        
        try:
            for page_idx in page_numbers:
                if page_idx < 0 or page_idx >= len(doc):
                    continue
                
                # Seite rendern
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                
                # Als Bild speichern
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # OCR durchführen
                ocr_text = pytesseract.image_to_string(img)
                
                # Seitennummer (1-basiert) für das Ergebnis
                results[page_idx + 1] = ocr_text
        
        except Exception as e:
            logger.error(f"Error performing OCR: {e}")
        
        return results
    
    @staticmethod
    def extract_doi(text):
        """
        Extrahiert DOI aus Text mittels Regex
        
        Args:
            text: Text, in dem nach DOI gesucht werden soll
        
        Returns:
            str: Gefundene DOI oder None
        """
        if not text:
            return None
        
        # DOI-Muster (verbessert für bessere Übereinstimmung)
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
        Extrahiert ISBN aus Text mittels Regex
        
        Args:
            text: Text, in dem nach ISBN gesucht werden soll
        
        Returns:
            str: Gefundene ISBN oder None
        """
        if not text:
            return None
        
        # ISBN-10 und ISBN-13 Muster
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
    
    @staticmethod
    def chunk_text(text, chunk_size=1000, overlap_size=200):
        """
        Teilt Text in kleinere Chunks mit konfigurierbarer Größe und Überlappung
        
        Args:
            text: Text zum Chunken
            chunk_size: Zielgröße der Chunks in Zeichen
            overlap_size: Überlappungsgröße in Zeichen
        
        Returns:
            list: Liste von Textchunks
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # Falls Text kleiner als chunk_size ist, als einzelnen Chunk zurückgeben
        if len(text) <= chunk_size:
            return [text]
        
        start_index = 0
        
        while start_index < len(text):
            # Ende-Index basierend auf Chunkgröße berechnen
            end_index = min(start_index + chunk_size, len(text))
            
            # Natürlichen Breakpoint finden
            if end_index < len(text):
                # Suche nach Absatzende oder Satzende innerhalb eines Bereichs um den End-Index
                search_start = max(0, end_index - 100)
                search_end = min(len(text), end_index + 100)
                
                paragraph_end = text.find('\n\n', search_start, search_end)
                sentence_end = -1
                
                # Suche nach Satzende (Punkt gefolgt von Leerzeichen oder Zeilenumbruch)
                for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    search_start = max(0, end_index - 50)
                    search_end = min(len(text), end_index + 50)
                    pos = text.find(punct, search_start, search_end)
                    if pos != -1 and (sentence_end == -1 or pos < sentence_end):
                        sentence_end = pos + len(punct) - 1
                
                # Verwende den nächstgelegenen natürlichen Breakpoint
                if paragraph_end != -1 and (sentence_end == -1 or abs(paragraph_end - end_index) < abs(sentence_end - end_index)):
                    end_index = paragraph_end + 2  # +2 für '\n\n'
                elif sentence_end != -1:
                    end_index = sentence_end + 1  # +1 für Leerzeichen nach Punkt
            
            # Chunk extrahieren
            chunk = text[start_index:end_index]
            chunks.append(chunk)
            
            # Start-Index für nächsten Chunk berechnen (mit Überlappung)
            start_index = end_index - overlap_size
            
            # Sicherstellen, dass wir nicht rückwärts gehen
            if start_index <= 0 or start_index >= end_index:
                start_index = end_index
        
        return chunks
    
    @staticmethod
    def chunk_text_semantic(text, chunk_size=1000, overlap_size=200):
        """
        Teilt Text in semantisch sinnvolle Chunks mit spaCy
        
        Args:
            text: Text zum Chunken
            chunk_size: Zielgröße der Chunks in Zeichen
            overlap_size: Überlappungsgröße in Zeichen
        
        Returns:
            list: Liste von Textchunks
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # Falls Text kleiner als chunk_size ist, als einzelnen Chunk zurückgeben
        if len(text) <= chunk_size:
            return [text]
        
        try:
            # Text in Absätze aufteilen
            paragraphs = re.split(r'\n\s*\n', text)
            
            current_chunk = []
            current_size = 0
            
            for paragraph in paragraphs:
                # Größe des aktuellen Absatzes
                para_size = len(paragraph)
                
                # Wenn der Absatz allein schon größer als chunk_size ist, unterteilen
                if para_size > chunk_size:
                    # Wenn wir schon etwas im aktuellen Chunk haben, diesen erst speichern
                    if current_size > 0:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    
                    # Großen Absatz in Sätze aufteilen
                    doc = nlp(paragraph)
                    sentences = [sent.text for sent in doc.sents]
                    
                    # Sätze zu Chunks zusammenfügen
                    sentence_chunk = []
                    sentence_size = 0
                    
                    for sentence in sentences:
                        sent_size = len(sentence)
                        
                        # Prüfen, ob der Satz in den aktuellen Chunk passt
                        if sentence_size + sent_size <= chunk_size:
                            sentence_chunk.append(sentence)
                            sentence_size += sent_size
                        else:
                            # Aktuellen Satz-Chunk speichern, wenn nicht leer
                            if sentence_size > 0:
                                chunks.append(' '.join(sentence_chunk))
                            
                            # Falls der Satz selbst zu groß ist, direkt speichern
                            if sent_size > chunk_size:
                                chunks.extend(PDFProcessor.chunk_text(sentence, chunk_size, overlap_size))
                            else:
                                # Neuen Chunk mit aktuellem Satz beginnen
                                sentence_chunk = [sentence]
                                sentence_size = sent_size
                    
                    # Restlichen Satz-Chunk speichern, wenn vorhanden
                    if sentence_chunk:
                        chunks.append(' '.join(sentence_chunk))
                
                # Normaler Fall: Absatz passt potenziell in einen Chunk
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
            
            # Überlappung hinzufügen, wenn benötigt
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
            
            return chunks
        
        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}")
            # Fallback zur einfachen Chunking-Methode
            return PDFProcessor.chunk_text(text, chunk_size, overlap_size)