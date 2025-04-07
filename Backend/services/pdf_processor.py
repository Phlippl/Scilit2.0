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
import json
from typing import Dict, List, Any, Optional, Union
import gc 

# PyMuPDF import with error handling
try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF not found. Please install it with: pip install PyMuPDF")

# spaCy import
import spacy

logger = logging.getLogger(__name__)

# Load appropriate spaCy model with fallbacks
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


class PDFProcessor:
    """Class for processing PDF files with improved performance and error handling"""
    
    def __init__(self):
        # Create thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        # Create OCR process pool (Tesseract is CPU intensive)
        self.ocr_executor = ThreadPoolExecutor(max_workers=2)
    
    def extract_text_from_pdf(self, pdf_file, max_pages=0, perform_ocr=False, progress_callback=None):
        """
        Extract text from a PDF file with improved page tracking and parallel OCR
        
        Args:
            pdf_file: PDF file (file path or bytes)
            max_pages: Maximum number of pages to process (0 = all)
            perform_ocr: Perform OCR for pages with little text
            progress_callback: Optional callback function for progress updates
        
        Returns:
            dict: Result with text and detailed page info
        """
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
            
            # Extract text from each page
            for i in range(pages_to_process):
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
                
                if len(page_text) > 15000:  # 15K characters threshold
                    logger.warning(f"Very large text block on page {i+1} ({len(page_text)} chars), breaking it up")
                    # Use natural paragraph breaks when possible
                    paragraph_sections = re.split(r'\n\s*\n', page_text)
                    # Rejoin with clear paragraph separators
                    page_text = '\n\n'.join(paragraph_sections)

                # Add to total text
                result['text'] += page_text + ' '
                
                # Update end position
                page_info['endPosition'] = len(result['text']) - 1
                
                # Check if page has little text -> OCR candidate
                if perform_ocr and len(page_text.strip()) < 100:
                    ocr_page_numbers.append(i)
                
                result['pages'].append(page_info)
            
            gc.collect()

            # Perform OCR for pages with little text using thread pool
            if perform_ocr and ocr_page_numbers:
                if progress_callback:
                    progress_callback(f"Performing OCR on {len(ocr_page_numbers)} pages", 50)
                
                # Prepare list of pages for OCR
                ocr_tasks = [(doc, page_num, 300) for page_num in ocr_page_numbers]
                
                # Process OCR in parallel using thread pool
                ocr_results_futures = []
                for task in ocr_tasks:
                    future = self.ocr_executor.submit(self._perform_ocr_on_page, *task)
                    ocr_results_futures.append(future)
                
                # Collect OCR results
                ocr_results = {}
                for i, future in enumerate(ocr_results_futures):
                    try:
                        page_num, ocr_text = future.result()
                        ocr_results[page_num] = ocr_text
                        
                        # Report progress
                        if progress_callback:
                            progress_callback(f"OCR processing: {i+1}/{len(ocr_results_futures)}", 
                                             50 + int((i+1)/len(ocr_results_futures) * 45))
                    except Exception as e:
                        logger.error(f"Error in OCR process: {e}")
                
                # Add OCR results to pages
                for page_num, ocr_text in ocr_results.items():
                    # Convert from 0-based to 1-based page number for index
                    idx = page_num - 1
                    if idx < len(result['pages']):
                        # Update text or add OCR result
                        orig_text = result['pages'][idx]['text']
                        if not orig_text.strip():
                            result['pages'][idx]['text'] = ocr_text
                            # Update total text
                            result['text'] = result['text'].replace(orig_text, ocr_text)
                        else:
                            # Add text if original exists
                            result['pages'][idx]['text'] += ' ' + ocr_text
                            result['text'] += ' ' + ocr_text
            
            # Clean up
            doc.close()
            if isinstance(pdf_file, bytes) and os.path.exists(pdf_path):
                os.unlink(pdf_path)
            
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
            
            # Render page
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
            
            # Save as image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(img)
            
            # Page number (1-based) for the result
            return page_idx + 1, ocr_text
        except Exception as e:
            logger.error(f"Error performing OCR on page {page_idx + 1}: {e}")
            return page_idx + 1, ""
    
    @staticmethod
    def extract_doi(text):
        """
        Extract DOI from text using regex
        
        Args:
            text: Text to search for DOI
        
        Returns:
            str: Found DOI or None
        """
        if not text:
            return None
        
        # DOI patterns (improved for better matching)
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
        Extract ISBN from text using regex
        
        Args:
            text: Text to search for ISBN
        
        Returns:
            str: Found ISBN or None
        """
        if not text:
            return None
        
        # ISBN patterns for ISBN-10 and ISBN-13
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
    
    def chunk_text_with_pages(self, text, pages_info, chunk_size=1000, overlap_size=200):
        """
        Split text into chunks with page tracking and overlap
        
        Args:
            text: Full text
            pages_info: List with page information including start and end positions
            chunk_size: Target chunk size in characters
            overlap_size: Overlap size in characters
        
        Returns:
            list: List of text chunks with page assignments
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # If text is smaller than chunk_size, return as single chunk
        if len(text) <= chunk_size:
            # Determine page number
            page_number = None
            for page in pages_info:
                if 0 >= page['startPosition'] and len(text) <= page['endPosition']:
                    page_number = page['pageNumber']
                    break
            
            return [{'text': text, 'page_number': page_number or 1}]
        
        # Create mapping from text position to page number
        pos_to_page = {}
        for page in pages_info:
            for pos in range(page['startPosition'], page['endPosition'] + 1):
                pos_to_page[pos] = page['pageNumber']
        
        # Split text into semantically meaningful chunks
        semantic_chunks = self.chunk_text_semantic(text, chunk_size, overlap_size)
        
        # For each chunk, determine the page number
        current_pos = 0
        for chunk in semantic_chunks:
            # Find position of chunk in original text
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
            
            # Most frequent page number for this chunk
            most_common_page = None
            max_count = 0
            for page_num, count in page_counts.items():
                if count > max_count:
                    max_count = count
                    most_common_page = page_num
            
            chunks.append({
                'text': chunk,
                'page_number': most_common_page or 1  # Default to page 1 if no mapping found
            })
        
        return chunks
    
    @staticmethod
    def chunk_text(text, chunk_size=1000, overlap_size=200):
        """
        Split text into smaller chunks with configurable size and overlap
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            overlap_size: Overlap size in characters
        
        Returns:
            list: List of text chunks
        """
        if not text or chunk_size <= 0:
            return []
        
        chunks = []
        
        # If text is smaller than chunk_size, return as single chunk
        if len(text) <= chunk_size:
            return [text]
        
        start_index = 0
        
        while start_index < len(text):
            # Calculate end index based on chunk size
            end_index = min(start_index + chunk_size, len(text))
            
            # Find natural breakpoint
            if end_index < len(text):
                # Look for paragraph end or sentence end within range around end_index
                search_start = max(0, end_index - 100)
                search_end = min(len(text), end_index + 100)
                
                paragraph_end = text.find('\n\n', search_start, search_end)
                sentence_end = -1
                
                # Look for sentence end (period followed by space or newline)
                for punct in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    search_start = max(0, end_index - 50)
                    search_end = min(len(text), end_index + 50)
                    pos = text.find(punct, search_start, search_end)
                    if pos != -1 and (sentence_end == -1 or pos < sentence_end):
                        sentence_end = pos + len(punct) - 1
                
                # Use the nearest natural breakpoint
                if paragraph_end != -1 and (sentence_end == -1 or abs(paragraph_end - end_index) < abs(sentence_end - end_index)):
                    end_index = paragraph_end + 2  # +2 for '\n\n'
                elif sentence_end != -1:
                    end_index = sentence_end + 1  # +1 for space after period
            
            # Extract chunk
            chunk = text[start_index:end_index]
            chunks.append(chunk)
            
            # Calculate start index for next chunk (with overlap)
            start_index = end_index - overlap_size
            
            # Ensure we don't go backwards
            if start_index <= 0 or start_index >= end_index:
                start_index = end_index
        
        return chunks
    
    def chunk_text_semantic(self, text, chunk_size=1000, overlap_size=200):
        """
        Split text into semantically meaningful chunks using spaCy with 
        robust error handling and performance safeguards
        """
        # Set maximum runtime and text length limits
        MAX_TEXT_LENGTH = 1_000_000  # 1 million characters max
        MAX_PARAGRAPHS = 5000  # Prevent excessive memory usage
        
        if not text or chunk_size <= 0:
            return []
        
        # Truncate very long texts to prevent memory issues
        if len(text) > MAX_TEXT_LENGTH:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {MAX_TEXT_LENGTH} chars")
            text = text[:MAX_TEXT_LENGTH]
        
        # If text is smaller than chunk_size, return as single chunk
        if len(text) <= chunk_size:
            return [text]
        
        # For extremely large texts, break into segments first
        if len(text) > 100000:  # 100K threshold
            logger.info(f"Text too large for single semantic chunking, processing in segments")
            segments = []
            # Process 50K segments with 5K overlap for context
            segment_size = 50000
            overlap = 5000
            
            for i in range(0, len(text), segment_size - overlap):
                end = min(i + segment_size, len(text))
                segment_text = text[i:end]
                
                # Process each segment with simpler chunking to avoid excessive processing
                segment_chunks = self.chunk_text(segment_text, chunk_size, overlap_size)
                segments.extend(segment_chunks)
                
                # Force garbage collection after each segment
                gc.collect()
                
            return segments
        
        chunks = []
        
        try:
            # Split text into paragraphs with safeguards
            paragraphs = re.split(r'\n\s*\n', text)
            
            # Apply limits to prevent excessive resource usage
            if len(paragraphs) > MAX_PARAGRAPHS:
                logger.warning(f"Too many paragraphs ({len(paragraphs)}), limiting to {MAX_PARAGRAPHS}")
                paragraphs = paragraphs[:MAX_PARAGRAPHS]
            
            current_chunk = []
            current_size = 0
            
            # Process time monitoring variables
            start_time = time.time()
            paragraph_count = 0
            
            for paragraph in paragraphs:
                # Check for excessive processing time
                if paragraph_count % 100 == 0 and time.time() - start_time > 120:  # 2 minutes max
                    logger.warning("Semantic chunking taking too long, switching to simple chunking")
                    # Add any accumulated text and process the rest with simple chunking
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    
                    # Use the faster simple chunker for remaining paragraphs
                    remaining_text = ' '.join(paragraphs[paragraph_count:])
                    simple_chunks = self.chunk_text(remaining_text, chunk_size, overlap_size)
                    chunks.extend(simple_chunks)
                    return chunks
                
                paragraph_count += 1
                para_size = len(paragraph)
                
                # If paragraph alone is larger than chunk_size, subdivide
                if para_size > chunk_size:
                    # If we already have something in current chunk, save it first
                    if current_size > 0:
                        chunks.append(' '.join(current_chunk))
                        current_chunk = []
                        current_size = 0
                    
                    # Split large paragraph into sentences using spaCy with timeout protection
                    sentence_splitting_start = time.time()
                    try:
                        # Set a timeout for spaCy processing
                        if len(paragraph) > 50000:  # Very large paragraph
                            logger.warning(f"Very large paragraph ({len(paragraph)} chars), using regex sentence splitting")
                            # Fallback to regex sentence splitting for very large paragraphs
                            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                        else:
                            # Use spaCy for better sentence splitting
                            # Set a timeout to prevent long processing
                            nlp_timeout = 20  # 20 seconds max for NLP processing
                            if time.time() - sentence_splitting_start > nlp_timeout:
                                raise TimeoutError("NLP processing timeout")
                                
                            doc = nlp(paragraph)
                            sentences = [sent.text for sent in doc.sents]
                        
                    except Exception as e:
                        logger.warning(f"Error in spaCy sentence splitting: {e}, falling back to regex")
                        # Fallback to regex sentence splitting
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
                            # Save current sentence chunk if not empty
                            if sentence_size > 0:
                                chunks.append(' '.join(sentence_chunk))
                            
                            # If sentence itself is too large, chunk it directly
                            if sent_size > chunk_size:
                                # Use simple chunking for very large sentences
                                sent_chunks = self.chunk_text(sentence, chunk_size, overlap_size)
                                chunks.extend(sent_chunks)
                            else:
                                # Start new chunk with current sentence
                                sentence_chunk = [sentence]
                                sentence_size = sent_size
                    
                    # Save remaining sentence chunk if exists
                    if sentence_chunk:
                        chunks.append(' '.join(sentence_chunk))
                
                # Normal case: Paragraph potentially fits in a chunk
                elif current_size + para_size <= chunk_size:
                    current_chunk.append(paragraph)
                    current_size += para_size
                else:
                    # Finish current chunk and start new one
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [paragraph]
                    current_size = para_size
            
            # Add last chunk if exists
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Add overlap if needed
            if overlap_size > 0 and len(chunks) > 1:
                chunks_with_overlap = [chunks[0]]
                for i in range(1, len(chunks)):
                    prev_chunk = chunks[i-1]
                    curr_chunk = chunks[i]
                    
                    # Add overlap
                    if len(prev_chunk) >= overlap_size:
                        overlap_text = prev_chunk[-overlap_size:]
                        chunks_with_overlap.append(overlap_text + curr_chunk)
                    else:
                        chunks_with_overlap.append(curr_chunk)
                
                chunks = chunks_with_overlap
            
            # Final sanity check to ensure we don't return empty chunks
            chunks = [chunk for chunk in chunks if chunk.strip()]
            return chunks
        
        except Exception as e:
            # Log the full error details
            logger.error(f"Error in semantic chunking: {str(e)}", exc_info=True)
            
            # Fallback to simpler chunking method for robustness
            logger.warning("Falling back to simple chunking due to error")
            return self.chunk_text(text, chunk_size, overlap_size)
    
    def process_file(self, file_path, settings=None, progress_callback=None):
        """
        Process a PDF file completely: extraction, chunking, metadata
        
        Args:
            file_path: Path to PDF file
            settings: Processing settings (max_pages, chunk_size, etc.)
            progress_callback: Optional callback function for progress updates
        
        Returns:
            dict: Result with text, chunks, metadata and page assignments
        """
        if settings is None:
            settings = {
                'maxPages': 0,
                'chunkSize': 1000,
                'chunkOverlap': 200,
                'performOCR': False
            }
        
        # Define a progress wrapper to divide progress across stages
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
        
        # Extract text with progress reporting
        extraction_result = self.extract_text_from_pdf(
            file_path, 
            max_pages=settings.get('maxPages', 0),
            perform_ocr=settings.get('performOCR', False),
            progress_callback=progress_wrapper('extraction')
        )
        
        # Progress update
        if progress_callback:
            progress_callback("Extracting metadata", 60)
        
        # Extract DOI, ISBN
        extracted_text = extraction_result['text']
        doi = self.extract_doi(extracted_text)
        isbn = self.extract_isbn(extracted_text)
        
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
        
        # Progress update
        if progress_callback:
            progress_callback("Processing complete", 100)
        
        gc.collect()

        return {
            'text': extracted_text,
            'chunks': chunks_with_pages,
            'metadata': {
                'doi': doi,
                'isbn': isbn,
                'totalPages': extraction_result['totalPages'],
                'processedPages': extraction_result['processedPages']
            },
            'pages': extraction_result['pages']
        }