# Backend/api/documents/document_api.py
"""
Main Blueprint for document management API endpoints
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import jwt
import traceback

# Import utils and services - aktualisiert für refactorierte Module
from utils.helpers import allowed_file, get_safe_filepath
from utils.auth_middleware import optional_auth, get_user_id
from utils.metadata_utils import validate_metadata, format_metadata_for_storage
from services.vector_db import delete_document as delete_from_vector_db

# Import submodules
from .document_processing import process_pdf_background, get_executor
from .document_analysis import analyze_document_background
from .document_status import (
    processing_status_lock, processing_status, 
    save_status_to_file, get_document_status
)

logger = logging.getLogger(__name__)

# Create Blueprint for document API
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')
CORS(documents_bp, resources={r"/*": {"origins": "*"}})

@documents_bp.route('/status/<document_id>', methods=['GET'])
def get_document_status_api(document_id):
    """Gets the processing status of a document"""
    logger.info(f"Fetching status for document ID: {document_id}")
    return get_document_status(document_id)

@documents_bp.route('/cancel-processing/<document_id>', methods=['POST'])
def cancel_processing(document_id):
    """Abbrechen eines laufenden Verarbeitungsprozesses"""
    try:
        # Get user ID
        user_id = get_user_id()
        logger.info(f"Canceling processing for document {document_id} by user {user_id}")
        
        # Update status to canceled
        with processing_status_lock:
            if document_id in processing_status:
                processing_status[document_id] = {
                    "status": "canceled",
                    "progress": 0,
                    "message": "Processing canceled by user"
                }
                # Save status to file
                save_status_to_file(document_id, processing_status[document_id])
                logger.info(f"Processing for document {document_id} canceled successfully")
        
        return jsonify({"success": True, "message": "Processing canceled"})
    except Exception as e:
        logger.error(f"Error canceling processing: {e}")
        return jsonify({"error": f"Failed to cancel processing: {str(e)}"}), 500

@documents_bp.route('/quick-analyze', methods=['POST'])
def quick_analyze():
    """Schnelle Analyse für DOI/ISBN Extraktion mit verbesserten Logging und Fehlerbehandlung"""
    logger.info("Starting quick-analyze endpoint")
    try:
        if 'file' not in request.files:
            logger.warning("No file provided in request")
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            logger.warning("Empty filename")
            return jsonify({"error": "No file selected"}), 400
            
        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({"error": "File type not allowed. Only PDF files are accepted."}), 400
        
        # Parse settings from request
        logger.debug("Parsing settings from request")
        settings = {}
        if 'data' in request.form:
            try:
                settings = json.loads(request.form.get('data', '{}'))
                logger.debug(f"Parsed settings: {settings}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON data in request: {e}")
                return jsonify({"error": "Invalid JSON data"}), 400
        
        # Get user ID
        user_id = get_user_id()
        logger.info(f"Processing quick-analyze for user {user_id}")
        
        # Temporarily save file
        filename = secure_filename(file.filename)
        temp_id = str(uuid.uuid4())
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        filepath = os.path.join(user_upload_dir, f"temp_{temp_id}_{filename}")
        file.save(filepath)
        logger.info(f"File saved to temporary location: {filepath}")
        
        # Configure extraction settings
        max_pages = int(settings.get('maxPages', 10))
        perform_ocr = bool(settings.get('performOCR', False))
        logger.info(f"Extraction settings: max_pages={max_pages}, perform_ocr={perform_ocr}")
        
        # Use PDFProcessor for extraction
        from services.pdf_processor import PDFProcessor
        pdf_processor = PDFProcessor()
        
        # Extrahiere nur DOI/ISBN ohne vollständige Verarbeitung
        try:
            logger.info(f"Starting identifier extraction from {filepath}")
            result = pdf_processor.extract_identifiers_only(filepath, max_pages)
            logger.info(f"Extraction result: {result}")
            
            # Metadaten abrufen, falls DOI gefunden wurde
            metadata = {}
            if result.get('doi'):
                doi = result['doi']
                logger.info(f"DOI found: {doi}, attempting to fetch metadata")
                try:
                    from api.metadata import fetch_metadata_from_crossref
                    logger.debug("Imported fetch_metadata_from_crossref successfully")
                    
                    crossref_metadata = fetch_metadata_from_crossref(doi)
                    logger.debug(f"CrossRef metadata result: {crossref_metadata}")
                    
                    if crossref_metadata:
                        logger.info(f"Successfully fetched metadata for DOI {doi}")
                        from .document_validation import format_metadata_for_storage
                        metadata = format_metadata_for_storage(crossref_metadata)
                        logger.debug(f"Formatted metadata: {metadata}")
                except ImportError as e:
                    logger.warning(f"Metadata API not available: {e}")
                except Exception as e:
                    logger.warning(f"Error fetching DOI metadata: {e}", exc_info=True)
            
            # Falls ISBN gefunden, versuche OpenLibrary
            elif result.get('isbn'):
                isbn = result['isbn']
                logger.info(f"ISBN found: {isbn}, attempting to fetch metadata")
                try:
                    import requests
                    isbn = isbn.replace('-', '').replace(' ', '')
                    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
                    logger.debug(f"Making OpenLibrary request to: {url}")
                    
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        logger.debug(f"OpenLibrary response: {data}")
                        
                        key = f"ISBN:{isbn}"
                        if key in data:
                            book_data = data[key]
                            # Extrahiere Buchtitel, Autoren, etc.
                            authors = []
                            if 'authors' in book_data:
                                for author in book_data['authors']:
                                    name = author.get('name', '')
                                    authors.append({'name': name})
                            
                            metadata = {
                                'title': book_data.get('title', ''),
                                'authors': authors,
                                'publisher': book_data.get('publishers', [{}])[0].get('name', '') if 'publishers' in book_data else '',
                                'publicationDate': book_data.get('publish_date', ''),
                                'isbn': isbn,
                                'type': 'book'
                            }
                            logger.info(f"Successfully fetched book metadata from OpenLibrary")
                except Exception as e:
                    logger.warning(f"Error fetching ISBN metadata: {e}", exc_info=True)
            
            logger.info(f"Quick-analyze completed successfully for temp_id: {temp_id}")
            return jsonify({
                "temp_id": temp_id,
                "filename": filename,
                "metadata": metadata,
                "identifiers": result
            })
            
        except Exception as e:
            logger.error(f"Error extracting identifiers: {e}", exc_info=True)
            
            # Return partial result even if error occurred
            return jsonify({
                "temp_id": temp_id,
                "filename": filename,
                "metadata": {},
                "identifiers": {"error": str(e)}
            })
            
    except Exception as e:
        logger.error(f"Error in quick analysis: {e}", exc_info=True)
        return jsonify({"error": f"Failed to analyze: {str(e)}"}), 500

@documents_bp.route('', methods=['GET'])
def list_documents():
    """Get list of all documents"""
    try:
        # Get user ID
        user_id = get_user_id()
        logger.info(f"Listing documents for user: {user_id}")
        
        documents = []
        
        # User-specific directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        if not os.path.exists(user_upload_dir):
            logger.info(f"User directory does not exist: {user_upload_dir}, returning empty list")
            return jsonify([])
        
        # Search JSON metadata files in user directory
        upload_folder = Path(user_upload_dir)
        metadata_files = list(upload_folder.glob("*.json"))
        logger.debug(f"Found {len(metadata_files)} metadata files")
        
        for file in metadata_files:
            try:
                with open(file, 'r') as f:
                    metadata = json.load(f)
                    documents.append(metadata)
                    logger.debug(f"Added document: {metadata.get('id', 'unknown')}, title: {metadata.get('title', 'untitled')}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in file {file}")
            except Exception as e:
                logger.error(f"Error reading metadata file {file}: {e}")
        
        # Sort by upload date, newest first
        logger.info(f"Returning {len(documents)} documents")
        return jsonify(sorted(
            documents, 
            key=lambda x: x.get('uploadDate', ''), 
            reverse=True
        ))
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@documents_bp.route('/<document_id>', methods=['GET'])
def get_document(document_id):
    """Get specific document by ID"""
    try:
        # Get user ID
        user_id = get_user_id()
        logger.info(f"Retrieving document {document_id} for user {user_id}")
        
        # Find metadata file
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        metadata_files = list(Path(user_upload_dir).glob(f"{document_id}_*.json"))
        
        if not metadata_files:
            logger.warning(f"Document {document_id} not found")
            return jsonify({"error": "Document not found"}), 404
            
        with open(metadata_files[0], 'r') as f:
            metadata = json.load(f)
            logger.debug(f"Retrieved metadata for document {document_id}")
            
        # Check processing status
        with processing_status_lock:
            if document_id in processing_status:
                metadata['processing_status'] = processing_status[document_id]
                logger.debug(f"Added processing status to response: {processing_status[document_id]}")
            
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@documents_bp.route('', methods=['POST'])
def save_document():
    """Upload and process a new document with improved validation and logging"""
    try:
        # Check if file or metadata is provided
        if 'file' not in request.files and not request.form.get('data'):
            logger.warning("No file or data provided in request")
            return jsonify({"error": "No file or data provided"}), 400
        
        # Extract metadata from form
        metadata = {}
        if 'data' in request.form:
            try:
                logger.debug("Parsing metadata from form data")
                metadata = json.loads(request.form.get('data', '{}'))
                
                # Check if title is directly in request.form (fix)
                if 'title' in request.form and request.form['title']:
                    metadata['title'] = request.form['title']
                    logger.debug(f"Using title from form field: {metadata['title']}")
                
                # Check if type is directly in request.form (fix)
                if 'type' in request.form and request.form['type']:
                    metadata['type'] = request.form['type']
                    logger.debug(f"Using type from form field: {metadata['type']}")
                
                # Check if authors is directly in request.form (fix)
                if 'authors' in request.form and request.form['authors']:
                    try:
                        metadata['authors'] = json.loads(request.form['authors'])
                        logger.debug(f"Using authors from form field: {metadata['authors']}")
                    except:
                        logger.warning("Failed to parse authors JSON from form field")
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON data in request")
                return jsonify({"error": "Invalid JSON data"}), 400
        
        # Validate metadata
        logger.debug("Validating metadata")
        is_valid, error_message = validate_metadata(metadata)
        if not is_valid:
            logger.warning(f"Metadata validation failed: {error_message}")
            return jsonify({"error": error_message}), 400
        
        # Generate document ID if not provided
        document_id = metadata.get('id', str(uuid.uuid4()))
        logger.info(f"Processing document {document_id}")
        
        # Get user ID
        user_id = get_user_id()
        logger.info(f"User ID: {user_id}")
        
        metadata['user_id'] = user_id
        
        # Create user-specific upload directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        logger.debug(f"User upload directory: {user_upload_dir}")
        
        # Check for temp_document_id to reuse already uploaded file
        temp_document_id = metadata.get('temp_document_id')
        filepath = None
        
        if temp_document_id:
            logger.info(f"Temp document ID provided: {temp_document_id}, looking for existing file")
            temp_files = list(Path(user_upload_dir).glob(f"temp_{temp_document_id}_*"))
            if temp_files:
                temp_filepath = str(temp_files[0])
                filename = os.path.basename(temp_filepath).replace(f"temp_{temp_document_id}_", "")
                filepath = os.path.join(user_upload_dir, f"{document_id}_{filename}")
                
                # Rename temp file to permanent file
                os.rename(temp_filepath, filepath)
                logger.info(f"Reused temp file: {temp_filepath} -> {filepath}")
        
        # If file is uploaded or no temp file found, process the uploaded file
        if 'file' in request.files and (filepath is None):
            file = request.files['file']
            if file.filename == '':
                logger.warning("Empty filename in uploaded file")
                return jsonify({"error": "No file selected"}), 400
            
            if not allowed_file(file.filename):
                logger.warning(f"Invalid file type: {file.filename}")
                return jsonify({"error": "File type not allowed. Only PDF files are accepted."}), 400
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(user_upload_dir, f"{document_id}_{filename}")
            
            try:
                file.save(filepath)
                logger.info(f"Uploaded file saved to: {filepath}")
            except Exception as e:
                logger.error(f"Error saving file: {e}")
                return jsonify({"error": f"File upload failed: {str(e)}"}), 500
        
        if filepath is None:
            logger.error("No file path available after processing")
            return jsonify({"error": "No file provided"}), 400
        
        # Optionally save document metadata to database
        try:
            from services.document_db_service import DocumentDBService
            doc_db_service = DocumentDBService()
            
            logger.debug("Saving document metadata to database")
            save_result = doc_db_service.save_document_metadata(
                document_id=document_id,
                user_id=user_id,
                title=metadata.get('title', os.path.basename(filepath)),
                file_name=os.path.basename(filepath),
                file_path=filepath,
                file_size=os.path.getsize(filepath),
                metadata=metadata
            )
            
            if not save_result:
                logger.warning(f"Document could not be saved to database for user: {user_id}")
        except Exception as e:
            logger.warning(f"Error saving to database: {e}")
            # Continue with upload even if DB save fails
        
        try:
            # Extract processing settings from metadata
            processing_settings = {
                'maxPages': int(metadata.get('maxPages', 0)),
                'performOCR': bool(metadata.get('performOCR', False)),
                'chunkSize': int(metadata.get('chunkSize', 1000)),
                'chunkOverlap': int(metadata.get('chunkOverlap', 200))
            }
            logger.debug(f"Processing settings: {processing_settings}")
            
            # Add upload-specific metadata
            metadata['document_id'] = document_id
            metadata['filename'] = os.path.basename(filepath)
            metadata['fileSize'] = os.path.getsize(filepath)
            metadata['uploadDate'] = datetime.utcnow().isoformat() + 'Z'
            metadata['filePath'] = filepath
            metadata['processingComplete'] = False
            
            # Save initial metadata to JSON file
            metadata_path = f"{filepath}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                logger.debug(f"Initial metadata saved to: {metadata_path}")
            
            # Get current app object
            app = current_app._get_current_object()
            
            # Start background processing
            logger.info(f"Starting background processing for document {document_id}")
            get_executor().submit(
                process_pdf_background,
                filepath,
                document_id,
                metadata,
                processing_settings
            )
            
            # Save initial status
            initial_status = {
                "status": "processing",
                "progress": 0,
                "message": "Document upload complete. Processing started..."
            }
            with processing_status_lock:
                processing_status[document_id] = initial_status
                
                # Save status with app context
                with app.app_context():
                    save_status_to_file(document_id, initial_status)
                    logger.debug(f"Initial processing status saved for document {document_id}")
            
            logger.info(f"Document {document_id} successfully uploaded and processing started")
            return jsonify({
                **metadata,
                "document_id": document_id,
                "processing_status": initial_status
            })
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(filepath):
                os.unlink(filepath)
                logger.warning(f"Cleaned up file {filepath} due to error")
            logger.error(f"Error processing document: {e}", exc_info=True)
            return jsonify({"error": f"Error processing document: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error in save_document: {e}", exc_info=True)
        return jsonify({"error": f"Error saving document: {str(e)}"}), 500

@documents_bp.route('/<document_id>', methods=['DELETE'])
def delete_document_api(document_id):
    """Delete a document"""
    try:
        # Authentication
        user_id = request.headers.get('X-User-ID', 'default_user')
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                secret_key = current_app.config['SECRET_KEY']
                payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                user_id = payload.get('sub', user_id)
            except Exception as e:
                logger.warning(f"JWT decoding failed: {e}")
        
        logger.info(f"Deleting document {document_id} for user {user_id}")
        
        # Find all files for this document in user's directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        files = list(Path(user_upload_dir).glob(f"{document_id}_*"))
        
        if not files:
            logger.warning(f"Document {document_id} not found for deletion")
            return jsonify({"error": "Document not found"}), 404
        
        # Delete PDF and metadata files
        for file in files:
            try:
                file.unlink()
                logger.debug(f"Deleted file: {file}")
            except Exception as e:
                logger.error(f"Error deleting file {file}: {e}")
        
        # Delete status file if exists
        status_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_status.json")
        if os.path.exists(status_file):
            try:
                os.unlink(status_file)
                logger.debug(f"Deleted status file: {status_file}")
            except Exception as e:
                logger.error(f"Error deleting status file {status_file}: {e}")
        
        # Delete from vector database
        try:
            delete_from_vector_db(document_id, user_id)
            logger.info(f"Deleted document {document_id} from vector database")
        except Exception as e:
            logger.error(f"Error deleting from vector database: {e}")
        
        # Clear any processing status
        with processing_status_lock:
            if document_id in processing_status:
                del processing_status[document_id]
                logger.debug(f"Removed processing status for document {document_id}")
        
        logger.info(f"Document {document_id} successfully deleted")
        return jsonify({"success": True, "message": f"Document {document_id} deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to delete document: {str(e)}"}), 500

@documents_bp.route('/<document_id>', methods=['PUT'])
def update_document(document_id):
    """Update a document"""
    try:
        # Authentication
        user_id = request.headers.get('X-User-ID', 'default_user')
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                secret_key = current_app.config['SECRET_KEY']
                payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                user_id = payload.get('sub', user_id)
            except Exception as e:
                logger.warning(f"JWT decoding failed: {e}")
        
        logger.info(f"Updating document {document_id} for user {user_id}")
        
        if not request.is_json:
            logger.warning("Request is not JSON")
            return jsonify({"error": "Request must be JSON"}), 400
        
        metadata = request.get_json()
        logger.debug(f"Update metadata received: {metadata}")
        
        # Find document in user's directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        files = list(Path(user_upload_dir).glob(f"{document_id}_*"))
        
        if not files:
            logger.warning(f"Document {document_id} not found for update")
            return jsonify({"error": "Document not found"}), 404
            
        # Find PDF file
        pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
        if not pdf_files:
            logger.warning(f"PDF file not found for document {document_id}")
            return jsonify({"error": "PDF file not found"}), 404
        
        filepath = str(pdf_files[0])
        logger.debug(f"Found PDF file at: {filepath}")
        
        # Load existing metadata
        metadata_path = f"{filepath}.json"
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                existing_metadata = json.load(f)
            logger.debug(f"Loaded existing metadata for document {document_id}")
            
            # Process specific fields that need updating in the vector database
            update_chunks = False
            critical_fields = ['title', 'authors', 'publicationDate', 'journal', 'publisher', 'doi', 'isbn']
            
            for field in critical_fields:
                if field in metadata and metadata[field] != existing_metadata.get(field):
                    logger.info(f"Critical field '{field}' changed, will update vector database")
                    update_chunks = True
                    break
            
            # Merge with existing metadata
            merged_metadata = {**existing_metadata, **metadata}
            metadata = merged_metadata
            logger.debug(f"Merged metadata: {metadata}")
            
            # If critical fields were updated, update the vector database
            if update_chunks and metadata.get('processed') and metadata.get('num_chunks', 0) > 0:
                logger.info(f"Critical metadata changed, updating vector database for document {document_id}")
                try:
                    # Get existing PDF processor settings
                    processing_settings = {
                        'maxPages': metadata.get('maxPages', 0),
                        'performOCR': metadata.get('performOCR', False),
                        'chunkSize': metadata.get('chunk_size', 1000),
                        'chunkOverlap': metadata.get('chunk_overlap', 200)
                    }
                    
                    # Update status
                    update_status = {
                        "status": "processing",
                        "progress": 0,
                        "message": "Updating document metadata..."
                    }
                    with processing_status_lock:
                        processing_status[document_id] = update_status
                        save_status_to_file(document_id, update_status)
                        logger.debug(f"Updated processing status for document {document_id}")
                    
                    # Start background processing
                    logger.info(f"Starting background processing for document update {document_id}")
                    get_executor().submit(
                        process_pdf_background,
                        filepath,
                        document_id,
                        metadata,
                        processing_settings
                    )
                    
                    metadata['processingComplete'] = False
                except Exception as e:
                    logger.error(f"Error updating vector database: {e}", exc_info=True)
        
        # Add update timestamp
        metadata['document_id'] = document_id
        metadata['updateDate'] = datetime.utcnow().isoformat() + 'Z'
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            logger.info(f"Updated metadata saved for document {document_id}")
        
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}", exc_info=True)
        return jsonify({"error": f"Failed to update document: {str(e)}"}), 500

@documents_bp.route('/analyze', methods=['POST'])
@optional_auth  # Use our auth middleware
def analyze_document():
    """
    Analyze a document without saving it to get metadata and chunks
    This helps separate the processing from the saving step
    """
    try:
        # Get user ID from auth middleware
        user_id = g.user_id if hasattr(g, 'user_id') else 'default_user'
        logger.info(f"Starting document analysis for user {user_id}")
        
        # Check if file was uploaded
        if 'file' not in request.files:
            logger.warning("No file provided in request")
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            logger.warning("Empty filename")
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({"error": "File type not allowed. Only PDF files are accepted."}), 400
        
        # Parse request settings
        logger.debug("Parsing settings from request")
        settings = {}
        if 'data' in request.form:
            try:
                settings = json.loads(request.form.get('data', '{}'))
                logger.debug(f"Parsed settings: {settings}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON data in request")
                return jsonify({"error": "Invalid JSON data"}), 400
        
        # Create document ID
        document_id = str(uuid.uuid4())
        logger.info(f"Created document ID for analysis: {document_id}")
        
        # Create user directory if it doesn't exist
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_filepath = os.path.join(user_upload_dir, f"temp_{document_id}_{filename}")
        file.save(temp_filepath)
        logger.info(f"Saved temporary file for analysis: {temp_filepath}")
        
        # Create job entry for async processing
        with processing_status_lock:
            processing_status[document_id] = {
                "status": "processing",
                "progress": 0,
                "message": "Starting analysis..."
            }
            # Save status to file
            save_status_to_file(document_id, processing_status[document_id])
        
        # If it's just analysis (not full processing), do it in a background thread
        get_executor().submit(
            analyze_document_background,
            temp_filepath,
            document_id,
            settings
        )
        
        # Return job ID for status polling
        return jsonify({
            "jobId": document_id,
            "status": "processing",
            "message": "Document analysis started"
        })
        
    except Exception as e:
        logger.error(f"Error starting document analysis: {e}")
        return jsonify({"error": f"Failed to analyze document: {str(e)}"}), 500

@documents_bp.route('/analyze/<document_id>', methods=['GET'])
@optional_auth
def get_analysis_status(document_id):
    """Get document analysis status and results"""
    try:
        # Get user ID from auth middleware
        user_id = g.user_id if hasattr(g, 'user_id') else 'default_user'
        
        # Check status in memory first
        with processing_status_lock:
            if document_id in processing_status:
                status_data = processing_status[document_id]
                
                # If completed, return results too
                if status_data.get("status") == "completed" and "result" in status_data:
                    return jsonify({
                        "status": "completed",
                        "result": status_data["result"]
                    })
                
                # Otherwise just return status
                return jsonify(status_data)
        
        # If not in memory, check status file
        status_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_status.json")
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                
                # If completed, check for results file
                if status_data.get("status") == "completed":
                    results_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_results.json")
                    if os.path.exists(results_file):
                        with open(results_file, 'r') as f:
                            results_data = json.load(f)
                        
                        return jsonify({
                            "status": "completed",
                            "result": results_data
                        })
                
                return jsonify(status_data)
            except Exception as e:
                logger.error(f"Error reading status file: {e}")
        
        # Not found
        return jsonify({
            "status": "error",
            "error": "Analysis job not found"
        }), 404
        
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        return jsonify({"error": f"Failed to get analysis status: {str(e)}"}), 500