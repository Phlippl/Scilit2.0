# Backend/api/documents/document_status.py
"""
Status tracking module for document processing
"""
import os
import json
import logging
import threading
from flask import current_app
from datetime import datetime

logger = logging.getLogger(__name__)

# Thread-safe storage for processing status
processing_status = {}
processing_status_lock = threading.Lock()

def save_status_to_file(document_id, status_data):
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
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2, default=str)
            
        return True
    except Exception as e:
        logger.error(f"Error saving status to file: {e}")
        return False

def get_document_status(document_id):
    """
    Gets the processing status of a document with improved error handling
    
    Args:
        document_id: ID of the document
    
    Returns:
        Flask response with processing status
    """
    try:
        # Check in-memory status first
        with processing_status_lock:
            if document_id in processing_status:
                # Also save to file for persistence
                save_status_to_file(document_id, processing_status[document_id])
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
        from flask import g
        user_id = g.user_id if hasattr(g, 'user_id') else 'default_user'
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        metadata_files = list(os.path.join(user_upload_dir).glob(f"{document_id}_*.json"))
        
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