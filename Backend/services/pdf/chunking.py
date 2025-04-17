# Backend/services/pdf/chunking.py
"""
Text-Chunking-Komponente für die PDF-Verarbeitung
"""
import re
import logging
import gc
import psutil
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Lazy-Loading für spaCy
_nlp = None

def get_nlp():
    """Lazy-Load spaCy model nur wenn benötigt"""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            try:
                _nlp = spacy.load("de_core_news_sm")
                logger.info("Loaded spaCy model: de_core_news_sm")
            except OSError:
                try:
                    _nlp = spacy.load("en_core_web_sm")
                    logger.info("Loaded spaCy model: en_core_web_sm")
                except OSError:
                    logger.warning("No spaCy language model found. Using blank model.")
                    _nlp = spacy.blank("en")
        except ImportError:
            logger.warning("spaCy not available")
            return None
    return _nlp

class TextChunker:
    """
    Komponente zum Chunking von extrahiertem Text
    """
    
    def __init__(self):
        """
        Initialisiert den Text-Chunker
        """
        # Setzt Limits und Konfiguration
        self.MAX_TEXT_LENGTH = 500000  # 500K Zeichen max für Chunking
        self.MAX_PARAGRAPH_SIZE = 10000  # 10K Zeichen max Absatzgröße
    
    def chunk_text_with_pages(self, text, pages_info, chunk_size=1000, overlap_size=200):
        """
        Teilt Text in Chunks mit Seitenverfolgung
        
        Args:
            text: Vollständiger Dokumenttext
            pages_info: Liste von Seiteninformationen mit Positionen
            chunk_size: Ziel-Chunkgröße in Zeichen
            overlap_size: Überlappungsgröße in Zeichen
        
        Returns:
            list: Liste von Textchunks mit Seitenzuordnungen
        """
        if not text or chunk_size <= 0:
            logger.warning("Invalid input for chunking: empty text or invalid chunk size")
            return []
        
        logger.info(f"Chunking text with pages, text length: {len(text)}, chunk_size: {chunk_size}, overlap: {overlap_size}")
        chunks = []
        
        # Wenn Text kleiner als Chunkgröße ist, als einzelnen Chunk zurückgeben
        if len(text) <= chunk_size:
            logger.debug("Text smaller than chunk size, returning as single chunk")
            # Seite finden
            page_number = 1
            for page in pages_info:
                if 0 >= page['startPosition'] and len(text) <= page['endPosition']:
                    page_number = page['pageNumber']
                    break
            
            return [{'text': text, 'page_number': page_number}]
        
        # Position-zu-Seite-Mapping erstellen
        logger.debug("Creating position to page mapping")
        pos_to_page = {}
        for page in pages_info:
            for pos in range(page['startPosition'], page['endPosition'] + 1):
                pos_to_page[pos] = page['pageNumber']
        
        # Speichernutzung überwachen
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        logger.debug(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Chunking-Methode basierend auf Textgröße wählen
        try:
            # Für große Texte, verwende einfacheres Chunking
            if len(text) > 100000:  # 100K ist ein Schwellenwert
                logger.info(f"Large text detected ({len(text)} chars), using simple chunking")
                text_chunks = self.chunk_text(text, chunk_size, overlap_size)
            else:
                logger.info(f"Using semantic chunking for text ({len(text)} chars)")
                text_chunks = self.chunk_text_semantic(text, chunk_size, overlap_size)
                
            current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            memory_used = current_memory - initial_memory
            logger.debug(f"Memory used after chunking: {memory_used:.2f} MB")
            
            # Erzwinge GC bei hoher Speichernutzung
            if memory_used > 200:  # 200MB Schwellenwert
                logger.warning(f"High memory usage in chunking: {memory_used:.2f} MB, forcing GC")
                gc.collect()
                
        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}", exc_info=True)
            logger.warning("Falling back to simple chunking")
            text_chunks = self.chunk_text(text, chunk_size, overlap_size)
        
        # Seiten zu Chunks zuordnen
        logger.debug(f"Assigning pages to {len(text_chunks)} chunks")
        current_pos = 0
        for chunk in text_chunks:
            # Finde Chunk-Position im Originaltext
            chunk_start = text.find(chunk, current_pos)
            if chunk_start == -1:
                # Fallback wenn exakte Position nicht gefunden
                chunk_start = current_pos
                logger.warning(f"Could not find exact chunk position, using fallback position: {current_pos}")
            
            chunk_end = min(chunk_start + len(chunk), len(text) - 1)
            current_pos = chunk_end - overlap_size if overlap_size > 0 else chunk_end
            
            # Zähle Seiten für diesen Chunk
            page_counts = {}
            for pos in range(chunk_start, chunk_end + 1):
                if pos in pos_to_page:
                    page_number = pos_to_page[pos]
                    page_counts[page_number] = page_counts.get(page_number, 0) + 1
            
            # Finde häufigste Seite
            most_common_page = 1
            max_count = 0
            for page_num, count in page_counts.items():
                if count > max_count:
                    max_count = count
                    most_common_page = page_num
            
            chunks.append({
                'text': chunk,
                'page_number': most_common_page
            })
        
        logger.info(f"Chunking complete, created {len(chunks)} chunks with page tracking")
        return chunks
    
    def chunk_text(self, text, chunk_size=1000, overlap_size=200):
        """
        Teilt Text in kleinere Chunks mit Überlappung (einfache Methode)
        
        Args:
            text: Zu teilender Text
            chunk_size: Ziel-Chunkgröße
            overlap_size: Überlappungsgröße
        
        Returns:
            list: Liste von Textchunks
        """
        if not text or chunk_size <= 0:
            logger.warning("Invalid input for simple chunking")
            return []
        
        logger.debug(f"Simple chunking text, length: {len(text)}, chunk_size: {chunk_size}, overlap: {overlap_size}")
        chunks = []
        
        # Einzelner Chunk für kleinen Text
        if len(text) <= chunk_size:
            logger.debug("Text smaller than chunk size, returning as single chunk")
            return [text]
        
        start_index = 0
        
        while start_index < len(text):
            # Berechne Ende basierend auf Chunkgröße
            end_index = min(start_index + chunk_size, len(text))
            
            # Finde natürlichen Breakpoint
            if end_index < len(text):
                # Suche nach Absatz- oder Satzende nahe dem Ziel
                search_start = max(0, end_index - 100)
                search_end = min(len(text), end_index + 100)
                
                # Versuche zuerst Absatzende
                paragraph_end = text.find('\n\n', search_start, search_end)
                
                # Dann Satzende
                sentence_end = -1
                for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    pos = text.find(punct, search_start, search_end)
                    if pos != -1 and (sentence_end == -1 or pos < sentence_end):
                        sentence_end = pos + len(punct) - 1
                
                # Verwende nächsten natürlichen Break
                if paragraph_end != -1 and (sentence_end == -1 or 
                                          abs(paragraph_end - end_index) < abs(sentence_end - end_index)):
                    logger.debug(f"Found paragraph break at {paragraph_end}, original end: {end_index}")
                    end_index = paragraph_end + 2  # Inkl. '\n\n'
                elif sentence_end != -1:
                    logger.debug(f"Found sentence break at {sentence_end}, original end: {end_index}")
                    end_index = sentence_end + 1  # Inkl. Leerzeichen nach Satzzeichen
            
            # Extrahiere Chunk
            chunk = text[start_index:end_index]
            chunks.append(chunk)
            
            # Berechne nächsten Start mit Überlappung
            start_index = end_index - overlap_size
            
            # Verhindere Loops oder Rückwärtsbewegung
            if start_index <= 0 or start_index >= end_index:
                start_index = end_index
        
        logger.debug(f"Simple chunking complete, created {len(chunks)} chunks")
        return chunks
    
    def chunk_text_semantic(self, text, chunk_size=1000, overlap_size=200):
        """
        Teilt Text in semantisch sinnvolle Chunks mit spaCy (fortgeschrittene Methode)
        
        Args:
            text: Zu teilender Text
            chunk_size: Ziel-Chunkgröße
            overlap_size: Überlappungsgröße
        
        Returns:
            list: Liste von Textchunks
        """
        # Vereinfachte, robustere Implementierung - zerlegt die komplexe Methode in Teile
        
        # Setze Limits
        MAX_PARAGRAPHS = 1000  # Vermeide übermäßige Speichernutzung
        
        if not text or chunk_size <= 0:
            logger.warning("Invalid input for semantic chunking")
            return []
        
        # Kürze sehr lange Texte
        if len(text) > self.MAX_TEXT_LENGTH:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {self.MAX_TEXT_LENGTH}")
            text = text[:self.MAX_TEXT_LENGTH]
        
        # Einzelner Chunk für kleinen Text
        if len(text) <= chunk_size:
            logger.debug("Text smaller than chunk size, returning as single chunk")
            return [text]
        
        # Verarbeite große Texte in Segmenten
        if len(text) > 20000:
            return self._chunk_large_text(text, chunk_size, overlap_size)
        
        try:
            # Teile Text in Absätze
            paragraphs = re.split(r'\n\s*\n', text)
            logger.debug(f"Split text into {len(paragraphs)} paragraphs")
            
            # Begrenze Absätze, um Speicherprobleme zu vermeiden
            if len(paragraphs) > MAX_PARAGRAPHS:
                logger.warning(f"Too many paragraphs ({len(paragraphs)}), limiting to {MAX_PARAGRAPHS}")
                paragraphs = paragraphs[:MAX_PARAGRAPHS]
            
            # Erstelle Chunks durch intelligente Absatzgruppierung
            return self._chunk_paragraphs(paragraphs, chunk_size, overlap_size)
            
        except Exception as e:
            logger.error(f"Error in semantic chunking: {str(e)}", exc_info=True)
            # Fallback zu einfacherem Chunking
            logger.warning("Error in semantic chunking, falling back to simple chunking")
            return self.chunk_text(text, chunk_size, overlap_size)
    
    def _chunk_large_text(self, text, chunk_size, overlap_size):
        """
        Spezielles Chunking für sehr große Texte
        
        Args:
            text: Zu teilender Text
            chunk_size: Ziel-Chunkgröße
            overlap_size: Überlappungsgröße
        
        Returns:
            list: Liste von Textchunks
        """
        logger.info(f"Large text detected ({len(text)} chars), processing in segments")
        segments = []
        segment_size = 10000
        overlap = 1000
        
        for i in range(0, len(text), segment_size - overlap):
            end = min(i + segment_size, len(text))
            segment_text = text[i:end]
            logger.debug(f"Processing segment {i}-{end} ({len(segment_text)} chars)")
            
            # Verarbeite jedes Segment mit einfacherem Chunking
            segment_chunks = self.chunk_text(segment_text, chunk_size, overlap_size)
            segments.extend(segment_chunks)
            
            # Erzwinge GC nach jedem Segment
            gc.collect()
            
        logger.debug(f"Segmented processing complete, created {len(segments)} chunks")
        return segments

