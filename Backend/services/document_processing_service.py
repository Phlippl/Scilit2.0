# Backend/services/document_processor_service.py
import os
import json
import logging
import gc
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from services.pdf_processor import PDFProcessor
from api.documents.document_status import update_document_status

logger = logging.getLogger(__name__)

class DocumentProcessorService:
    """Basisklasse für alle Dokumentenverarbeitungsdienste"""
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
    
    def validate_document(self, filepath: str) -> tuple:
        """Validiert das Dokument und gibt Erfolg und Ergebnis zurück"""
        try:
            is_valid, validation_result = self.pdf_processor.validate_pdf(filepath)
            if not is_valid:
                raise ValueError(f"Invalid PDF file: {validation_result}")
            return True, validation_result
        except Exception as e:
            logger.error(f"Error validating document: {str(e)}")
            return False, str(e)
    
    def process_document(
        self,
        document_id: str,
        filepath: str, 
        settings: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        cleanup_file: bool = False
    ) -> Dict[str, Any]:
        """
        Grundlegende Dokumentenverarbeitung
        
        Args:
            document_id: ID des Dokuments
            filepath: Pfad zur Dokument-Datei
            settings: Verarbeitungseinstellungen
            progress_callback: Optionale Callback-Funktion für Fortschrittsupdates
            cleanup_file: Ob die Datei nach Verarbeitung gelöscht werden soll
            
        Returns:
            dict: Verarbeitungsergebnis
        """
        # Standard-Progress-Callback falls keiner angegeben
        if progress_callback is None:
            progress_callback = lambda msg, pct: update_document_status(
                document_id=document_id,
                status="processing",
                progress=pct,
                message=msg
            )
        
        try:
            # Validierung
            progress_callback("Validating document...", 10)
            valid, validation_result = self.validate_document(filepath)
            if not valid:
                raise ValueError(f"Document validation failed: {validation_result}")
            
            # Verarbeitung
            progress_callback("Extracting text and metadata...", 30)
            pdf_result = self.pdf_processor.process_file(
                filepath,
                settings,
                progress_callback=progress_callback
            )
            
            # Ergebnis
            result = {
                "metadata": pdf_result.get('metadata', {}),
                "chunks": pdf_result.get('chunks', []),
                "totalPages": pdf_result.get('metadata', {}).get('totalPages', 0),
                "processedPages": pdf_result.get('metadata', {}).get('processedPages', 0),
                "text_length": len(pdf_result.get('text', '')),
                "processing_complete": True
            }
            
            # Aufräumen falls gewünscht
            if cleanup_file and os.path.exists(filepath):
                try:
                    os.unlink(filepath)
                    logger.debug(f"Cleaned up file {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to clean up file {filepath}: {e}")
            
            # Garbage Collection
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            
            # Aufräumen bei Fehlern
            if cleanup_file and os.path.exists(filepath):
                try:
                    os.unlink(filepath)
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up file: {cleanup_error}")
            
            # Garbage Collection
            gc.collect()
            
            raise