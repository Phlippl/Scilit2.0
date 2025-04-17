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
from services.pdf_processor import PDFProcessor
from utils.helpers import timeout_handler
from .document_status import update_document_status, cleanup_status

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
    from .document_status import processing_status, processing_status_lock, save_status_to_file
    from .document_validation import format_metadata_for_storage

    # Create app context
    app = current_app._get_current_object()
    
    with app.app_context():
        try:
            # Update status
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=10,
                message="Analyzing document..."
            )
            
            # Define progress update callback
            def update_progress(message: str, progress: int):
                try:
                    update_document_status(
                        document_id=document_id,
                        status="processing",
                        progress=progress,
                        message=message
                    )
                except Exception as e:
                    logger.error(f"Error updating progress for document {document_id}: {str(e)}")
            
            # Process PDF to extract text, metadata, and chunks
            pdf_processor = PDFProcessor()
            
            # Extract processing settings
            processing_settings = {
                'maxPages': int(settings.get('maxPages', 0)),
                'performOCR': bool(settings.get('performOCR', False)),
                'chunkSize': int(settings.get('chunkSize', 1000)),
                'chunkOverlap': int(settings.get('chunkOverlap', 200))
            }
            
            # Validate PDF first
            update_progress("Validating PDF...", 20)
            try:
                is_valid, validation_result = pdf_processor.validate_pdf(filepath)
                if not is_valid:
                    raise ValueError(f"Invalid PDF file: {validation_result}")
            except Exception as e:
                raise ValueError(f"Error validating PDF: {str(e)}")
            
            # Process the file
            update_progress("Extracting text and metadata...", 40)
            result = pdf_processor.process_file(
                filepath,
                settings=processing_settings,
                progress_callback=update_progress
            )
            
            # Attempt to fetch additional metadata
            update_progress("Enriching metadata...", 80)
            metadata = result['metadata']
            
            # Try to fetch additional metadata via DOI
            if metadata.get('doi'):
                try:
                    crossref_metadata = fetch_metadata_from_crossref(metadata['doi'])
                    if crossref_metadata:
                        # Merge and prioritize existing metadata
                        for key, value in crossref_metadata.items():
                            if not metadata.get(key) and value:
                                metadata[key] = value
                except Exception as e:
                    logger.warning(f"Error fetching additional metadata: {e}")
            
            # Limit chunks to avoid overwhelming the response
            MAX_CHUNKS_IN_RESPONSE = 100
            chunks = result.get('chunks', [])
            if len(chunks) > MAX_CHUNKS_IN_RESPONSE:
                logger.info(f"Limiting chunks in response from {len(chunks)} to {MAX_CHUNKS_IN_RESPONSE}")
                limited_chunks = chunks[:MAX_CHUNKS_IN_RESPONSE]
                result.update({
                    'limitedChunks': True,
                    'totalChunks': len(chunks),
                    'chunks': limited_chunks
                })
            
            # Prepare result data
            result_data = {
                "metadata": format_metadata_for_storage(metadata),
                "chunks": result.get('chunks', []),
                "totalPages": metadata.get('totalPages', 0),
                "processedPages": metadata.get('processedPages', 0),
                "limitedChunks": result.get('limitedChunks', False),
                "totalChunks": result.get('totalChunks', len(chunks))
            }
            
            # Store result for retrieval
            update_document_status(
                document_id=document_id,
                status="completed",
                progress=100,
                message="Analysis complete",
                result=result_data
            )
            
            # Clean up temporary file
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            except Exception as e:
                logger.error(f"Error deleting temporary file {filepath}: {e}")
                
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}", exc_info=True)
            
            # Update status to reflect error
            update_document_status(
                document_id=document_id,
                status="error",
                progress=0,
                message=f"Error analyzing document: {str(e)}",
                result={"error": str(e)}
            )
            
            # Clean up temporary file
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
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
    from flask import current_app
    from .document_status import processing_status, processing_status_lock
    from .document_status import get_document_status

    # Get status from central function
    status_data = get_document_status(document_id)
    
    # Check if status contains results
    if status_data.get("status") == "completed" and "result" in status_data:
        return {
            "status": "completed",
            "result": status_data["result"]
        }
    
    # If not in memory and no results in status, check for results file
    results_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_results.json")
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r') as f:
                results_data = json.load(f)
                
            return {
                "status": "completed",
                "result": results_data
            }
        except Exception as e:
            logger.error(f"Error reading results file: {e}")
    
    # If no results file found, return status as is
    return status_data