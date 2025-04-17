# Backend/api/documents/document_processing.py
"""
Background document processing module
"""
import os
import json
import logging
import uuid
import time
import threading
import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from concurrent.futures import ThreadPoolExecutor

# Import required services and modules
from services.pdf import get_pdf_processor
from services.pdf.processor import ProcessingSettings
from services.vector_db import store_document_chunks, delete_document as delete_from_vector_db
from .document_status import update_document_status, cleanup_status, processing_status, processing_status_lock, save_status_to_file, get_document_status
from utils.metadata_utils import validate_metadata, format_metadata_for_storage
from services.document_processing_service import DocumentProcessorService
from services.document_storage_service import DocumentStorageService


# Import metadata retrieval functions
try:
    from api.metadata import fetch_metadata_from_crossref
except ImportError:
    def fetch_metadata_from_crossref(doi):
        logger.warning(f"Metadata API not available. Cannot fetch metadata for DOI")
        return None

# Configure logging
logger = logging.getLogger(__name__)

# Create thread pool executor for background tasks
executor = ThreadPoolExecutor(max_workers=2)

def get_executor():
    """
    Returns the thread pool executor, creates a new one if needed
    
    Returns:
        ThreadPoolExecutor: The thread pool executor for background tasks
    """
    global executor
    try:
        # Check if executor is still working
        executor.submit(lambda: None).result(timeout=0.1)
        return executor
    except Exception as e:
        # If executor is not working or closed, create a new one
        logger.info(f"Creating new executor due to: {str(e)}")
        executor = ThreadPoolExecutor(max_workers=2)
        return executor

def process_pdf_background(filepath: str, document_id: str, metadata: Dict[str, Any], settings: Dict[str, Any]):
    """
    Process PDF file in background thread using DocumentStorageService
    
    Args:
        filepath: Path to the PDF file
        document_id: Document ID
        metadata: Document metadata
        settings: Processing settings
    """
    # Enable garbage collection
    gc.enable()
    
    # Create app context for processing
    from flask import current_app
    app = current_app._get_current_object()
    
    with app.app_context():
        try:
            logger.info(f"Starting document processing for {document_id} using DocumentStorageService")
            
            # Use the DocumentStorageService for processing
            doc_storage_service = DocumentStorageService()
            
            # Process and store the document
            result, updated_metadata = doc_storage_service.process_and_store_document(
                document_id=document_id,
                filepath=filepath,
                metadata=metadata,
                settings=settings
            )
            
            # Save updated metadata to file
            try:
                metadata_path = f"{filepath}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(updated_metadata, f, indent=2)
                logger.info(f"Updated metadata saved for document {document_id}")
            except Exception as e:
                logger.error(f"Error saving updated metadata: {e}")
            
            # Cleanup status after 10 minutes
            cleanup_status(document_id, 600)
            
        except Exception as e:
            logger.error(f"Error in background processing for document {document_id}: {str(e)}", exc_info=True)
            
            # Update status to error with detailed message
            update_document_status(
                document_id=document_id,
                status="error",
                progress=0,
                message=f"Error processing document: {str(e)}"
            )
                
            # Try to save error information to metadata file
            try:
                metadata_path = f"{filepath}.json"
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            existing_metadata = json.load(f)
                        metadata = existing_metadata
                    except Exception:
                        pass
                        
                metadata['processingComplete'] = False
                metadata['processingError'] = str(e)
                metadata['processedDate'] = datetime.utcnow().isoformat() + 'Z'
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            except Exception as metadata_err:
                logger.error(f"Error saving error metadata for {document_id}: {metadata_err}")
            
            # Force garbage collection
            gc.collect()