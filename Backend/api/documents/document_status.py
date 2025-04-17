# Backend/api/documents/document_status.py
"""
Status tracking module for document processing with enhanced thread safety and persistence
"""
import os
import json
import logging
import threading
from typing import Dict, Any, Optional, List, Union, Callable
from flask import current_app
from services.status_service import get_status_service

logger = logging.getLogger(__name__)

# Thread-safe storage for processing status - kept for backward compatibility
processing_status = {}
processing_status_lock = threading.RLock()

def initialize_status_service():
    """Initialisiert den StatusService mit dem richtigen Verzeichnis"""
    try:
        status_service = get_status_service()
        upload_folder = current_app.config.get('UPLOAD_FOLDER', './uploads')
        status_dir = os.path.join(upload_folder, 'status')
        os.makedirs(status_dir, exist_ok=True)
        status_service.set_storage_dir(status_dir)
        logger.info(f"Status service initialized with directory: {status_dir}")
    except Exception as e:
        logger.error(f"Error initializing status service: {e}")

def save_status_to_file(document_id, status_data):
    """Legacy Funktion für Abwärtskompatibilität"""
    # Diese Funktion verwendet intern den neuen Service
    try:
        status_service = get_status_service()
        status = status_data.get("status", "unknown")
        progress = status_data.get("progress")
        message = status_data.get("message")
        result = status_data.get("result")
        
        return status_service.update_status(
            status_id=document_id,
            status=status,
            progress=progress,
            message=message,
            result=result
        )
    except Exception as e:
        logger.error(f"Error in compatibility save_status_to_file: {e}")
        return False


def load_status_from_file(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Legacy Funktion für Abwärtskompatibilität - ruft den StatusService auf
    """
    try:
        return get_document_status(document_id)
    except Exception as e:
        logger.error(f"Error loading status from file: {e}")
        return None


def update_document_status(
    document_id: str, 
    status: str, 
    progress: Optional[int] = None, 
    message: Optional[str] = None, 
    result: Optional[Dict[str, Any]] = None
) -> bool:
    """Aktualisiert den Dokumentenstatus über den zentralen Service"""
    try:
        # Service verwenden
        status_service = get_status_service()
        
        # Status aktualisieren
        success = status_service.update_status(
            status_id=document_id,
            status=status,
            progress=progress,
            message=message,
            result=result
        )
        
        # Für Abwärtskompatibilität: Auch in altem Status-Dict speichern
        if success:
            status_data = {
                "status": status,
                "progress": progress if progress is not None else 0,
                "message": message if message is not None else ""
            }
            if result is not None:
                status_data["result"] = result
                
            with processing_status_lock:
                processing_status[document_id] = status_data
        
        return success
    except Exception as e:
        logger.error(f"Error updating document status: {e}")
        return False

def get_document_status(document_id: str) -> Dict[str, Any]:
    """Ruft den Dokumentenstatus ab"""
    try:
        status_service = get_status_service()
        return status_service.get_status(document_id)
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        return {
            "status": "error",
            "message": f"Error retrieving status: {str(e)}"
        }


def register_status_callback(document_id: str, callback: Callable) -> bool:
    """Registriert einen Callback für Status-Updates"""
    try:
        status_service = get_status_service()
        return status_service.register_observer(document_id, callback)
    except Exception as e:
        logger.error(f"Error registering status callback: {e}")
        return False


def cleanup_status(document_id: str, delay_seconds: int = 600) -> None:
    """Bereinigt Status nach Verzögerung"""
    try:
        status_service = get_status_service()
        status_service.cleanup_status(document_id, delay_seconds)
        
        # Lösche auch aus dem alten Dict für vollständige Bereinigung
        if delay_seconds == 0:  # Sofortige Bereinigung
            with processing_status_lock:
                if document_id in processing_status:
                    del processing_status[document_id]
                    logger.debug(f"Removed document {document_id} from legacy status dict")
        else:
            # Verzögerte Bereinigung
            def delayed_cleanup():
                import time
                time.sleep(delay_seconds)
                with processing_status_lock:
                    if document_id in processing_status:
                        del processing_status[document_id]
                        logger.debug(f"Removed document {document_id} from legacy status dict after delay")
                        
            threading.Thread(target=delayed_cleanup, daemon=True).start()
            
    except Exception as e:
        logger.error(f"Error scheduling status cleanup: {e}")