def _chunk_paragraphs(self, paragraphs, chunk_size, overlap_size):
    """
    Erstellt Chunks aus einer Liste von Absätzen
    
    Args:
        paragraphs: Liste von Textabsätzen
        chunk_size: Ziel-Chunkgröße
        overlap_size: Überlappungsgröße
    
    Returns:
        list: Liste von Textchunks
    """
    chunks = []
    current_chunk = []
    current_size = 0
    
    # Überwache Verarbeitungszeit
    import time
    start_time = time.time()
    
    for paragraph in paragraphs:
        # Prüfe auf übermäßige Verarbeitungszeit nach jedem 20. Absatz
        if len(current_chunk) % 20 == 0 and time.time() - start_time > 15:  # 15s max
            logger.warning("Semantic chunking taking too long, switching to simpler approach")
            
            # Verarbeite die restlichen Absätze mit einfachem Chunking
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            remaining_text = ' '.join(paragraphs[len(chunks):])
            return chunks + self.chunk_text(remaining_text, chunk_size, overlap_size)
        
        para_size = len(paragraph)
        
        # Behandle Absätze, die größer als die Chunkgröße sind
        if para_size > chunk_size:
            logger.debug(f"Paragraph larger than chunk size: {para_size} chars")
            # Speichere aktuellen Chunk zuerst
            if current_size > 0:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Verarbeite großen Absatz separat
            big_para_chunks = self._chunk_big_paragraph(paragraph, chunk_size, overlap_size)
            chunks.extend(big_para_chunks)
            continue
        
        # Normaler Fall: Absatz passt in Chunk
        if current_size + para_size <= chunk_size:
            current_chunk.append(paragraph)
            current_size += para_size
        else:
            # Beende aktuellen Chunk und starte einen neuen
            chunks.append(' '.join(current_chunk))
            current_chunk = [paragraph]
            current_size = para_size
    
    # Füge letzten Chunk hinzu
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Füge Überlappung hinzu, falls nötig
    if overlap_size > 0 and len(chunks) > 1:
        return self._add_overlap_to_chunks(chunks, overlap_size)
    
    # Entferne leere Chunks
    return [chunk for chunk in chunks if chunk.strip()]

