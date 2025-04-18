# Backend/services/pdf/processor.py
"""
Core PDF processing class with clear responsibilities and delegation to specialized components.
"""
import os
import logging
import gc
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from .extractors import TextExtractor, IdentifierExtractor
from .chunking import TextChunker
from .ocr import OCRProcessor
from utils.identifier_utils import extract_identifiers

logger = logging.getLogger(__name__)

@dataclass
class ProcessingSettings:
    """Settings for PDF processing with sensible defaults"""
    max_pages: int = 0  # 0 means process all pages
    perform_ocr: bool = False
    chunk_size: int = 1000
    chunk_overlap: int = 200
    extract_metadata: bool = True
    max_file_size_mb: int = 50
    warn_file_size_mb: int = 20

class PDFProcessor:
    """
    Core PDF processing class responsible for coordinating PDF-specific operations.
    Delegates to specialized components for specific tasks.
    """
    
    def __init__(self):
        """Initialize the processor and its components"""
        self.text_extractor = TextExtractor()
        self.identifier_extractor = IdentifierExtractor()
        self.text_chunker = TextChunker()
        self.ocr_processor = OCRProcessor()
    
    def validate_pdf(self, filepath: str) -> tuple:
        """
        Validate a PDF file
        
        Args:
            filepath: Path to PDF file
            
        Returns:
            tuple: (is_valid, validation_result)
        """
        return self.text_extractor.validate_pdf(filepath)
    
    def process_file(self, filepath: str, 
                   settings: Optional[Dict[str, Any]] = None,
                   progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Process a PDF file and extract text, chunks, and metadata
        
        Args:
            filepath: Path to PDF file
            settings: Processing settings
            progress_callback: Callback for progress updates
            
        Returns:
            dict: Processing result with text, chunks, metadata
        """
        # Use standard settings if none provided
        if not settings:
            settings = {}
        
        # Convert to ProcessingSettings
        proc_settings = ProcessingSettings(
            max_pages=int(settings.get('maxPages', 0)),
            perform_ocr=bool(settings.get('performOCR', False)),
            chunk_size=int(settings.get('chunkSize', 1000)),
            chunk_overlap=int(settings.get('chunkOverlap', 200)),
            extract_metadata=bool(settings.get('extractMetadata', True)),
            max_file_size_mb=int(settings.get('maxFileSizeMB', 50)),
            warn_file_size_mb=int(settings.get('warnFileSizeMB', 20))
        )
        
        logger.info(f"Processing file: {filepath}")
        
        try:
            # Check file size
            if isinstance(filepath, str) and os.path.exists(filepath):
                file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                
                if file_size_mb > proc_settings.max_file_size_mb:
                    logger.error(f"File too large: {file_size_mb:.1f} MB, max: {proc_settings.max_file_size_mb} MB")
                    raise ValueError(f"File too large: {file_size_mb:.1f} MB. Maximum allowed size is {proc_settings.max_file_size_mb} MB.")
                
                if file_size_mb > proc_settings.warn_file_size_mb:
                    logger.warning(f"Large file detected: {file_size_mb:.1f} MB. Processing may take longer.")
                    if progress_callback:
                        progress_callback(f"Large file ({file_size_mb:.1f} MB). Processing may take longer.", 0)
            
            # Validate PDF format
            valid, message = self.validate_pdf(filepath)
            if not valid:
                logger.error(f"Invalid PDF: {message}")
                raise ValueError(f"Invalid PDF: {message}")
            
            # Create progress wrapper for different stages
            def progress_wrapper(stage, callback=progress_callback):
                if not callback:
                    return lambda msg, pct: None
                
                # Divide progress by stages
                if stage == 'extraction':
                    return lambda msg, pct: callback(msg, pct * 0.6)
                elif stage == 'chunking':
                    return lambda msg, pct: callback(msg, 60 + pct * 0.3)
                elif stage == 'metadata':
                    return lambda msg, pct: callback(msg, 90 + pct * 0.1)
                else:
                    return callback
            
            # Extract text - delegate to TextExtractor
            extraction_result = self.text_extractor.extract_text(
                filepath,
                max_pages=proc_settings.max_pages,
                perform_ocr=proc_settings.perform_ocr,
                progress_callback=progress_wrapper('extraction')
            )
            
            # Progress update
            if progress_callback:
                progress_callback("Extracting metadata", 60)
            
            # Extract metadata - use centralized utility
            metadata = {}
            if proc_settings.extract_metadata:
                extracted_text = extraction_result['text']
                # Use centralized identifier extraction
                identifiers = extract_identifiers(extracted_text)
                metadata = {
                    'doi': identifiers['doi'],
                    'isbn': identifiers['isbn'],
                    'totalPages': extraction_result['totalPages'],
                    'processedPages': extraction_result['processedPages']
                }
                logger.info(f"Extracted identifiers: {identifiers}")
            
            # Progress update
            if progress_callback:
                progress_callback("Creating chunks with page tracking", 65)
            
            # Create chunks with page mapping - delegate to TextChunker
            chunks_with_pages = self.text_chunker.chunk_text_with_pages(
                extraction_result['text'],
                extraction_result['pages'],
                chunk_size=proc_settings.chunk_size,
                overlap_size=proc_settings.chunk_overlap
            )
            
            # Validate chunks - remove empty chunks
            chunks_with_pages = [chunk for chunk in chunks_with_pages if chunk.get('text', '').strip()]
            logger.info(f"Created {len(chunks_with_pages)} non-empty chunks")
            
            # Progress update
            if progress_callback:
                progress_callback("Processing complete", 100)
            
            # Force garbage collection
            gc.collect()

            result = {
                'text': extraction_result['text'],
                'chunks': chunks_with_pages,
                'metadata': metadata,
                'pages': extraction_result['pages']
            }
            
            logger.info(f"Processing complete: {len(result['text'])} chars, {len(result['chunks'])} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Error in PDF processing: {e}", exc_info=True)
            
            # Force garbage collection
            gc.collect()
            
            # Re-raise with context
            raise ValueError(f"Failed to process PDF: {str(e)}")
    
    def extract_identifiers_only(self, filepath: str, max_pages: int = 10) -> Dict[str, Any]:
        """
        Extract only identifiers (DOI, ISBN) from a PDF
        
        Args:
            filepath: Path to PDF file
            max_pages: Maximum number of pages to process
            
        Returns:
            dict: Extracted identifiers
        """
        # Delegate to IdentifierExtractor
        return self.identifier_extractor.extract_identifiers_from_pdf(filepath, max_pages)
    
    def cleanup_cache(self):
        """Clean up internal caches"""
        self.text_extractor.cleanup_cache()
        self.identifier_extractor.cleanup_cache()