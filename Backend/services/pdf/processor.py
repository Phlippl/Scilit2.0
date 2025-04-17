# Backend/services/pdf/processor.py
"""
Hauptklasse zur PDF-Verarbeitung mit klaren Verantwortlichkeiten
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
    """Einstellungen für die PDF-Verarbeitung"""
    max_pages: int = 0
    perform_ocr: bool = False
    chunk_size: int = 1000
    chunk_overlap: int = 200
    extract_metadata: bool = True
    max_file_size_mb: int = 50
    warn_file_size_mb: int = 20

class PDFProcessor:
    """
    Modulare PDF-Verarbeitungsklasse mit klaren Verantwortlichkeiten
    """
    
    def __init__(self):
        """Initialisiert den PDF-Processor mit seinen Komponenten"""
        self.text_extractor = TextExtractor()
        self.identifier_extractor = IdentifierExtractor()
        self.text_chunker = TextChunker()
        self.ocr_processor = OCRProcessor()
        
        # Cache für Extraktionsergebnisse
        self._extraction_cache = {}
        self._max_cache_size = 50
    
    def validate_pdf(self, filepath: str) -> tuple:
        """
        Validiert ein PDF-Dokument
        
        Args:
            filepath: Pfad zur PDF-Datei
            
        Returns:
            tuple: (is_valid, validation_result)
        """
        return self.text_extractor.validate_pdf(filepath)
    
    def process_file(self, filepath: str, 
                    settings: Optional[Dict[str, Any]] = None,
                    progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Verarbeitet eine PDF-Datei vollständig
        
        Args:
            filepath: Pfad zur PDF-Datei
            settings: Verarbeitungseinstellungen
            progress_callback: Callback-Funktion für Fortschrittsaktualisierungen
            
        Returns:
            dict: Verarbeitungsergebnis mit Text, Chunks, Metadaten
        """
        # Standardeinstellungen verwenden wenn keine angegeben
        if not settings:
            settings = {
                'maxPages': 0,
                'performOCR': False,
                'chunkSize': 1000,
                'chunkOverlap': 200
            }
        
        # Konvertiere zu ProcessingSettings
        proc_settings = ProcessingSettings(
            max_pages=int(settings.get('maxPages', 0)),
            perform_ocr=bool(settings.get('performOCR', False)),
            chunk_size=int(settings.get('chunkSize', 1000)),
            chunk_overlap=int(settings.get('chunkOverlap', 200)),
            extract_metadata=bool(settings.get('extractMetadata', True)),
            max_file_size_mb=int(settings.get('maxFileSizeMB', 50)),
            warn_file_size_mb=int(settings.get('warnFileSizeMB', 20))
        )
        
        logger.info(f"Processing file: {filepath}, settings: {settings}")
        
        try:
            # Prüfe Dateigröße
            if isinstance(filepath, str) and os.path.exists(filepath):
                file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                
                if file_size_mb > proc_settings.max_file_size_mb:
                    logger.error(f"File too large: {file_size_mb:.1f} MB, max: {proc_settings.max_file_size_mb} MB")
                    raise ValueError(f"File too large: {file_size_mb:.1f} MB. Maximum allowed size is {proc_settings.max_file_size_mb} MB.")
                
                if file_size_mb > proc_settings.warn_file_size_mb:
                    logger.warning(f"Large file detected: {file_size_mb:.1f} MB. Processing may take longer.")
                    if progress_callback:
                        progress_callback(f"Large file ({file_size_mb:.1f} MB). Processing may take longer.", 0)
            
            # Validiere PDF-Format
            valid, message = self.validate_pdf(filepath)
            if not valid:
                logger.error(f"Invalid PDF: {message}")
                raise ValueError(f"Invalid PDF: {message}")
            
            # Erstelle Wrapper für Fortschrittsrückmeldungen
            def progress_wrapper(stage, callback=progress_callback):
                if not callback:
                    return lambda msg, pct: None
                
                # Teile Fortschritt nach Phasen auf
                if stage == 'extraction':
                    return lambda msg, pct: callback(msg, pct * 0.6)
                elif stage == 'chunking':
                    return lambda msg, pct: callback(msg, 60 + pct * 0.3)
                elif stage == 'metadata':
                    return lambda msg, pct: callback(msg, 90 + pct * 0.1)
                else:
                    return callback
            
            # Text extrahieren
            extraction_result = self.text_extractor.extract_text(
                filepath,
                max_pages=proc_settings.max_pages,
                perform_ocr=proc_settings.perform_ocr,
                progress_callback=progress_wrapper('extraction')
            )
            
            # Fortschrittsupdate
            if progress_callback:
                progress_callback("Extracting metadata", 60)
            
            # DOI, ISBN extrahieren
            metadata = {}
            if proc_settings.extract_metadata:
                extracted_text = extraction_result['text']
                # Verwende zentralisierte Funktion
                identifiers = extract_identifiers(extracted_text)
                metadata = {
                    'doi': identifiers['doi'],
                    'isbn': identifiers['isbn'],
                    'totalPages': extraction_result['totalPages'],
                    'processedPages': extraction_result['processedPages']
                }
                logger.info(f"Extracted identifiers: {identifiers}")
            
            # Fortschrittsupdate
            if progress_callback:
                progress_callback("Creating chunks with page tracking", 65)
            
            # Chunks mit Seitenzuordnung erstellen
            chunks_with_pages = self.text_chunker.chunk_text_with_pages(
                extraction_result['text'],
                extraction_result['pages'],
                chunk_size=proc_settings.chunk_size,
                overlap_size=proc_settings.chunk_overlap
            )
            
            # Validiere Chunks - entferne leere Chunks
            chunks_with_pages = [chunk for chunk in chunks_with_pages if chunk.get('text', '').strip()]
            logger.info(f"Created {len(chunks_with_pages)} non-empty chunks")
            
            # Fortschrittsupdate
            if progress_callback:
                progress_callback("Processing complete", 100)
            
            # Erzwinge Garbage Collection
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
            
            # Erzwinge Garbage Collection
            gc.collect()
            
            # Werfe mit Kontext
            raise ValueError(f"Failed to process PDF: {str(e)}")
    
    def extract_identifiers_only(self, filepath: str, max_pages: int = 10) -> Dict[str, Any]:
        """
        Extrahiert nur Identifikatoren (DOI, ISBN) aus einem PDF
        
        Args:
            filepath: Pfad zur PDF-Datei
            max_pages: Maximale Anzahl zu verarbeitender Seiten
            
        Returns:
            dict: Extrahierte Identifikatoren
        """
        return self.identifier_extractor.extract_identifiers_from_pdf(filepath, max_pages)
    
    def cleanup_cache(self):
        """Bereinigt den internen Cache"""
        self._extraction_cache.clear()
        self.text_extractor.cleanup_cache()
        self.identifier_extractor.cleanup_cache()