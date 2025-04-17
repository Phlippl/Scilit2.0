# Backend/services/documents/processor.py
"""
Konsolidierter Document-Processor-Service, der die Funktionalität 
von DocumentProcessorService, DocumentStorageService und DocumentAnalysisService vereint.
"""
import os
import json
import logging
import gc
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Tuple, Union

from flask import current_app
from services.pdf import get_pdf_processor
from services.vector_db import store_document_chunks, delete_document as delete_from_vector_db
from services.registry import get
from utils.file_utils import write_json, read_json, get_safe_filepath, cleanup_file
from utils.error_handler import APIError
from utils.metadata_utils import format_metadata_for_storage
from config import config_manager

# Importiere Status-Service für zentralisiertes Status-Management
from services.status_service import update_document_status, cleanup_status

logger = logging.getLogger(__name__)

class DocumentProcessingResult:
    """Standardisiertes Ergebnisobjekt für Dokumentverarbeitung"""
    
    def __init__(self, 
                document_id: str,
                success: bool = True,
                message: str = "",
                metadata: Dict[str, Any] = None,
                chunks: List[Dict[str, Any]] = None,
                text: str = "",
                error: Optional[Exception] = None):
        """
        Initialisiert das Ergebnisobjekt
        
        Args:
            document_id: ID des verarbeiteten Dokuments
            success: Erfolg der Verarbeitung
            message: Statusnachricht
            metadata: Metadaten des Dokuments
            chunks: Extrahierte Textabschnitte
            text: Gesamter extrahierter Text
            error: Aufgetretener Fehler (falls vorhanden)
        """
        self.document_id = document_id
        self.success = success
        self.message = message
        self.metadata = metadata or {}
        self.chunks = chunks or []
        self.text = text
        self.error = error
        self.processing_time = datetime.utcnow().isoformat() + 'Z'
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert das Ergebnis in ein Dictionary"""
        result = {
            "document_id": self.document_id,
            "success": self.success,
            "message": self.message,
            "metadata": self.metadata,
            "chunks_count": len(self.chunks),
            "text_length": len(self.text),
            "processing_time": self.processing_time
        }
        
        # Für API-Antworten nur begrenzte Anzahl an Chunks zurückgeben
        if self.chunks:
            MAX_CHUNKS_IN_RESPONSE = 100
            if len(self.chunks) > MAX_CHUNKS_IN_RESPONSE:
                result["chunks"] = self.chunks[:MAX_CHUNKS_IN_RESPONSE]
                result["limited_chunks"] = True
                result["total_chunks"] = len(self.chunks)
            else:
                result["chunks"] = self.chunks
        
        # Bei Fehler Fehlermeldung hinzufügen
        if self.error:
            result["error"] = str(self.error)
        
        return result

class DocumentProcessor:
    """
    Konsolidierter Document-Processor, der die Funktionalität der separaten Services vereint
    und eine einheitliche API für die Dokumentverarbeitung bietet.
    """
    
    def __init__(self):
        """Initialisiert den Document-Processor"""
        self.pdf_processor = get_pdf_processor()
    
    def process(self, 
               filepath: str, 
               document_id: str, 
               metadata: Optional[Dict[str, Any]] = None,
               settings: Optional[Dict[str, Any]] = None,
               store: bool = True, 
               cleanup_file_after: bool = False) -> DocumentProcessingResult:
        """
        Verarbeitet ein Dokument mit optionaler Speicherung
        
        Args:
            filepath: Pfad zur Dokumentdatei
            document_id: Dokument-ID
            metadata: Optionale Metadaten
            settings: Verarbeitungseinstellungen
            store: Ob das Dokument in der Vektordatenbank gespeichert werden soll
            cleanup_file_after: Ob die Datei nach der Verarbeitung gelöscht werden soll
            
        Returns:
            DocumentProcessingResult: Ergebnis der Verarbeitung
        """
        # Aktiviere Garbage Collection
        gc.enable()
        
        # Standardwerte für Metadaten und Einstellungen
        metadata = metadata or {}
        settings = settings or {}
        
        # Standard-Verarbeitungseinstellungen
        processing_settings = {
            'maxPages': int(settings.get('maxPages', 0)),
            'performOCR': bool(settings.get('performOCR', False)),
            'chunkSize': int(settings.get('chunkSize', 1000)),
            'chunkOverlap': int(settings.get('chunkOverlap', 200)),
            'extractMetadata': bool(settings.get('extractMetadata', True))
        }
        
        try:
            # Status initialisieren
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=0,
                message="Starte Dokumentverarbeitung..."
            )
            
            # Dokument validieren
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=10,
                message="Validiere Dokument..."
            )
            
            valid, validation_result = self._validate_document(filepath)
            if not valid:
                raise ValueError(f"Dokumentvalidierung fehlgeschlagen: {validation_result}")
            
            # PDF verarbeiten
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=30,
                message="Extrahiere Text und Metadaten..."
            )
            
            # Verarbeite PDF mit dem PDF-Processor
            pdf_result = self.pdf_processor.process_file(
                filepath,
                processing_settings,
                progress_callback=lambda msg, pct: update_document_status(
                    document_id=document_id,
                    status="processing",
                    progress=30 + int(pct * 0.5),  # 30% - 80%
                    message=msg
                )
            )
            
            # Metadaten aktualisieren, falls in der Datei gefunden
            extracted_metadata = pdf_result.get('metadata', {})
            if extracted_metadata:
                for key in ['doi', 'isbn', 'totalPages', 'processedPages']:
                    if key in extracted_metadata and extracted_metadata[key]:
                        metadata[key] = extracted_metadata[key]
            
            # Status aktualisieren
            if store:
                update_document_status(
                    document_id=document_id,
                    status="processing",
                    progress=85,
                    message="Speichere Chunks in Vektordatenbank..."
                )
            
            # Speichere Metadaten und Chunks
            chunks = pdf_result.get('chunks', [])
            result = DocumentProcessingResult(
                document_id=document_id,
                success=True,
                message="Dokument erfolgreich verarbeitet",
                metadata=metadata,
                chunks=chunks,
                text=pdf_result.get('text', '')
            )
            
            # In Vektordatenbank speichern, falls gewünscht
            if store and chunks and len(chunks) > 0:
                # Angemessene Chunk-Begrenzung
                max_chunks = min(len(chunks), 500)
                limited_chunks = chunks[:max_chunks]
                
                # Metadaten formatieren
                user_id = metadata.get('user_id', 'default_user')
                formatted_metadata = format_metadata_for_storage(metadata)
                
                # Versuche, in Vektordatenbank zu speichern
                try:
                    store_result = store_document_chunks(
                        document_id=document_id,
                        chunks=limited_chunks,
                        metadata=formatted_metadata
                    )
                    
                    if store_result:
                        logger.info(f"Dokument {document_id} mit {len(limited_chunks)} Chunks gespeichert")
                    else:
                        logger.warning(f"Fehler beim Speichern von Dokument {document_id} in Vektordatenbank")
                        result.message = "Dokument verarbeitet, aber Chunks konnten nicht gespeichert werden"
                        result.success = False
                    
                    # Metadata aktualisieren
                    result.metadata['processed'] = store_result
                    result.metadata['num_chunks'] = len(limited_chunks)
                    result.metadata['chunk_size'] = processing_settings['chunkSize']
                    result.metadata['chunk_overlap'] = processing_settings['chunkOverlap']
                    
                except Exception as e:
                    logger.error(f"Fehler beim Speichern in Vektordatenbank: {e}")
                    result.message = f"Dokument verarbeitet, aber Fehler beim Speichern: {str(e)}"
                    result.success = False
            
            # Speichere die Metadaten als JSON-Datei
            if store:
                metadata_path = f"{filepath}.json"
                # Abschluss der Verarbeitung in Metadaten
                metadata['processingComplete'] = result.success
                metadata['processedDate'] = result.processing_time
                write_json(metadata_path, metadata)
            
            # Bereinige Datei, falls gewünscht
            if cleanup_file_after and os.path.exists(filepath):
                try:
                    cleanup_file(filepath)
                    logger.debug(f"Datei {filepath} nach Verarbeitung gelöscht")
                except Exception as e:
                    logger.warning(f"Fehler beim Löschen der Datei {filepath}: {e}")
            
            # Aktualisiere Status
            status = "completed" if result.success else "completed_with_warnings"
            update_document_status(
                document_id=document_id,
                status=status,
                progress=100,
                message=result.message,
                result=result.to_dict()
            )
            
            # Cleanup Status nach 10 Minuten
            cleanup_status(document_id, 600)
            
            # Garbage Collection
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler bei der Dokumentverarbeitung für {document_id}: {e}", exc_info=True)
            
            # Aktualisiere Status
            update_document_status(
                document_id=document_id,
                status="error",
                progress=0,
                message=f"Fehler bei der Dokumentverarbeitung: {str(e)}"
            )
            
            # Speichere Fehler in Metadaten, falls vorhanden
            if store:
                try:
                    metadata_path = f"{filepath}.json"
                    if os.path.exists(metadata_path):
                        try:
                            existing_metadata = read_json(metadata_path)
                            if existing_metadata:
                                metadata = existing_metadata
                        except Exception:
                            pass
                            
                    metadata['processingComplete'] = False
                    metadata['processingError'] = str(e)
                    metadata['processedDate'] = datetime.utcnow().isoformat() + 'Z'
                    
                    write_json(metadata_path, metadata)
                except Exception as metadata_err:
                    logger.error(f"Fehler beim Speichern der Fehlermetadaten für {document_id}: {metadata_err}")
            
            # Bereinige Datei bei Fehler, falls gewünscht
            if cleanup_file_after and os.path.exists(filepath):
                try:
                    cleanup_file(filepath)
                    logger.debug(f"Datei {filepath} nach Fehler gelöscht")
                except Exception as cleanup_err:
                    logger.warning(f"Fehler beim Löschen der Datei {filepath}: {cleanup_err}")
            
            # Garbage Collection
            gc.collect()
            
            # Fehler zurückgeben
            return DocumentProcessingResult(
                document_id=document_id,
                success=False,
                message=f"Fehler bei der Dokumentverarbeitung: {str(e)}",
                metadata=metadata,
                error=e
            )
    
    def analyze(self, 
               filepath: str, 
               document_id: str,
               settings: Optional[Dict[str, Any]] = None,
               cleanup_file_after: bool = True) -> DocumentProcessingResult:
        """
        Analysiert ein Dokument ohne dauerhafte Speicherung
        
        Args:
            filepath: Pfad zur Dokumentdatei
            document_id: Dokument-ID
            settings: Verarbeitungseinstellungen
            cleanup_file_after: Ob die Datei nach der Analyse gelöscht werden soll
            
        Returns:
            DocumentProcessingResult: Ergebnis der Analyse
        """
        # Verarbeite Dokument ohne Speicherung
        return self.process(
            filepath=filepath,
            document_id=document_id,
            metadata={},
            settings=settings,
            store=False,
            cleanup_file_after=cleanup_file_after
        )
    
    def _validate_document(self, filepath: str) -> Tuple[bool, str]:
        """
        Validiert das Dokument und gibt Erfolg und Ergebnis zurück
        
        Args:
            filepath: Pfad zur Dokumentdatei
            
        Returns:
            tuple: (is_valid, validation_result)
        """
        try:
            is_valid, validation_result = self.pdf_processor.validate_pdf(filepath)
            if not is_valid:
                raise ValueError(f"Ungültige PDF-Datei: {validation_result}")
            return True, validation_result
        except Exception as e:
            logger.error(f"Fehler bei der Dokumentvalidierung: {str(e)}")
            return False, str(e)

# Starten der Dokumentverarbeitung im Hintergrund
def process_document_background(filepath: str, document_id: str, metadata: Dict[str, Any], settings: Dict[str, Any]):
    """
    Verarbeitet ein Dokument im Hintergrund
    
    Args:
        filepath: Pfad zur Dokumentdatei
        document_id: Dokument-ID
        metadata: Dokument-Metadaten
        settings: Verarbeitungseinstellungen
    """
    # Ruft den Document-Processor über die Service-Registry auf
    try:
        # Holt app-Kontext (wenn in Flask-Anwendung)
        try:
            from flask import current_app
            app = current_app._get_current_object()
            with app.app_context():
                document_processor = DocumentProcessor()
                document_processor.process(
                    filepath=filepath,
                    document_id=document_id,
                    metadata=metadata,
                    settings=settings,
                    store=True,
                    cleanup_file_after=False
                )
        except (ImportError, RuntimeError):
            # Bei Ausführung außerhalb von Flask
            document_processor = DocumentProcessor()
            document_processor.process(
                filepath=filepath,
                document_id=document_id,
                metadata=metadata,
                settings=settings,
                store=True,
                cleanup_file_after=False
            )
    except Exception as e:
        logger.error(f"Fehler bei der Hintergrundverarbeitung für {document_id}: {e}", exc_info=True)
        
        # Fehler in Status melden
        update_document_status(
            document_id=document_id,
            status="error",
            progress=0,
            message=f"Fehler bei der Dokumentverarbeitung: {str(e)}"
        )