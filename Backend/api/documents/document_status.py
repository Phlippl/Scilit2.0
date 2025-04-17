# Backend/api/documents/document_status.py
"""
Status tracking module for document processing with enhanced thread safety and persistence
"""
import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Union
from flask import current_app, g
from datetime import datetime
from pathlib import Path
from services.status_services import get_status_service

logger = logging.getLogger(__name__)

# Thread-safe storage for processing status
processing_status = {}
processing_status_lock = None

# Optional callback registry for status updates
status_callbacks = {}

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
    """Alte Funktion für Abwärtskompatibilität"""
    # Diese Funktion wird beibehalten, ruft aber intern den neuen Service auf
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
    Load document processing status from file
    
    Args:
        document_id: ID of the document
    
    Returns:
        dict: Status data or None if not found
    """
    try:
        status_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_status.json")
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            return status_data
        return None
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
                
            global processing_status
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


def register_status_callback(document_id: str, callback: callable) -> bool:
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
    except Exception as e:
        logger.error(f"Error scheduling status cleanup: {e}")