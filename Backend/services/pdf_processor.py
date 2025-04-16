import os
import re
import logging
import tempfile
import time
import gc
import psutil
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional, Union, Callable
import pytesseract
from PIL import Image
import io

# Import fitz (PyMuPDF) with proper error handling
try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF not found. Please install: pip install PyMuPDF")

# Configure logging
logger = logging.getLogger(__name__)

# Global spaCy model - lazy loaded
nlp = None

def get_nlp():
    """Lazy-load spaCy model only when needed"""
    global nlp
    if nlp is None:
        import spacy
        try:
            nlp = spacy.load("de_core_news_sm")
            logger.info("Loaded spaCy model: de_core_news_sm")
        except OSError:
            try:
                nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model: en_core_web_sm")
            except OSError:
                logger.warning("No spaCy language model found. Using blank model.")
                nlp = spacy.blank("en")
    return nlp

class PDFProcessor:
    """
    Optimized class for PDF processing with improved performance and error handling
    """
    
    def __init__(self, max_workers=2, ocr_max_workers=1, cache_size=50):
        """
        Initialize PDF processor with configurable thread pools
        
        Args:
            max_workers: Maximum number of worker threads for general processing
            ocr_max_workers: Maximum number of worker threads for OCR (CPU intensive)
            cache_size: Maximum number of entries in the processing cache
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.ocr_executor = ThreadPoolExecutor(max_workers=ocr_max_workers)
        self._text_cache = {}
        self._identifier_cache = {}
        self.cache_size = cache_size
        
        # Define limits
        self.MAX_FILE_SIZE_MB = 50
        self.WARN_FILE_SIZE_MB = 20
        self.MAX_TEXT_LENGTH = 500000  # 500K characters max for chunking
        self.MAX_PARAGRAPH_SIZE = 10000  # 10K characters max paragraph size
        self.MAX_OCR_PAGES = 5  # Maximum pages to OCR in one batch
    
    def __del__(self):
        """Cleanup thread pools on deletion"""
        self.executor.shutdown(wait=False)
        self.ocr_executor.shutdown(wait=False)
    
    def validate_pdf(self, filepath):
        """Validate PDF format with improved error handling"""
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                return False, "PDF file not found"
                
            # Check header bytes
            with open(filepath, 'rb') as f:
                header = f.read(5)
                if header != b'%PDF-':
                    return False, "Invalid PDF file format (incorrect header)"
            
            # Try opening with PyMuPDF
            try:
                doc = fitz.open(filepath)
                page_count = len(doc)
                doc.close()
                return True, page_count
            except Exception as e:
                return False, f"Could not open PDF with PyMuPDF: {str(e)}"
                
        except Exception as e:
            return False, str(e)
    
    def extract_text_from_pdf(self, pdf_file, max_pages=0, perform_ocr=False, progress_callback=None):
        """
        Extract text from a PDF file with improved page tracking
        
        Args:
            pdf_file: PDF file path or bytes
            max_pages: Maximum pages to process (0 = all)
            perform_ocr: Perform OCR for pages with little text
            progress_callback: Optional progress reporting function
        
        Returns:
            dict: Extraction result with text and page information
        """
        # Check cache
        file_hash = None
        if isinstance(pdf_file, str) and os.path.exists(pdf_file):
            file_hash = f"{os.path.getsize(pdf_file)}_{os.path.getmtime(pdf_file)}"
            if file_hash in self._text_cache:
                logger.info(f"Using cached text for {pdf_file}")
                return self._text_cache[file_hash]
        
        try:
            # Create temp file for bytes input
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
            
            # Process pages in batches for better memory management
            pages_to_process = result['processedPages']
            ocr_candidates = []
            BATCH_SIZE = 10  # Process 10 pages at a time
            
            for batch_start in range(0, pages_to_process, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, pages_to_process)
                
                # Process each page in the batch
                for i in range(batch_start, batch_end):
                    page = doc[i]
                    
                    # Report progress
                    if progress_callback:
                        progress_callback(f"Processing page {i+1}/{pages_to_process}", 
                                        int(i/pages_to_process * 100))
                    
                    # Page metadata
                    page_info = {
                        'pageNumber': i + 1,
                        'width': page.rect.width,
                        'height': page.rect.height,
                        'text': '',
                        'startPosition': len(result['text']), # Position in total text
                    }
                    
                    # Extract text
                    page_text = page.get_text()
                    
                    # Split large text blocks to prevent memory issues
                    if len(page_text) > self.MAX_PARAGRAPH_SIZE:
                        # Use natural breaks to split text
                        split_texts = re.split(r'\n\s*\n', page_text)
                        page_text = '\n\n'.join(split_texts)
                        
                    page_info['text'] = page_text
                    page_info['length'] = len(page_text)
                    
                    # Add to total text
                    result['text'] += page_text + ' '
                    
                    # Update end position
                    page_info['endPosition'] = len(result['text']) - 1
                    
                    # Add to OCR candidates if low text
                    if perform_ocr and len(page_text.strip()) < 100:
                        ocr_candidates.append(i)
                    
                    result['pages'].append(page_info)
                
                # Force garbage collection after each batch
                gc.collect()

            # Perform OCR for pages with little text
            if perform_ocr and ocr_candidates:
                if progress_callback:
                    progress_callback(f"Performing OCR on {len(ocr_candidates)} pages", 50)
                
                # Process OCR in smaller batches to limit memory usage
                for i in range(0, len(ocr_candidates), self.MAX_OCR_PAGES):
                    batch = ocr_candidates[i:i+self.MAX_OCR_PAGES]
                    
                    # Process OCR for this batch
                    futures = []
                    for page_num in batch:
                        future = self.ocr_executor.submit(self._perform_ocr_on_page, doc, page_num, 300)
                        futures.append(future)
                    
                    # Collect OCR results
                    for j, future in enumerate(futures):
                        try:
                            page_num, ocr_text = future.result()
                            # Convert to 1-based page number for index
                            idx = page_num - 1
                            if idx < len(result['pages']):
                                # Update text
                                orig_text = result['pages'][idx]['text']
                                if not orig_text.strip():
                                    result['pages'][idx]['text'] = ocr_text
                                    # Update total text by replacing the empty text
                                    result['text'] = result['text'].replace(orig_text, ocr_text)
                                else:
                                    # Append OCR text if original text exists
                                    result['pages'][idx]['text'] += ' ' + ocr_text
                                    result['text'] += ' ' + ocr_text
                            
                            # Report progress
                            if progress_callback:
                                progress_callback(f"OCR processing: {i+j+1}/{len(ocr_candidates)}", 
                                                50 + int((i+j+1)/len(ocr_candidates) * 45))
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
                # Maintain cache size
                if len(self._text_cache) >= self.cache_size:
                    # Remove oldest entry
                    oldest_key = next(iter(self._text_cache))
                    self._text_cache.pop(oldest_key)
                    
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
        Perform OCR on a single page
        
        Args:
            doc: Open PyMuPDF document
            page_idx: Page index (0-based)
            dpi: DPI for rendering
        
        Returns:
            tuple: (page_number, ocr_text)
        """
        try:
            if page_idx < 0 or page_idx >= len(doc):
                return page_idx + 1, ""
            
            # Render page to image
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            
            # Convert to image for OCR
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(img)
            
            # Return page number (1-based) with text
            return page_idx + 1, ocr_text
        except Exception as e:
            logger.error(f"Error performing OCR on page {page_idx + 1}: {e}")
            return page_idx + 1, ""
    
    def extract_identifiers(self, text, cache_key=None):
        """
        Extract DOI and ISBN from text with caching
        
        Args:
            text: Text to search
            cache_key: Optional key for caching
            
        Returns:
            dict: Found identifiers
        """
        # Check cache first
        if cache_key and cache_key in self._identifier_cache:
            return self._identifier_cache[cache_key]
            
        # Extract DOI and ISBN
        doi = self.extract_doi(text)
        isbn = self.extract_isbn(text)
        
        result = {'doi': doi, 'isbn': isbn}
        
        # Cache result if key provided
        if cache_key:
            # Maintain cache size
            if len(self._identifier_cache) >= self.cache_size:
                # Remove oldest entry
                oldest_key = next(iter(self._identifier_cache))
                self._identifier_cache.pop(oldest_key)
                
            self._identifier_cache[cache_key] = result
            
        return result
    
    @staticmethod
    def extract_doi(text):
        """
        Extract DOI from text using regex
        
        Args:
            text: Text to search
        
        Returns:
            str: Found DOI or None
        """
        if not text:
            return None
        
        # DOI patterns
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
        Extract ISBN from text using regex
        
        Args:
            text: Text to search
        
        Returns:
            str: Found ISBN or None
        """
        if not text:
            return None
        
        # ISBN patterns
        isbn_patterns = [
            r'\bISBN(?:-13)?[:\s]*(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # ISBN-13
            r'\bISBN(?:-10)?[:\s]*(\d[- ]?(?:\d[- ]?){8}[\dX])\b',   # ISBN-10
            r'\b(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # Bare ISBN-13
            r'\b(\d[- ]?(?:\d[- ]?){8}[\dX])\b'    # Bare ISBN-10
        ]
        
        for pattern in isbn_patterns:
            matches = re.search(pattern, text, re.IGNORECASE)
            if matches and matches.group(1):
                # Remove hyphens and spaces
                return matches.group(1).replace('-', '').replace(' ', '')
        
        return None
    
    def extract_identifiers_only(self, filepath, max_pages=10):
        """
        Extrahiert nur DOI und ISBN aus den ersten Seiten eines PDFs
        
        Args:
            filepath: Pfad zur PDF-Datei
            max_pages: Maximale Anzahl zu verarbeitender Seiten
            
        Returns:
            dict: Dictionary mit gefundenen Identifikatoren
        """
        try:
            # PDF öffnen
            doc = fitz.open(filepath)
            
            # Seitenzahl begrenzen
            pages_to_process = min(max_pages, len(doc))
            
            # Text aus ersten Seiten extrahieren
            text = ""
            for i in range(pages_to_process):
                page = doc[i]
                text += page.get_text() + "\n"
            
            # DOI und ISBN extrahieren
            doi = self.extract_doi(text)
            isbn = self.extract_isbn(text)
            
            # Dokument schließen
            doc.close()
            
            return {
                'doi': doi,
                'isbn': isbn,
                'pages_processed': pages_to_process,
                'total_pages': len(doc)
            }
        except Exception as e:
            logger.error(f"Error extracting identifiers: {e}")
            return {'error': str(e)}

    def chunk_text_with_pages(self, text, pages_info, chunk_size=1000, overlap_size=200):
        """
        Split text into chunks with page tracking
        
        Args:
            text: Full document text
            pages_info: List of page information with positions
            chunk_size: Target chunk size in characters
            overlap_size: Overlap size in characters
        
        Returns:
            list: List of text chunks with page assignments
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # If text is smaller than chunk size, return as single chunk
        if len(text) <= chunk_size:
            # Find page
            page_number = 1
            for page in pages_info:
                if 0 >= page['startPosition'] and len(text) <= page['endPosition']:
                    page_number = page['pageNumber']
                    break
            
            return [{'text': text, 'page_number': page_number}]
        
        # Create position to page mapping
        pos_to_page = {}
        for page in pages_info:
            for pos in range(page['startPosition'], page['endPosition'] + 1):
                pos_to_page[pos] = page['pageNumber']
        
        # Monitor memory usage
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        # Choose chunking method based on text size
        try:
            # For large texts, use simpler chunking
            if len(text) > 100000:  # 100K is a threshold
                text_chunks = self.chunk_text(text, chunk_size, overlap_size)
            else:
                text_chunks = self.chunk_text_semantic(text, chunk_size, overlap_size)
                
            current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            memory_used = current_memory - initial_memory
            
            # Force GC on high memory usage
            if memory_used > 200:  # 200MB threshold
                logger.warning(f"High memory usage in chunking: {memory_used:.2f} MB, forcing GC")
                gc.collect()
                
        except Exception as e:
            logger.error(f"Error in semantic chunking: {e}, falling back to simple chunking")
            text_chunks = self.chunk_text(text, chunk_size, overlap_size)
        
        # Assign pages to chunks
        current_pos = 0
        for chunk in text_chunks:
            # Find chunk position in the original text
            chunk_start = text.find(chunk, current_pos)
            if chunk_start == -1:
                # Fallback if exact position not found
                chunk_start = current_pos
            
            chunk_end = min(chunk_start + len(chunk), len(text) - 1)
            current_pos = chunk_end - overlap_size if overlap_size > 0 else chunk_end
            
            # Count pages for this chunk
            page_counts = {}
            for pos in range(chunk_start, chunk_end + 1):
                if pos in pos_to_page:
                    page_number = pos_to_page[pos]
                    page_counts[page_number] = page_counts.get(page_number, 0) + 1
            
            # Find most common page
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
        
        return chunks
    
    def chunk_text(self, text, chunk_size=1000, overlap_size=200):
        """
        Split text into smaller chunks with overlap
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size
            overlap_size: Overlap size
        
        Returns:
            list: List of text chunks
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # Single chunk for small text
        if len(text) <= chunk_size:
            return [text]
        
        start_index = 0
        
        while start_index < len(text):
            # Calculate end based on chunk size
            end_index = min(start_index + chunk_size, len(text))
            
            # Find natural breakpoint
            if end_index < len(text):
                # Look for paragraph or sentence end near target
                search_start = max(0, end_index - 100)
                search_end = min(len(text), end_index + 100)
                
                # Try paragraph break first
                paragraph_end = text.find('\n\n', search_start, search_end)
                
                # Then sentence end
                sentence_end = -1
                for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    pos = text.find(punct, search_start, search_end)
                    if pos != -1 and (sentence_end == -1 or pos < sentence_end):
                        sentence_end = pos + len(punct) - 1
                
                # Use nearest natural break
                if paragraph_end != -1 and (sentence_end == -1 or 
                                          abs(paragraph_end - end_index) < abs(sentence_end - end_index)):
                    end_index = paragraph_end + 2  # Include '\n\n'
                elif sentence_end != -1:
                    end_index = sentence_end + 1  # Include space after punctuation
            
            # Extract chunk
            chunk = text[start_index:end_index]
            chunks.append(chunk)
            
            # Calculate next start with overlap
            start_index = end_index - overlap_size
            
            # Prevent loops or backward movement
            if start_index <= 0 or start_index >= end_index:
                start_index = end_index
        
        return chunks
    
    def chunk_text_semantic(self, text, chunk_size=1000, overlap_size=200):
        """
        Split text into semantically meaningful chunks using spaCy
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size
            overlap_size: Overlap size
        
        Returns:
            list: List of text chunks
        """
        # Set limits
        MAX_PARAGRAPHS = 1000  # Avoid excessive memory use
        
        if not text or chunk_size <= 0:
            return []
        
        # Truncate very long texts
        if len(text) > self.MAX_TEXT_LENGTH:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {self.MAX_TEXT_LENGTH}")
            text = text[:self.MAX_TEXT_LENGTH]
        
        # Single chunk for small text
        if len(text) <= chunk_size:
            return [text]
        
        # Process large texts in segments
        if len(text) > 20000:
            logger.info("Large text detected, processing in segments")
            segments = []
            segment_size = 10000
            overlap = 1000
            
            for i in range(0, len(text), segment_size - overlap):
                end = min(i + segment_size, len(text))
                segment_text = text[i:end]
                
                # Process each segment with simpler chunking
                segment_chunks = self.chunk_text(segment_text, chunk_size, overlap_size)
                segments.extend(segment_chunks)
                
                # Force GC after each segment
                gc.collect()
                
            return segments
        
        try:
            # Split text into paragraphs
            paragraphs = re.split(r'\n\s*\n', text)
            
            # Limit paragraphs to prevent memory issues
            if len(paragraphs) > MAX_PARAGRAPHS:
                logger.warning(f"Too many paragraphs ({len(paragraphs)}), limiting to {MAX_PARAGRAPHS}")
                paragraphs = paragraphs[:MAX_PARAGRAPHS]
            
            chunks = []
            current_chunk = []
            current_size = 0
            
            # Monitor processing time
            start_time = time.time()
            paragraph_count = 0
            
            # Load spaCy only when needed
            spacy_nlp = get_nlp()
            
            for paragraph in paragraphs:
                # Check for excessive processing time
                if paragraph_count % 50 == 0 and time.time() - start_time > 30:  # 30s max
                    logger.warning("Semantic chunking taking too long, switching to simple chunking")
                    
                    # Add current chunk and process rest with simple chunking
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    
                    remaining_text = ' '.join(paragraphs[paragraph_count:])
                    simple_chunks = self.chunk_text(remaining_text, chunk_size, overlap_size)
                    chunks.extend(simple_chunks)
                    return chunks
                
                paragraph_count += 1
                para_size = len(paragraph)
                
                # Handle paragraphs larger than chunk size
                if para_size > chunk_size:
                    # Save current chunk first
                    if current_size > 0:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    
                    # Split large paragraph into sentences
                    sentence_splitting_start = time.time()
                    
                    try:
                        # Use regex for very large paragraphs
                        if len(paragraph) > 10000:
                            logger.warning(f"Very large paragraph ({len(paragraph)} chars), using regex")
                            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                        else:
                            # Use spaCy for better sentence splitting
                            if time.time() - sentence_splitting_start > 5:  # 5s timeout
                                raise TimeoutError("NLP processing timeout")
                                
                            doc = spacy_nlp(paragraph)
                            sentences = [sent.text for sent in doc.sents]
                        
                    except Exception as e:
                        logger.warning(f"Error in spaCy sentence splitting: {e}, using regex")
                        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    
                    # Combine sentences into chunks
                    sentence_chunk = []
                    sentence_size = 0
                    
                    for sentence in sentences:
                        sent_size = len(sentence)
                        
                        # Check if sentence fits in current chunk
                        if sentence_size + sent_size <= chunk_size:
                            sentence_chunk.append(sentence)
                            sentence_size += sent_size
                        else:
                            # Save current sentence chunk
                            if sentence_size > 0:
                                chunks.append(' '.join(sentence_chunk))
                            
                            # Handle very large sentences
                            if sent_size > chunk_size:
                                # Use simple chunking for large sentences
                                sent_chunks = self.chunk_text(sentence, chunk_size, overlap_size)
                                chunks.extend(sent_chunks)
                            else:
                                # Start new chunk with current sentence
                                sentence_chunk = [sentence]
                                sentence_size = sent_size
                    
                    # Save any remaining sentence chunk
                    if sentence_chunk:
                        chunks.append(' '.join(sentence_chunk))
                
                # Normal case: paragraph fits in chunk
                elif current_size + para_size <= chunk_size:
                    current_chunk.append(paragraph)
                    current_size += para_size
                else:
                    # Finish current chunk and start new one
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [paragraph]
                    current_size = para_size
            
            # Add final chunk
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Add overlap if needed
            if overlap_size > 0 and len(chunks) > 1:
                chunks_with_overlap = [chunks[0]]
                
                for i in range(1, len(chunks)):
                    prev_chunk = chunks[i-1]
                    curr_chunk = chunks[i]
                    
                    # Add overlap from previous chunk
                    if len(prev_chunk) >= overlap_size:
                        overlap_text = prev_chunk[-overlap_size:]
                        chunks_with_overlap.append(overlap_text + curr_chunk)
                    else:
                        # Use whole previous chunk if smaller than overlap size
                        overlap_text = prev_chunk
                        chunks_with_overlap.append(overlap_text + curr_chunk)
                
                chunks = chunks_with_overlap
            
            # Remove empty chunks
            return [chunk for chunk in chunks if chunk.strip()]
            
        except Exception as e:
            logger.error(f"Error in semantic chunking: {str(e)}", exc_info=True)
            # Fall back to simpler chunking
            return self.chunk_text(text, chunk_size, overlap_size)
    
    def process_file(self, file_path, settings=None, progress_callback=None):
        """
        Process a PDF file: extraction, chunking, metadata
        
        Args:
            file_path: Path to PDF file
            settings: Processing settings
            progress_callback: Progress reporting function
        
        Returns:
            dict: Result with text, chunks, metadata, page assignments
        """
        if settings is None:
            settings = {
                'maxPages': 0,
                'chunkSize': 1000,
                'chunkOverlap': 200,
                'performOCR': False
            }
        
        try:
            # Check file size
            if isinstance(file_path, str) and os.path.exists(file_path):
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                
                if file_size_mb > self.MAX_FILE_SIZE_MB:
                    raise ValueError(f"File too large: {file_size_mb:.1f} MB. Maximum allowed size is {self.MAX_FILE_SIZE_MB} MB.")
                
                if file_size_mb > self.WARN_FILE_SIZE_MB:
                    logger.warning(f"Large file detected: {file_size_mb:.1f} MB. Processing may take longer.")
                    if progress_callback:
                        progress_callback(f"Large file ({file_size_mb:.1f} MB). Processing may take longer.", 0)
            
            # Validate PDF format
            valid, message = self.validate_pdf(file_path)
            if not valid:
                raise ValueError(f"Invalid PDF: {message}")
            
            # Progress wrapper
            def progress_wrapper(stage, progress_func=None):
                if not progress_callback:
                    return lambda msg, pct: None
                
                # Split progress by stages
                if stage == 'extraction':
                    return lambda msg, pct: progress_callback(msg, pct * 0.6)
                elif stage == 'chunking':
                    return lambda msg, pct: progress_callback(msg, 60 + pct * 0.3)
                elif stage == 'metadata':
                    return lambda msg, pct: progress_callback(msg, 90 + pct * 0.1)
                else:
                    return progress_callback
            
            # Extract text
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # Create file hash for caching
            file_hash = None
            if isinstance(file_path, str) and os.path.exists(file_path):
                file_hash = f"{os.path.getsize(file_path)}_{os.path.getmtime(file_path)}"
            
            extraction_result = self.extract_text_from_pdf(
                file_path, 
                max_pages=settings.get('maxPages', 0),
                perform_ocr=settings.get('performOCR', False),
                progress_callback=progress_wrapper('extraction')
            )
            
            # Monitor memory usage
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_used = current_memory - start_memory
            logger.info(f"Memory used for extraction: {memory_used:.2f} MB")
            
            # Progress update
            if progress_callback:
                progress_callback("Extracting metadata", 60)
            
            # Extract DOI, ISBN
            extracted_text = extraction_result['text']
            identifiers = self.extract_identifiers(extracted_text, file_hash)
            
            # Progress update
            if progress_callback:
                progress_callback("Creating chunks with page tracking", 65)
            
            # Create chunks with page tracking
            chunks_with_pages = self.chunk_text_with_pages(
                extracted_text,
                extraction_result['pages'],
                chunk_size=settings.get('chunkSize', 1000),
                overlap_size=settings.get('chunkOverlap', 200)
            )
            
            # Validate chunks - remove empty chunks
            chunks_with_pages = [chunk for chunk in chunks_with_pages if chunk.get('text', '').strip()]
            
            # Progress update
            if progress_callback:
                progress_callback("Processing complete", 100)
            
            # Force garbage collection
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
            
            # Force garbage collection
            gc.collect()
            
            # Throw with context
            raise ValueError(f"Failed to process PDF: {str(e)}")

