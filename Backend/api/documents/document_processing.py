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
import concurrent.futures
import gc
from datetime import datetime
from pathlib import Path

# Import required services and modules
from services.pdf_processor import PDFProcessor
from services.vector_db import store_document_chunks, delete_document as delete_from_vector_db
from .document_status import update_document_status, cleanup_status
from .document_validation import format_metadata_for_storage, format_authors

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
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

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
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        return executor

def process_pdf_background(filepath, document_id, metadata, settings):
    """
    Process PDF file in background thread with improved error handling
    
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
        # Set reasonable limits
        max_file_size_mb = 20  # Maximum file size to process in MB
        
        try:
            # Check file size
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if file_size_mb > max_file_size_mb:
                error_msg = f"File too large ({file_size_mb:.1f}MB). Maximum allowed size is {max_file_size_mb}MB."
                with processing_status_lock:
                    processing_status[document_id] = {
                        "status": "error",
                        "progress": 0,
                        "message": error_msg
                    }
                    # Save status to file
                    save_status_to_file(document_id, processing_status[document_id])
                    
                # Save error to metadata
                metadata_path = f"{filepath}.json"
                metadata['processingComplete'] = False
                metadata['processingError'] = error_msg
                metadata['processedDate'] = datetime.utcnow().isoformat() + 'Z'
                try:
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                except Exception as write_err:
                    logger.error(f"Error saving error metadata for {document_id}: {write_err}")
                return
        
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=0,
                message="Starting PDF processing..."
            )
            
            # Progress update callback with improved error handling
            def update_progress(message, progress):
                try:
                    update_document_status(
                        document_id=document_id,
                        status="processing",
                        progress=progress,
                        message=message
                    )
                except Exception as e:
                    logger.error(f"Error updating progress for document {document_id}: {str(e)}")
                        
                      
            try:
                # Validate PDF first
                is_valid, validation_result = pdf_processor.validate_pdf(filepath)
                if not is_valid:
                    raise ValueError(f"Invalid PDF file: {validation_result}")
            except Exception as e:
                raise ValueError(f"Error validating PDF: {str(e)}")
            
            # Process PDF with progress reporting
            pdf_result = pdf_processor.process_file(
                filepath, 
                settings,
                progress_callback=update_progress
            )
            
            # Update metadata with extracted information
            if pdf_result['metadata'].get('doi') and not metadata.get('doi'):
                metadata['doi'] = pdf_result['metadata']['doi']
            
            if pdf_result['metadata'].get('isbn') and not metadata.get('isbn'):
                metadata['isbn'] = pdf_result['metadata']['isbn']
            
            # Fetch metadata via DOI or ISBN if needed
            if not metadata.get('title') and (metadata.get('doi') or metadata.get('isbn')):
                update_progress("Fetching metadata from external sources...", 90)
                
                # Try DOI first
                if metadata.get('doi'):
                    try:
                        crossref_metadata = fetch_metadata_from_crossref(metadata['doi'])
                        if crossref_metadata:
                            # Format and add metadata
                            title = crossref_metadata.get("title", "")
                            if isinstance(title, list) and len(title) > 0:
                                title = title[0]
                            
                            # Update with metadata from CrossRef
                            metadata.update({
                                "title": title,
                                "authors": crossref_metadata.get("author", []),
                                "publicationDate": crossref_metadata.get("published-print", {}).get("date-parts", [[""]])[0][0],
                                "journal": crossref_metadata.get("container-title", ""),
                                "publisher": crossref_metadata.get("publisher", ""),
                                "volume": crossref_metadata.get("volume", ""),
                                "issue": crossref_metadata.get("issue", ""),
                                "pages": crossref_metadata.get("page", ""),
                                "type": crossref_metadata.get("type", ""),
                            })
                    except Exception as e:
                        logger.error(f"Error fetching CrossRef metadata: {e}")
            
            # Update status
            update_progress("Storing chunks in vector database...", 95)
            
            # Store chunks in vector database with error handling
            chunks_stored = False
            if pdf_result['chunks'] and len(pdf_result['chunks']) > 0:
                # Limit the number of chunks to prevent overwhelming the vector DB
                max_chunks = min(len(pdf_result['chunks']), 500)
                if len(pdf_result['chunks']) > max_chunks:
                    logger.warning(f"Limiting document {document_id} to {max_chunks} chunks (from {len(pdf_result['chunks'])})")
                    pdf_result['chunks'] = pdf_result['chunks'][:max_chunks]
                
                # Add user_id to metadata
                user_id = metadata.get('user_id', 'default_user')
                
                try:
                    # Properly format author data
                    authors_data = metadata.get('authors', [])
                    if isinstance(authors_data, list):
                        # Convert complex objects to strings
                        authors = format_authors(authors_data)
                        metadata['authors'] = authors
                    
                    # Format metadata consistently
                    formatted_metadata = format_metadata_for_storage(metadata)
                    
                    # Store chunks in vector database
                    store_result = store_document_chunks(
                        document_id=document_id,
                        chunks=pdf_result['chunks'],
                        metadata=formatted_metadata
                    )
                    chunks_stored = True
                    
                    # Update metadata with chunk info
                    metadata['processed'] = store_result
                    metadata['num_chunks'] = len(pdf_result['chunks'])
                    metadata['chunk_size'] = settings.get('chunkSize', 1000)
                    metadata['chunk_overlap'] = settings.get('chunkOverlap', 200)
                except Exception as e:
                    logger.error(f"Error storing chunks for document {document_id}: {str(e)}")
                    update_progress(f"Error storing chunks: {str(e)}", 95)
                    chunks_stored = False
            
            # Final metadata updates
            metadata['processingComplete'] = chunks_stored
            metadata['processedDate'] = datetime.utcnow().isoformat() + 'Z'
            
            # Save updated metadata
            metadata_path = f"{filepath}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Final status update
            if chunks_stored:
                update_document_status(
                    document_id=document_id,
                    status="completed",
                    progress=100,
                    message="Document processing completed"
                )
            else:
                with processing_status_lock:
                    processing_status[document_id] = {
                        "status": "completed_with_warnings",
                        "progress": 100,
                        "message": "Document processed but chunks could not be stored"
                    }
                    # Save status to file
                    save_status_to_file(document_id, processing_status[document_id])
            
            # Cleanup function that works without executor
            def cleanup_status_direct(doc_id):
                """Cleanup function that works without executor"""
                with processing_status_lock:
                    if doc_id in processing_status:
                        del processing_status[doc_id]
                        logger.info(f"Cleaned up status for document {doc_id} via direct method")

            # Clean up status after 10 minutes
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
                    except:
                        pass
                        
                metadata['processingComplete'] = False
                metadata['processingError'] = str(e)
                metadata['processedDate'] = datetime.utcnow().isoformat() + 'Z'
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            except Exception as metadata_err:
                logger.error(f"Error saving error metadata for {document_id}: {metadata_err}")