def _chunk_big_paragraph(self, paragraph, chunk_size, overlap_size):
    """
    Teilt einen großen Absatz in Chunks
    
    Args:
        paragraph: Absatztext
        chunk_size: Ziel-Chunkgröße
        overlap_size: Überlappungsgröße
    
    Returns:
        list: Liste von Chunks aus dem Absatz
    """
    para_chunks = []
    
    # Versuche, mit spaCy in Sätze zu zerlegen
    try:
        nlp = get_nlp()
        if nlp and len(paragraph) < 50000:  # Begrenzung für spaCy-Verarbeitung
            doc = nlp(paragraph)
            sentences = [sent.text for sent in doc.sents]
            logger.debug(f"Split paragraph into {len(sentences)} sentences using spaCy")
            
            # Kombiniere Sätze zu Chunks
            sent_chunk = []
            sent_size = 0
            
            for sentence in sentences:
                sent_size = len(sentence)
                
                # Prüfe, ob Satz in aktuellen Chunk passt
                if sent_size + sent_size <= chunk_size:
                    sent_chunk.append(sentence)
                    sent_size += sent_size
                else:
                    # Speichere aktuellen Satz-Chunk
                    if sent_size > 0:
                        para_chunks.append(' '.join(sent_chunk))
                    
                    # Behandle sehr große Sätze
                    if sent_size > chunk_size:
                        logger.debug(f"Very large sentence: {sent_size} chars, using simple chunking")
                        # Verwende einfaches Chunking für große Sätze
                        sent_chunks = self.chunk_text(sentence, chunk_size, overlap_size)
                        para_chunks.extend(sent_chunks)
                    else:
                        # Starte neuen Chunk mit aktuellem Satz
                        sent_chunk = [sentence]
                        sent_size = sent_size
            
            # Speichere verbleibenden Satz-Chunk
            if sent_chunk:
                para_chunks.append(' '.join(sent_chunk))
            
            return para_chunks
    except Exception as e:
        logger.warning(f"Error using spaCy for sentence splitting: {e}")
    
    # Fallback: Verwende Regex für Satzzerlegung
    logger.debug("Using regex fallback for chunking large paragraph")
    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
    
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sent_size = len(sentence)
        
        if current_size + sent_size <= chunk_size:
            current_chunk.append(sentence)
            current_size += sent_size
        else:
            if current_chunk:
                para_chunks.append(' '.join(current_chunk))
            
            # Behandle sehr große Sätze
            if sent_size > chunk_size:
                # Teile sehr lange Sätze auf
                sent_parts = self.chunk_text(sentence, chunk_size, overlap_size)
                para_chunks.extend(sent_parts)
                current_chunk = []
                current_size = 0
            else:
                # Starte neuen Chunk
                current_chunk = [sentence]
                current_size = sent_size
    
    # Füge letzten Chunk hinzu
    if current_chunk:
        para_chunks.append(' '.join(current_chunk))
    
    return para_chunks

def _add_overlap_to_chunks(self, chunks, overlap_size):
    """
    Fügt Überlappung zwischen Chunks hinzu
    
    Args:
        chunks: Liste von Chunks
        overlap_size: Größe der Überlappung
    
    Returns:
        list: Chunks mit Überlappung
    """
    if not chunks or len(chunks) <= 1:
        return chunks
    
    logger.debug(f"Adding overlap between {len(chunks)} chunks, size: {overlap_size}")
    chunks_with_overlap = [chunks[0]]
    
    for i in range(1, len(chunks)):
        prev_chunk = chunks[i-1]
        curr_chunk = chunks[i]
        
        # Füge Überlappung vom vorherigen Chunk hinzu
        if len(prev_chunk) >= overlap_size:
            overlap_text = prev_chunk[-overlap_size:]
            chunks_with_overlap.append(overlap_text + curr_chunk)
        else:
            # Verwende ganzen vorherigen Chunk, wenn kleiner als Überlappungsgröße
            overlap_text = prev_chunk
            chunks_with_overlap.append(overlap_text + curr_chunk)
    
    return chunks_with_overlap