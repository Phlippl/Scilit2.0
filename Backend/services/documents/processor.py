# Backend/services/documents/processor.py
"""
High-level document processing service that coordinates the entire document workflow.
Responsible for orchestrating processing, storage, and status management.
"""
import os
import logging
import gc
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Tuple, Union

from flask import current_app
from services.pdf import get_pdf_processor
# Use direct VectorStorage import instead of legacy functions
from services.vector_storage import get_vector_storage
from utils.file_utils import write_json, read_json, cleanup_file
from utils.metadata_utils import format_metadata_for_storage
from config import config_manager

# Status management
from services.status_service import update_document_status, cleanup_status

logger = logging.getLogger(__name__)

class DocumentProcessingResult:
    """Standardized result object for document processing"""
    
    def __init__(self, 
                document_id: str,
                success: bool = True,
                message: str = "",
                metadata: Dict[str, Any] = None,
                chunks: List[Dict[str, Any]] = None,
                text: str = "",
                error: Optional[Exception] = None):
        """
        Initialize the result object
        
        Args:
            document_id: ID of the processed document
            success: Processing success flag
            message: Status message
            metadata: Document metadata
            chunks: Extracted text chunks
            text: Complete extracted text
            error: Exception if processing failed
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
        """Convert the result to a dictionary"""
        result = {
            "document_id": self.document_id,
            "success": self.success,
            "message": self.message,
            "metadata": self.metadata,
            "chunks_count": len(self.chunks),
            "text_length": len(self.text),
            "processing_time": self.processing_time
        }
        
        # For API responses only return limited number of chunks
        if self.chunks:
            MAX_CHUNKS_IN_RESPONSE = 100
            if len(self.chunks) > MAX_CHUNKS_IN_RESPONSE:
                result["chunks"] = self.chunks[:MAX_CHUNKS_IN_RESPONSE]
                result["limited_chunks"] = True
                result["total_chunks"] = len(self.chunks)
            else:
                result["chunks"] = self.chunks
        
        # Add error message if present
        if self.error:
            result["error"] = str(self.error)
        
        return result

class DocumentProcessor:
    """
    High-level document processor that coordinates the entire document workflow.
    Delegates PDF-specific operations to PDFProcessor.
    """
    
    def __init__(self):
        """Initialize the document processor"""
        # Get the PDF processor via the service registry
        self.pdf_processor = get_pdf_processor()
        # Get the vector storage
        self.vector_storage = get_vector_storage()
    
    def process(self, 
               filepath: str, 
               document_id: str, 
               metadata: Optional[Dict[str, Any]] = None,
               settings: Optional[Dict[str, Any]] = None,
               store: bool = True, 
               cleanup_file_after: bool = False) -> DocumentProcessingResult:
        """
        Process a document with optional storage
        
        Args:
            filepath: Path to document file
            document_id: Document ID
            metadata: Optional metadata
            settings: Processing settings
            store: Whether to store in vector database
            cleanup_file_after: Whether to delete file after processing
            
        Returns:
            DocumentProcessingResult: Processing result
        """
        # Enable garbage collection
        gc.enable()
        
        # Default values
        metadata = metadata or {}
        settings = settings or {}
        
        try:
            # Initialize status
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=0,
                message="Starting document processing..."
            )
            
            # Validate document
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=10,
                message="Validating document..."
            )
            
            valid, validation_result = self._validate_document(filepath)
            if not valid:
                raise ValueError(f"Document validation failed: {validation_result}")
            
            # Process PDF - delegate to PDFProcessor
            update_document_status(
                document_id=document_id,
                status="processing",
                progress=30,
                message="Extracting text and metadata..."
            )
            
            # Process PDF using the dedicated PDF processor
            pdf_result = self.pdf_processor.process_file(
                filepath,
                settings,
                progress_callback=lambda msg, pct: update_document_status(
                    document_id=document_id,
                    status="processing",
                    progress=30 + int(pct * 0.5),  # 30% - 80%
                    message=msg
                )
            )
            
            # Update metadata with extracted information
            extracted_metadata = pdf_result.get('metadata', {})
            if extracted_metadata:
                for key in ['doi', 'isbn', 'totalPages', 'processedPages']:
                    if key in extracted_metadata and extracted_metadata[key]:
                        metadata[key] = extracted_metadata[key]
            
            # Update status for vector storage
            if store:
                update_document_status(
                    document_id=document_id,
                    status="processing",
                    progress=85,
                    message="Storing chunks in vector database..."
                )
            
            # Prepare result object
            chunks = pdf_result.get('chunks', [])
            result = DocumentProcessingResult(
                document_id=document_id,
                success=True,
                message="Document successfully processed",
                metadata=metadata,
                chunks=chunks,
                text=pdf_result.get('text', '')
            )
            
            # Store in vector database if requested
            if store and chunks and len(chunks) > 0:
                # Apply reasonable chunk limit
                max_chunks = min(len(chunks), 500)
                limited_chunks = chunks[:max_chunks]
                
                # Format metadata for storage
                user_id = metadata.get('user_id', 'default_user')
                formatted_metadata = format_metadata_for_storage(metadata)
                
                # Store in vector database
                try:
                    self.vector_storage.store_document_chunks(
                        document_id=document_id,
                        chunks=limited_chunks,
                        metadata=formatted_metadata
                    )
                    
                    logger.info(f"Document {document_id} with {len(limited_chunks)} chunks stored")
                    
                    # Update metadata
                    result.metadata['processed'] = True
                    result.metadata['num_chunks'] = len(limited_chunks)
                    result.metadata['chunk_size'] = settings.get('chunkSize', 1000)
                    result.metadata['chunk_overlap'] = settings.get('chunkOverlap', 200)
                    
                except Exception as e:
                    logger.error(f"Error storing in vector database: {e}")
                    result.message = f"Document processed, but error storing: {str(e)}"
                    result.success = False
            
            # Save metadata as JSON file
            if store:
                metadata_path = f"{filepath}.json"
                # Add processing completion to metadata
                metadata['processingComplete'] = result.success
                metadata['processedDate'] = result.processing_time
                write_json(metadata_path, metadata)
            
            # Clean up file if requested
            if cleanup_file_after and os.path.exists(filepath):
                try:
                    cleanup_file(filepath)
                    logger.debug(f"File {filepath} deleted after processing")
                except Exception as e:
                    logger.warning(f"Error deleting file {filepath}: {e}")
            
            # Update status
            status = "completed" if result.success else "completed_with_warnings"
            update_document_status(
                document_id=document_id,
                status=status,
                progress=100,
                message=result.message,
                result=result.to_dict()
            )
            
            # Clean up status after 10 minutes
            cleanup_status(document_id, 600)
            
            # Force garbage collection
            gc.collect()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
            
            # Update status
            update_document_status(
                document_id=document_id,
                status="error",
                progress=0,
                message=f"Error processing document: {str(e)}"
            )
            
            # Save error in metadata if storing
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
                    logger.error(f"Error saving error metadata for {document_id}: {metadata_err}")
            
            # Clean up file on error if requested
            if cleanup_file_after and os.path.exists(filepath):
                try:
                    cleanup_file(filepath)
                    logger.debug(f"File {filepath} deleted after error")
                except Exception as cleanup_err:
                    logger.warning(f"Error deleting file {filepath}: {cleanup_err}")
            
            # Force garbage collection
            gc.collect()
            
            # Return error result
            return DocumentProcessingResult(
                document_id=document_id,
                success=False,
                message=f"Error processing document: {str(e)}",
                metadata=metadata,
                error=e
            )
    
    def analyze(self, 
               filepath: str, 
               document_id: str,
               settings: Optional[Dict[str, Any]] = None,
               cleanup_file_after: bool = True) -> DocumentProcessingResult:
        """
        Analyze a document without permanent storage
        
        Args:
            filepath: Path to document file
            document_id: Document ID
            settings: Processing settings
            cleanup_file_after: Whether to delete file after analysis
            
        Returns:
            DocumentProcessingResult: Analysis result
        """
        # Process document without storage
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
        Validate document and return success and result
        
        Args:
            filepath: Path to document file
            
        Returns:
            tuple: (is_valid, validation_result)
        """
        try:
            # Delegate validation to PDF processor
            is_valid, validation_result = self.pdf_processor.validate_pdf(filepath)
            if not is_valid:
                raise ValueError(f"Invalid PDF file: {validation_result}")
            return True, validation_result
        except Exception as e:
            logger.error(f"Error validating document: {str(e)}")
            return False, str(e)

# Function for background processing
def process_document_background(filepath: str, document_id: str, metadata: Dict[str, Any], settings: Dict[str, Any]):
    """
    Process document in background
    
    Args:
        filepath: Path to document file
        document_id: Document ID
        metadata: Document metadata
        settings: Processing settings
    """
    try:
        # Get app context (if in Flask application)
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
            # If running outside Flask
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
        logger.error(f"Error in background processing for {document_id}: {e}", exc_info=True)
        
        # Report error in status
        update_document_status(
            document_id=document_id,
            status="error",
            progress=0,
            message=f"Error processing document: {str(e)}"
        )