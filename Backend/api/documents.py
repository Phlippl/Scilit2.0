# Backend/api/documents.py
"""
Blueprint for document management API endpoints
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, g
from werkzeug.utils import secure_filename
from pathlib import Path
import time
import concurrent.futures
from typing import Dict, List, Any, Optional, Union
import threading
import jwt
import re

# Import services
from services.pdf_processor import PDFProcessor
from services.vector_db import store_document_chunks, delete_document, get_or_create_collection
from utils.helpers import allowed_file, extract_doi, extract_isbn, get_safe_filepath, timeout_handler
from utils.auth_middleware import optional_auth  # Import auth middleware

# Import metadata API for DOI/ISBN queries
from api.metadata import fetch_metadata_from_crossref

logger = logging.getLogger(__name__)

# Create Blueprint for document API
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

# Create processor instance (shared to avoid recreation)
pdf_processor = PDFProcessor()

# Thread pool for background processing
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def get_executor():
    """
    Gibt den Thread-Pool-Executor zurück, erstellt ihn neu, wenn nötig
    
    Returns:
        ThreadPoolExecutor: Der Thread-Pool-Executor für Hintergrundaufgaben
    """
    global executor
    try:
        # Prüfen, ob der Executor noch funktioniert
        executor.submit(lambda: None).result(timeout=0.1)
        return executor
    except Exception as e:
        # Wenn Executor nicht funktioniert oder geschlossen wurde, einen neuen erstellen
        logger.info(f"Erstelle neuen Executor wegen: {str(e)}")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        return executor

# In-memory processing status tracking (for real app, use Redis or database)
processing_status = {}

# Thread-safe storage for processing status
processing_status_lock = threading.Lock()

def save_status_to_file(document_id, status_data):
    """Save document processing status to file with app context"""
    try:
        status_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status')
        os.makedirs(status_dir, exist_ok=True)
        
        status_file = os.path.join(status_dir, f"{document_id}_status.json")
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
            
        return True
    except Exception as e:
        logger.error(f"Error saving status to file: {e}")
        return False

def process_pdf_background(filepath, document_id, metadata, settings):
    """
    Process PDF file in background thread with improved error handling
    
    Args:
        filepath: Path to the PDF file
        document_id: Document ID
        metadata: Document metadata
        settings: Processing settings
    """
    from flask import current_app
    import gc
    gc.enable()  # Enable garbage collection
    
    # Mit einem Anwendungskontext arbeiten
    from app import create_app
    app = create_app()
    with app.app_context():
        # Set reasonable limits
        max_file_size_mb = 20 #50  # Maximum file size to process in MB
        
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
        
            # Update status
            with processing_status_lock:
                processing_status[document_id] = {
                    "status": "processing",
                    "progress": 0,
                    "message": "Starting PDF processing..."
                }
                # Save status to file
                save_status_to_file(document_id, processing_status[document_id])
            
            # Progress update callback with improved error handling
            def update_progress(message, progress):
                try:
                    with processing_status_lock:
                        processing_status[document_id] = {
                            "status": "processing",
                            "progress": progress,
                            "message": message
                        }
                        # Save status to file
                        save_status_to_file(document_id, processing_status[document_id])
                except Exception as e:
                    logger.error(f"Error updating progress for document {document_id}: {str(e)}")
            
            # Process PDF file
            try:
                # Check if the file is a valid PDF
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
                            author_strings = []
                            for author in authors_data:
                                if isinstance(author, dict) and 'name' in author:
                                    author_strings.append(author['name'])
                                elif isinstance(author, str):
                                    author_strings.append(author)
                            metadata['authors'] = author_strings
                        
                        # Store chunks in vector database
                        store_result = store_document_chunks(
                            document_id=document_id,
                            chunks=pdf_result['chunks'],
                            metadata={
                                "user_id": user_id,
                                "document_id": document_id,
                                "title": metadata.get('title', ''),
                                "authors": ", ".join(metadata.get('authors', [])) if isinstance(metadata.get('authors'), list) else metadata.get('authors', ''),
                                "type": metadata.get('type', 'other'),
                                "publicationDate": metadata.get('publicationDate', ''),
                                "journal": metadata.get('journal', ''),
                                "publisher": metadata.get('publisher', ''),
                                "doi": metadata.get('doi', ''),
                                "isbn": metadata.get('isbn', ''),
                                "volume": metadata.get('volume', ''),
                                "issue": metadata.get('issue', ''),
                                "pages": metadata.get('pages', '')
                            }
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
                    with processing_status_lock:
                        processing_status[document_id] = {
                            "status": "completed",
                            "progress": 100,
                            "message": "Document processing completed"
                        }
                        # Save status to file
                        save_status_to_file(document_id, processing_status[document_id])
                else:
                    with processing_status_lock:
                        processing_status[document_id] = {
                            "status": "completed_with_warnings",
                            "progress": 100,
                            "message": "Document processed but chunks could not be stored"
                        }
                        # Save status to file
                        save_status_to_file(document_id, processing_status[document_id])
                    
            except Exception as e:
                logger.error(f"Error processing PDF {document_id}: {str(e)}", exc_info=True)
                update_progress(f"Error processing PDF: {str(e)}", 0)
                
                # Update metadata with detailed error
                metadata['processingComplete'] = False
                metadata['processingError'] = str(e)
                metadata['processedDate'] = datetime.utcnow().isoformat() + 'Z'
                
                # Save error metadata
                try:
                    metadata_path = f"{filepath}.json"
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                except Exception as write_err:
                    logger.error(f"Error saving error metadata: {write_err}")
            
            # Hilfsfunktion für direkten Cleanup ohne Executor hinzufügen
            def cleanup_status_direct(doc_id):
                """Cleanup function that works without executor"""
                with processing_status_lock:
                    if doc_id in processing_status:
                        del processing_status[doc_id]
                        logger.info(f"Cleaned up status for document {doc_id} via direct method")

            # Clean up status after 10 minutes
            def cleanup_status():
                time.sleep(600)  # 10 minutes
                with processing_status_lock:
                    if document_id in processing_status:
                        del processing_status[document_id]
            
            try:
                if not executor._shutdown:  # Prüfen, ob der Executor noch aktiv ist
                    executor.submit(cleanup_status)
                else:
                    # Alternative: Timer verwenden, wenn Executor bereits heruntergefahren ist
                    import threading
                    cleanup_timer = threading.Timer(600, lambda: cleanup_status_direct(document_id))
                    cleanup_timer.daemon = True  # Daemon-Thread wird beendet, wenn das Hauptprogramm endet
                    cleanup_timer.start()
                    logger.info(f"Using Timer instead of Executor for cleanup of document {document_id}")
            except Exception as e:
                logger.warning(f"Could not schedule cleanup for document {document_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error in background processing for document {document_id}: {str(e)}", exc_info=True)
            
            # Update status to error with detailed message
            with processing_status_lock:
                processing_status[document_id] = {
                    "status": "error",
                    "progress": 0,
                    "message": f"Error processing document: {str(e)}"
                }
                # Save status to file
                save_status_to_file(document_id, processing_status[document_id])
                
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

@documents_bp.route('/status/<document_id>', methods=['GET'])
def get_document_status(document_id):
    """Gets the processing status of a document with improved error handling"""
    try:
        # User authentication
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
        
        # Check in-memory status first
        with processing_status_lock:
            if document_id in processing_status:
                # Also save to file for persistence
                save_status_to_file(document_id, processing_status[document_id])
                return jsonify(processing_status[document_id])
            
        # If not in memory, check status file
        status_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_status.json")
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                return jsonify(status_data)
            except Exception as e:
                logger.error(f"Error reading status file: {e}")
        
        # Check metadata file to determine status
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        metadata_files = list(Path(user_upload_dir).glob(f"{document_id}_*.json"))
        
        if not metadata_files:
            return jsonify({"error": "Document not found"}), 404
        
        # Check metadata file to determine status
        try:
            with open(metadata_files[0], 'r') as f:
                metadata = json.load(f)
                
            # If processing is flagged as complete
            if metadata.get('processingComplete', False):
                return jsonify({
                    "status": "completed",
                    "progress": 100,
                    "message": "Document processing completed"
                })
            
            # If processing failed
            if metadata.get('processingError'):
                return jsonify({
                    "status": "error",
                    "progress": 0,
                    "message": metadata.get('processingError', 'Unknown error')
                })
        except Exception as e:
            logger.error(f"Error reading metadata file for status: {e}")
        
        # If no status found, assume pending
        return jsonify({
            "status": "pending",
            "progress": 0,
            "message": "Document processing not started or status unknown"
        })
            
    except Exception as e:
        logger.error(f"Error retrieving status for document {document_id}: {e}")
        return jsonify({
            "status": "error", 
            "message": f"Error retrieving status: {str(e)}"
        }), 500

@documents_bp.route('', methods=['GET'])
def list_documents():
    """Get list of all documents"""
    try:
        # Authentication check
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

def validate_metadata(metadata):
    """
    Validate document metadata structure and content
    
    Args:
        metadata: Document metadata to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(metadata, dict):
        return False, "Metadata must be a dictionary"
    
    # Required fields validation
    required_fields = ['title', 'type']
    for field in required_fields:
        if field not in metadata or not metadata[field]:
            return False, f"Required field '{field}' is missing or empty"
    
    # Title validation
    if len(metadata.get('title', '')) > 500:
        return False, "Title is too long (max 500 characters)"
    
    # Type validation
    valid_types = ['article', 'book', 'edited_book', 'conference', 'thesis', 
                  'report', 'newspaper', 'website', 'interview', 'press', 'other']
    if metadata.get('type') not in valid_types:
        return False, f"Invalid document type. Must be one of: {', '.join(valid_types)}"
    
    # Authors validation
    if 'authors' in metadata:
        authors = metadata['authors']
        if not isinstance(authors, list):
            return False, "Authors must be a list"
        
        for i, author in enumerate(authors):
            if isinstance(author, dict):
                if 'name' not in author:
                    return False, f"Author at position {i} is missing required 'name' field"
            elif isinstance(author, str):
                # Convert string authors to dict format for consistency
                authors[i] = {'name': author}
            else:
                return False, f"Invalid author format at position {i}"
    
    # Date validation
    date_fields = ['publicationDate', 'date', 'lastUpdated', 'accessDate']
    for field in date_fields:
        if field in metadata and metadata[field]:
            date_value = metadata[field]
            
            # Basic ISO date format validation (YYYY-MM-DD)
            if isinstance(date_value, str):
                # Full ISO date
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_value):
                    # Year only
                    if not re.match(r'^\d{4}$', date_value):
                        # Year-Month
                        if not re.match(r'^\d{4}-\d{2}$', date_value):
                            return False, f"Invalid date format for {field}. Use YYYY-MM-DD, YYYY-MM or YYYY"
            else:
                return False, f"Date field {field} must be a string"
    
    # DOI validation
    if 'doi' in metadata and metadata['doi']:
        doi = metadata['doi']
        if not re.match(r'^10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+$', doi):
            return False, "Invalid DOI format. DOIs should start with '10.'"
    
    # ISBN validation
    if 'isbn' in metadata and metadata['isbn']:
        isbn = metadata['isbn'].replace('-', '').replace(' ', '')
        if not (len(isbn) == 10 or len(isbn) == 13):
            return False, "Invalid ISBN length. Must be 10 or 13 digits."
        if not isbn.isdigit() and not (isbn[:-1].isdigit() and isbn[-1] in '0123456789Xx'):
            return False, "Invalid ISBN format. Must contain only digits (except for ISBN-10 check digit 'X')"
    
    # Check for excessive field lengths
    long_text_fields = {
        'abstract': 10000,
        'title': 500,
        'journal': 200,
        'publisher': 200
    }
    
    for field, max_length in long_text_fields.items():
        if field in metadata and isinstance(metadata[field], str) and len(metadata[field]) > max_length:
            return False, f"Field '{field}' exceeds maximum length of {max_length} characters"
    
    return True, None

