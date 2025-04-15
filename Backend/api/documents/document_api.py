# Backend/api/documents/documents_api.py
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

# Import utils and services
from utils.helpers import allowed_file, get_safe_filepath
from utils.auth_middleware import optional_auth, get_user_id
from services.vector_db import delete_document as delete_from_vector_db

# Import submodules
from .document_processing import process_pdf_background, get_executor
from .document_validation import validate_metadata
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
    return get_document_status(document_id)

@documents_bp.route('', methods=['GET'])
def list_documents():
    """Get list of all documents"""
    try:
        # Get user ID
        user_id = get_user_id()
        
        documents = []
        
        # User-specific directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        if not os.path.exists(user_upload_dir):
            return jsonify([])
        
        # Search JSON metadata files in user directory
        upload_folder = Path(user_upload_dir)
        metadata_files = list(upload_folder.glob("*.json"))
        
        for file in metadata_files:
            try:
                with open(file, 'r') as f:
                    metadata = json.load(f)
                    documents.append(metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in file {file}")
            except Exception as e:
                logger.error(f"Error reading metadata file {file}: {e}")
        
        # Sort by upload date, newest first
        return jsonify(sorted(
            documents, 
            key=lambda x: x.get('uploadDate', ''), 
            reverse=True
        ))
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({"error": str(e)}), 500

@documents_bp.route('/<document_id>', methods=['GET'])
def get_document(document_id):
    """Get specific document by ID"""
    try:
        # Get user ID
        user_id = get_user_id()
        
        # Find metadata file
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        metadata_files = list(Path(user_upload_dir).glob(f"{document_id}_*.json"))
        
        if not metadata_files:
            return jsonify({"error": "Document not found"}), 404
            
        with open(metadata_files[0], 'r') as f:
            metadata = json.load(f)
            
        # Check processing status
        with processing_status_lock:
            if document_id in processing_status:
                metadata['processing_status'] = processing_status[document_id]
            
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        return jsonify({"error": str(e)}), 500

@documents_bp.route('', methods=['POST'])
def save_document():
    """Upload and process a new document with improved validation"""
    try:
        # Check if file or metadata is provided
        if 'file' not in request.files and not request.form.get('data'):
            return jsonify({"error": "No file or data provided"}), 400
        
        # Extract metadata from form
        metadata = {}
        if 'data' in request.form:
            try:
                metadata = json.loads(request.form.get('data', '{}'))
                
                # Check if title is directly in request.form (fix)
                if 'title' in request.form and request.form['title']:
                    metadata['title'] = request.form['title']
                
                # Check if type is directly in request.form (fix)
                if 'type' in request.form and request.form['type']:
                    metadata['type'] = request.form['type']
                
                # Check if authors is directly in request.form (fix)
                if 'authors' in request.form and request.form['authors']:
                    try:
                        metadata['authors'] = json.loads(request.form['authors'])
                    except:
                        pass  # Ignore errors when parsing authors
                
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400
        
        # Validate metadata
        is_valid, error_message = validate_metadata(metadata)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Generate document ID if not provided
        document_id = metadata.get('id', str(uuid.uuid4()))
        
        # Get user ID
        user_id = get_user_id()
        
        metadata['user_id'] = user_id
        
        # Create user-specific upload directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # If file is uploaded, process it
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed. Only PDF files are accepted."}), 400
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(user_upload_dir, f"{document_id}_{filename}")
            
            try:
                file.save(filepath)
            except Exception as e:
                logger.error(f"Error saving file: {e}")
                return jsonify({"error": f"File upload failed: {str(e)}"}), 500
            
            # Optionally save document metadata to database
            try:
                from services.document_db_service import DocumentDBService
                doc_db_service = DocumentDBService()
                
                save_result = doc_db_service.save_document_metadata(
                    document_id=document_id,
                    user_id=user_id,
                    title=metadata.get('title', filename),
                    file_name=filename,
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
                
                # Add upload-specific metadata
                metadata['document_id'] = document_id
                metadata['filename'] = filename
                metadata['fileSize'] = os.path.getsize(filepath)
                metadata['uploadDate'] = datetime.utcnow().isoformat() + 'Z'
                metadata['filePath'] = filepath
                metadata['processingComplete'] = False
                
                # Save initial metadata to JSON file
                metadata_path = f"{filepath}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Get current app object
                app = current_app._get_current_object()
                
                # Start background processing
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
                
                return jsonify({
                    **metadata,
                    "processing_status": initial_status
                })
                
            except Exception as e:
                # Clean up on error
                if os.path.exists(filepath):
                    os.unlink(filepath)
                logger.error(f"Error processing document: {e}")
                return jsonify({"error": f"Error processing document: {str(e)}"}), 500
        
        # If only metadata updates are being made (no file upload)
        else:
            try:
                user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
                files = list(Path(user_upload_dir).glob(f"{document_id}_*"))
                if not files:
                    return jsonify({"error": "Document not found"}), 404
                
                pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
                if not pdf_files:
                    return jsonify({"error": "PDF file not found"}), 404
                
                filepath = str(pdf_files[0])
                metadata['document_id'] = document_id
                metadata['updateDate'] = datetime.utcnow().isoformat() + 'Z'
                
                metadata_path = f"{filepath}.json"
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        existing_metadata = json.load(f)
                    # Zusammenführen der neuen und bestehenden Metadaten
                    metadata = {**existing_metadata, **metadata}
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return jsonify(metadata)
                
            except Exception as e:
                logger.error(f"Fehler beim Aktualisieren der Dokument-Metadaten: {e}")
                return jsonify({"error": f"Fehler beim Aktualisieren des Dokuments: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Fehler in save_document: {e}")
        return jsonify({"error": f"Fehler beim Speichern des Dokuments: {str(e)}"}), 500

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
        
        # Find all files for this document in user's directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        files = list(Path(user_upload_dir).glob(f"{document_id}_*"))
        
        if not files:
            return jsonify({"error": "Document not found"}), 404
        
        # Delete PDF and metadata files
        for file in files:
            try:
                file.unlink()
            except Exception as e:
                logger.error(f"Error deleting file {file}: {e}")
        
        # Delete status file if exists
        status_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_status.json")
        if os.path.exists(status_file):
            try:
                os.unlink(status_file)
            except Exception as e:
                logger.error(f"Error deleting status file {status_file}: {e}")
        
        # Delete from vector database
        delete_from_vector_db(document_id, user_id)
        
        # Clear any processing status
        with processing_status_lock:
            if document_id in processing_status:
                del processing_status[document_id]
        
        return jsonify({"success": True, "message": f"Document {document_id} deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
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
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        metadata = request.get_json()
        
        # Find document in user's directory
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        files = list(Path(user_upload_dir).glob(f"{document_id}_*"))
        
        if not files:
            return jsonify({"error": "Document not found"}), 404
            
        # Find PDF file
        pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
        if not pdf_files:
            return jsonify({"error": "PDF file not found"}), 404
        
        filepath = str(pdf_files[0])
        
        # Load existing metadata
        metadata_path = f"{filepath}.json"
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                existing_metadata = json.load(f)
            
            # Process specific fields that need updating in the vector database
            update_chunks = False
            critical_fields = ['title', 'authors', 'publicationDate', 'journal', 'publisher', 'doi', 'isbn']
            
            for field in critical_fields:
                if field in metadata and metadata[field] != existing_metadata.get(field):
                    update_chunks = True
                    break
            
            # Merge with existing metadata
            merged_metadata = {**existing_metadata, **metadata}
            metadata = merged_metadata
            
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
                    
                    # Start background processing
                    get_executor().submit(
                        process_pdf_background,
                        filepath,
                        document_id,
                        metadata,
                        processing_settings
                    )
                    
                    metadata['processingComplete'] = False
                except Exception as e:
                    logger.error(f"Error updating vector database: {e}")
        
        # Add update timestamp
        metadata['document_id'] = document_id
        metadata['updateDate'] = datetime.utcnow().isoformat() + 'Z'
        
        # Save metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}")
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
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed. Only PDF files are accepted."}), 400
        
        # Parse request settings
        settings = {}
        if 'data' in request.form:
            try:
                settings = json.loads(request.form.get('data', '{}'))
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400
        
        # Create document ID
        document_id = str(uuid.uuid4())
        
        # Create user directory if it doesn't exist
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_filepath = os.path.join(user_upload_dir, f"temp_{document_id}_{filename}")
        file.save(temp_filepath)
        
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