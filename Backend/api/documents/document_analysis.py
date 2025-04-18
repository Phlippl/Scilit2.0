# Backend/api/documents/document_analysis.py
"""
Module for document analysis without full processing
"""
import os
import logging
import gc
import time
from typing import Dict, Any

# Import services and utilities
from services.documents.processor import DocumentProcessor
from utils.helpers import timeout_handler
from services.status_service import get_status_service

# Import metadata retrieval functions
try:
    from api.metadata import fetch_metadata_from_crossref
except ImportError:
    def fetch_metadata_from_crossref(doi):
        logging.warning(f"Metadata API not available. Cannot fetch metadata for DOI")
        return None

# Configure logging
logger = logging.getLogger(__name__)

@timeout_handler(max_seconds=120, cpu_limit=70)
def analyze_document_background(filepath: str, document_id: str, settings: Dict[str, Any]):
    """
    Background task to analyze a document
    
    Args:
        filepath: Path to the document
        document_id: Document ID
        settings: Processing settings
    """
    # Import app context 
    from flask import current_app
    app = current_app._get_current_object()
    
    with app.app_context():
        try:
            # Initialisiere Verarbeitungseinstellungen
            processing_settings = {
                'maxPages': int(settings.get('maxPages', 0)),
                'performOCR': bool(settings.get('performOCR', False)),
                'chunkSize': int(settings.get('chunkSize', 1000)),
                'chunkOverlap': int(settings.get('chunkOverlap', 200))
            }
            
            # Aktualisiere Status
            get_status_service().update_status(
                status_id=document_id,
                status="processing",
                progress=10,
                message="Analyzing document..."
            )
            
            # Use the consolidated DocumentProcessor directly
            document_processor = DocumentProcessor()
            
            # Analyze the document
            result = document_processor.analyze(
                filepath=filepath,
                document_id=document_id,
                settings=processing_settings,
                cleanup_file_after=True
            )
            
            # Convert result to dictionary
            result_dict = result.to_dict()
            
            # Update status with results
            get_status_service().update_status(
                status_id=document_id,
                status="completed",
                progress=100,
                message="Analysis complete",
                result=result_dict
            )
            
            # Cleanup Status after 10 minutes
            get_status_service().cleanup_status(document_id, 600)
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}", exc_info=True)
            
            # Update status to reflect error
            get_status_service().update_status(
                status_id=document_id,
                status="error",
                progress=0,
                message=f"Error analyzing document: {str(e)}",
                result={"error": str(e)}
            )
            
            # Clean up temporary file
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
                    logger.debug(f"Cleaned up file {filepath} after error")
            except Exception as cleanup_error:
                logger.error(f"Error deleting temporary file {filepath}: {cleanup_error}")
            
            # Force garbage collection
            gc.collect()

def get_analysis_results(document_id: str) -> Dict[str, Any]:
    """
    Retrieve analysis results for a given document ID
    
    Args:
        document_id: ID of the document to retrieve results for
    
    Returns:
        Dict containing analysis results or error information
    """
    # Direct use of the get_status_service function
    status_data = get_status_service().get_status(document_id)
    
    # Check if status contains results
    if status_data.get("status") == "completed" and "result" in status_data:
        return {
            "status": "completed",
            "result": status_data["result"]
        }
    
    # If no results in status, return status as is
    return status_data