@documents_bp.route('', methods=['POST'])
def save_document():
    """Upload und Verarbeitung eines neuen Dokuments mit verbesserter Validierung"""
    try:
        # Prüfen, ob Datei oder Metadaten vorhanden sind
        if 'file' not in request.files and not request.form.get('data'):
            return jsonify({"error": "Keine Datei oder Daten bereitgestellt"}), 400
        
        # Metadaten aus dem Formular extrahieren
        metadata = {}
        if 'data' in request.form:
            try:
                metadata = json.loads(request.form.get('data', '{}'))
                
                # Prüfe, ob title direkt im request.form vorhanden ist (Fix)
                if 'title' in request.form and request.form['title']:
                    metadata['title'] = request.form['title']
                
                # Prüfe, ob type direkt im request.form vorhanden ist (Fix)
                if 'type' in request.form and request.form['type']:
                    metadata['type'] = request.form['type']
                
                # Prüfe, ob authors direkt im request.form vorhanden ist (Fix)
                if 'authors' in request.form and request.form['authors']:
                    try:
                        metadata['authors'] = json.loads(request.form['authors'])
                    except:
                        pass  # Ignoriere Fehler beim authors-Parsing
                
            except json.JSONDecodeError:
                return jsonify({"error": "Ungültige JSON-Daten"}), 400
        
        # Metadatenvalidierung durchführen
        is_valid, error_message = validate_metadata(metadata)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Dokument-ID generieren, falls nicht vorhanden
        document_id = metadata.get('id', str(uuid.uuid4()))
        
        # Benutzer-Authentifizierung: Zuerst über JWT, ansonsten Fallback über X-User-ID Header
        user_id = 'default_user'
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # Robustere Token-Validierung
            if token and token.count('.') == 2:
                try:
                    secret_key = current_app.config['SECRET_KEY']
                    payload = jwt.decode(token, secret_key, algorithms=['HS256'])
                    user_id = payload.get('sub', user_id)
                except Exception as e:
                    logger.warning(f"JWT-Decodierung fehlgeschlagen: {e}")
            else:
                logger.warning(f"Ungültiges Token-Format: {token}")
        else:
            header_user_id = request.headers.get('X-User-ID')
            if header_user_id:
                user_id = header_user_id
                
            # Log für Debugging-Zwecke
            logger.info(f"Kein Authorization-Header gefunden. Verwendung von X-User-ID: {user_id}")
        
        metadata['user_id'] = user_id
        
        # Benutzer-spezifisches Upload-Verzeichnis erstellen
        user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Wenn eine Datei hochgeladen wurde, verarbeite den Upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "Keine Datei ausgewählt"}), 400
            
            if not allowed_file(file.filename):
                return jsonify({"error": "Dateityp nicht erlaubt. Nur PDF-Dateien werden akzeptiert."}), 400
            
            filename = secure_filename(file.filename)
            filepath = os.path.join(user_upload_dir, f"{document_id}_{filename}")
            
            try:
                file.save(filepath)
            except Exception as e:
                logger.error(f"Fehler beim Speichern der Datei: {e}")
                return jsonify({"error": f"Dateiupload fehlgeschlagen: {str(e)}"}), 500
            
            # Optional: Speichern der Dokument-Metadaten in einer Datenbank
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
                    logger.warning(f"Dokument konnte nicht in Datenbank gespeichert werden für User: {user_id}")
            except Exception as e:
                logger.warning(f"Fehler beim Speichern in der Datenbank: {e}")
                # Falls die DB-Speicherung fehlschlägt, wird der Upload fortgesetzt
            
            try:
                # Verarbeitungseinstellungen aus den Metadaten extrahieren
                processing_settings = {
                    'maxPages': int(metadata.get('maxPages', 0)),
                    'performOCR': bool(metadata.get('performOCR', False)),
                    'chunkSize': int(metadata.get('chunkSize', 1000)),
                    'chunkOverlap': int(metadata.get('chunkOverlap', 200))
                }
                
                # Upload-spezifische Metadaten ergänzen
                metadata['document_id'] = document_id
                metadata['filename'] = filename
                metadata['fileSize'] = os.path.getsize(filepath)
                metadata['uploadDate'] = datetime.utcnow().isoformat() + 'Z'
                metadata['filePath'] = filepath
                metadata['processingComplete'] = False
                
                # Initiale Metadaten in einer JSON-Datei speichern
                metadata_path = f"{filepath}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Mit App-Kontext ausführen
                app = current_app._get_current_object()
                
                # Hintergrundverarbeitung starten
                get_executor().submit(
                    process_pdf_background,
                    filepath,
                    document_id,
                    metadata,
                    processing_settings
                )
                
                # Initialen Status speichern
                initial_status = {
                    "status": "processing",
                    "progress": 0,
                    "message": "Dokumentupload abgeschlossen. Verarbeitung gestartet..."
                }
                with processing_status_lock:
                    processing_status[document_id] = initial_status
                    
                    # Status mit App-Kontext speichern
                    with app.app_context():
                        save_status_to_file(document_id, initial_status)
                
                return jsonify({
                    **metadata,
                    "processing_status": initial_status
                })
                
            except Exception as e:
                # Aufräumen im Fehlerfall
                if os.path.exists(filepath):
                    os.unlink(filepath)
                logger.error(f"Fehler bei der Verarbeitung des Dokuments: {e}")
                return jsonify({"error": f"Fehler beim Verarbeiten des Dokuments: {str(e)}"}), 500
        
        # Fall: Es werden nur Metadaten-Updates durchgeführt (ohne Datei-Upload)
        else:
            try:
                user_upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], user_id)
                files = list(Path(user_upload_dir).glob(f"{document_id}_*"))
                if not files:
                    return jsonify({"error": "Dokument nicht gefunden"}), 404
                
                pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
                if not pdf_files:
                    return jsonify({"error": "PDF-Datei nicht gefunden"}), 404
                
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
        delete_document(document_id, user_id)
        
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

