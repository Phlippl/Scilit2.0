# Backend/api/documents/document_analysis.py
"""
Module for document analysis without full processing
"""
import os
import json
import logging
import gc
import time
from datetime import datetime
from typing import Dict, Any

# Import services and utilities
from services.pdf import get_pdf_processor
from services.document_analysis_service import DocumentAnalysisService
from utils.helpers import timeout_handler
from .document_status import update_document_status, cleanup_status, get_document_status

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
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=10,
                message="Analyzing document..."
            )
            
            # Direkte Nutzung des DocumentAnalysisService
            analysis_service = DocumentAnalysisService()
            
            # Analysiere das Dokument
            result = analysis_service.analyze_document(
                document_id=document_id,
                filepath=filepath,
                settings=processing_settings
            )
            
            # Cleanup Status nach 10 Minuten
            cleanup_status(document_id, 600)
            
            # Erzwinge Garbage Collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}", exc_info=True)
            
            # Aktualisiere Status, um Fehler widerzuspiegeln
            update_document_status(
                document_id=document_id,
                status="error",
                progress=0,
                message=f"Error analyzing document: {str(e)}",
                result={"error": str(e)}
            )
            
            # Räume temporäre Datei auf
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
                    logger.debug(f"Cleaned up file {filepath} after error")
            except Exception as cleanup_error:
                logger.error(f"Error deleting temporary file {filepath}: {cleanup_error}")
            
            # Erzwinge Garbage Collection
            gc.collect()

def get_analysis_results(document_id: str) -> Dict[str, Any]:
    """
    Retrieve analysis results for a given document ID
    
    Args:
        document_id: ID of the document to retrieve results for
    
    Returns:
        Dict containing analysis results or error information
    """
    # Direkte Nutzung der get_document_status Funktion
    status_data = get_document_status(document_id)
    
    # Check if status contains results
    if status_data.get("status") == "completed" and "result" in status_data:
        return {
            "status": "completed",
            "result": status_data["result"]
        }
    
    # If no results in status, return status as is
    return status_data