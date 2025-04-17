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

logger = logging.getLogger(__name__)

# Thread-safe storage for processing status
processing_status = {}
processing_status_lock = threading.Lock()

# Optional callback registry for status updates
status_callbacks = {}


def save_status_to_file(document_id: str, status_data: Dict[str, Any]) -> bool:
    """
    Save document processing status to file with app context
    
    Args:
        document_id: ID of the document
        status_data: Status information dictionary
    
    Returns:
        bool: Success status of file saving
    """
    try:
        status_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status')
        os.makedirs(status_dir, exist_ok=True)
        
        status_file = os.path.join(status_dir, f"{document_id}_status.json")
        
        # Create temp file first for safer writing
        temp_file = f"{status_file}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(status_data, f, indent=2, default=str)
        
        # Atomic file replacement to prevent partial writes
        os.replace(temp_file, status_file)
        
        logger.debug(f"Status saved to file for document {document_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving status to file: {e}")
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


def update_document_status(document_id: str, status: str, progress: Optional[int] = None, 
                          message: Optional[str] = None, result: Optional[Dict[str, Any]] = None) -> bool:
    """
    Update document status with thread safety and persistence
    
    Args:
        document_id: ID of the document
        status: Status string ('processing', 'completed', 'error', etc.)
        progress: Optional progress percentage (0-100)
        message: Optional status message
        result: Optional result data to include
    
    Returns:
        bool: Success status
    """
    try:
        # Create status data object
        status_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add optional fields if provided
        if progress is not None:
            status_data["progress"] = progress
        
        if message is not None:
            status_data["message"] = message
            
        if result is not None:
            status_data["result"] = result
        
        # Update in-memory status with thread safety
        with processing_status_lock:
            processing_status[document_id] = status_data
            
            # Try to save to file if app context is available
            try:
                if current_app:
                    save_status_to_file(document_id, status_data)
            except RuntimeError:
                # No app context available - log but don't fail
                logger.debug(f"No Flask app context for status file saving: {document_id}")
        
        # Trigger any registered callbacks
        if document_id in status_callbacks:
            try:
                for callback in status_callbacks[document_id]:
                    callback(status_data)
            except Exception as callback_err:
                logger.error(f"Error in status callback: {callback_err}")
        
        return True
    except Exception as e:
        logger.error(f"Error updating document status: {e}")
        return False


def get_document_status(document_id: str) -> Dict[str, Any]:
    """
    Gets the processing status of a document with improved error handling
    
    Args:
        document_id: ID of the document
    
    Returns:
        dict: Processing status information
    """
    try:
        # Check in-memory status first
        with processing_status_lock:
            if document_id in processing_status:
                # Also save to file for persistence
                try:
                    if current_app:
                        save_status_to_file(document_id, processing_status[document_id])
                except RuntimeError:
                    # No app context - just log
                    logger.debug(f"No Flask app context for status file saving: {document_id}")
                
                return processing_status[document_id]
            
        # If not in memory, check status file
        status_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_status.json")
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                return status_data
            except Exception as e:
                logger.error(f"Error reading status file: {e}")
        
        # Check metadata file to determine status
        user_id = g.user_id if hasattr(g, 'user_id') else 'default_user'
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        
        try:
            path_obj = Path(user_upload_dir)
            metadata_files = list(path_obj.glob(f"{document_id}_*.json"))
            
            if not metadata_files:
                return {
                    "status": "error",
                    "message": "Document not found"
                }
                
            # Check metadata file to determine status
            try:
                with open(metadata_files[0], 'r') as f:
                    metadata = json.load(f)
                    
                # If processing is flagged as complete
                if metadata.get('processingComplete', False):
                    return {
                        "status": "completed",
                        "progress": 100,
                        "message": "Document processing completed"
                    }
                
                # If processing failed
                if metadata.get('processingError'):
                    return {
                        "status": "error",
                        "progress": 0,
                        "message": metadata.get('processingError', 'Unknown error')
                    }
            except Exception as e:
                logger.error(f"Error reading metadata file for status: {e}")
        except Exception as e:
            logger.error(f"Error accessing user directory: {e}")
        
        # If no status found, assume pending
        return {
            "status": "pending",
            "progress": 0,
            "message": "Document processing not started or status unknown"
        }
            
    except Exception as e:
        logger.error(f"Error retrieving status for document {document_id}: {e}")
        return {
            "status": "error", 
            "message": f"Error retrieving status: {str(e)}"
        }


def register_status_callback(document_id: str, callback: callable) -> bool:
    """
    Register a callback for status updates
    
    Args:
        document_id: Document ID to monitor
        callback: Function to call with status updates
        
    Returns:
        bool: Success status
    """
    try:
        with processing_status_lock:
            if document_id not in status_callbacks:
                status_callbacks[document_id] = []
            status_callbacks[document_id].append(callback)
        return True
    except Exception as e:
        logger.error(f"Error registering status callback: {e}")
        return False


def cleanup_status(document_id: str, delay_seconds: int = 600) -> None:
    """
    Clean up status after a delay (prevent memory leaks)
    
    Args:
        document_id: Document ID to clean up
        delay_seconds: Delay in seconds before cleanup
    """
    def _delayed_cleanup():
        time.sleep(delay_seconds)
        with processing_status_lock:
            if document_id in processing_status:
                del processing_status[document_id]
                logger.debug(f"Cleaned up status for document {document_id}")
            if document_id in status_callbacks:
                del status_callbacks[document_id]
                logger.debug(f"Cleaned up callbacks for document {document_id}")
    
    # Start cleanup in background thread
    cleanup_thread = threading.Thread(target=_delayed_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    logger.debug(f"Scheduled status cleanup for document {document_id} in {delay_seconds}s")