# Backend/api/documents.py - Add these new endpoints

@timeout_handler(max_seconds=120, cpu_limit=70)
def analyze_document_background(filepath, document_id, settings):
    """
    Background task to analyze a document
    
    Args:
        filepath: Path to the document
        document_id: Document ID
        settings: Processing settings
    """
    from flask import current_app
    import gc
    gc.enable()  # Enable garbage collection
    
    # Create app context
    from app import create_app
    app = create_app()
    
    with app.app_context():
        try:
            # Update status
            with processing_status_lock:
                processing_status[document_id] = {
                    "status": "processing",
                    "progress": 10,
                    "message": "Analyzing document..."
                }
                # Save status to file
                save_status_to_file(document_id, processing_status[document_id])
            
            # Define progress update callback
            def update_progress(message, progress):
                try:
                    with processing_status_lock:
                        processing_status[document_id] = {
                            "status": "processing",
                            "progress": progress,
                            "message": message
                        }
                        # Save status to file
                        save_status_to_file(document_id, processing_status[document_id])
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
            
            # Process the file
            result = pdf_processor.process_file(
                filepath,
                settings=processing_settings,
                progress_callback=update_progress
            )
            
            # Limit chunks to avoid overwhelming the response
            MAX_CHUNKS_IN_RESPONSE = 100
            if len(result['chunks']) > MAX_CHUNKS_IN_RESPONSE:
                logger.info(f"Limiting chunks in response from {len(result['chunks'])} to {MAX_CHUNKS_IN_RESPONSE}")
                result['limitedChunks'] = True
                result['totalChunks'] = len(result['chunks'])
                result['chunks'] = result['chunks'][:MAX_CHUNKS_IN_RESPONSE]
            
            # Store result for retrieval
            with processing_status_lock:
                processing_status[document_id] = {
                    "status": "completed",
                    "progress": 100,
                    "message": "Analysis complete",
                    "result": {
                        "metadata": result['metadata'],
                        "chunks": result['chunks'],
                        "totalPages": result['metadata'].get('totalPages', 0),
                        "processedPages": result['metadata'].get('processedPages', 0)
                    }
                }
                
                # Save results to separate file (status file might have size limits)
                results_file = os.path.join(current_app.config['UPLOAD_FOLDER'], 'status', f"{document_id}_results.json")
                with open(results_file, 'w') as f:
                    json.dump({
                        "metadata": result['metadata'],
                        "chunks": result['chunks'],
                        "totalPages": result['metadata'].get('totalPages', 0),
                        "processedPages": result['metadata'].get('processedPages', 0)
                    }, f, default=str)
                
                # Save status to file
                save_status_to_file(document_id, {
                    "status": "completed",
                    "progress": 100,
                    "message": "Analysis complete"
                })
            
            # Clean up temporary file
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            except Exception as e:
                logger.error(f"Error deleting temporary file {filepath}: {e}")
                
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            logger.error(f"Error in document analysis: {e}")
            
            # Update status to reflect error
            with processing_status_lock:
                processing_status[document_id] = {
                    "status": "error",
                    "progress": 0,
                    "error": str(e),
                    "message": f"Error analyzing document: {str(e)}"
                }
                # Save status to file
                save_status_to_file(document_id, processing_status[document_id])
            
            # Clean up temporary file
            try:
                if os.path.exists(filepath):
                    os.unlink(filepath)
            except Exception as cleanup_error:
                logger.error(f"Error deleting temporary file {filepath}: {cleanup_error}")
            
            # Force garbage collection
            gc.collect()

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