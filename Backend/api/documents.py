# Backend/api/documents.py
"""
Blueprint for document management API endpoints
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
from pathlib import Path

# Eigene Services importieren
from services.pdf_processor import PDFProcessor
from services.vector_db import store_document_chunks, delete_document, get_or_create_collection
from utils.helpers import allowed_file, extract_doi, extract_isbn, get_safe_filepath

# Metadata-API für DOI/ISBN-Abfragen importieren
from api.metadata import fetch_metadata_from_crossref

logger = logging.getLogger(__name__)

# Blueprint für Dokument-API erstellen
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

@documents_bp.route('', methods=['GET'])
def list_documents():
    """Liste aller Dokumente abrufen"""
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        documents = []
        
        # Alle JSON-Metadatendateien durchsuchen
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        metadata_files = list(upload_folder.glob("*.json"))
        
        for file in metadata_files:
            with open(file, 'r') as f:
                metadata = json.load(f)
                documents.append(metadata)
        
        # Nach Uploaddatum sortieren, neueste zuerst
        return jsonify(sorted(documents, key=lambda x: x.get('upload_date', ''), reverse=True))
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({"error": str(e)}), 500

@documents_bp.route('/<document_id>', methods=['GET'])
def get_document(document_id):
    """Spezifisches Dokument anhand seiner ID abrufen"""
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Metadatendatei finden
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        metadata_files = list(upload_folder.glob(f"{document_id}_*.json"))
        
        if not metadata_files:
            return jsonify({"error": "Document not found"}), 404
            
        with open(metadata_files[0], 'r') as f:
            metadata = json.load(f)
            
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        return jsonify({"error": str(e)}), 500

@documents_bp.route('', methods=['POST'])
def save_document():
    """Neues Dokument hochladen und verarbeiten"""
    try:
        if 'file' not in request.files and not request.form.get('data'):
            return jsonify({"error": "No file or data provided"}), 400
            
        # Metadaten aus dem Formular extrahieren
        metadata = {}
        if 'data' in request.form:
            try:
                metadata = json.loads(request.form.get('data', '{}'))
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid JSON data"}), 400
        
        # Dokument-ID generieren, falls nicht vorhanden
        document_id = metadata.get('id', str(uuid.uuid4()))
        
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # PDF-Datei verarbeiten, falls vorhanden
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
                
            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed. Only PDF files are accepted."}), 400
            
            # Datei sicher speichern
            filename = secure_filename(file.filename)
            filepath = get_safe_filepath(document_id, filename)
            file.save(filepath)
            
            try:
                # PDF-Verarbeitung mit den benutzerdefinierten Einstellungen
                processing_settings = {
                    'maxPages': int(metadata.get('maxPages', 0)),
                    'performOCR': bool(metadata.get('performOCR', False)),
                    'chunkSize': int(metadata.get('chunkSize', 1000)),
                    'chunkOverlap': int(metadata.get('chunkOverlap', 200))
                }
                
                # PDF verarbeiten
                pdf_processor = PDFProcessor()
                result = pdf_processor.process_file(filepath, processing_settings)
                
                # Extrahierte Daten den Metadaten hinzufügen
                if 'doi' not in metadata or not metadata['doi']:
                    metadata['doi'] = result['metadata'].get('doi')
                
                if 'isbn' not in metadata or not metadata['isbn']:
                    metadata['isbn'] = result['metadata'].get('isbn')
                    
                # Metadaten über DOI oder ISBN abrufen, falls nicht bereits angegeben
                if not metadata.get('title') and (metadata.get('doi') or metadata.get('isbn')):
                    # Zuerst DOI versuchen
                    if metadata.get('doi'):
                        crossref_metadata = fetch_metadata_from_crossref(metadata['doi'])
                        if crossref_metadata:
                            # Crossref-Metadaten formatieren und hinzufügen
                            metadata.update({
                                "title": crossref_metadata.get("title", [""]) if isinstance(crossref_metadata.get("title"), list) else crossref_metadata.get("title", ""),
                                "authors": crossref_metadata.get("author", []),
                                "publicationDate": crossref_metadata.get("published", {}).get("date-parts", [[""]])[0][0],
                                "journal": crossref_metadata.get("container-title", [""]) if isinstance(crossref_metadata.get("container-title"), list) else "",
                                "publisher": crossref_metadata.get("publisher", ""),
                                "volume": crossref_metadata.get("volume", ""),
                                "issue": crossref_metadata.get("issue", ""),
                                "pages": crossref_metadata.get("page", ""),
                                "type": crossref_metadata.get("type", ""),
                            })
                    
                    # TODO: ISBN-Metadaten abrufen, wenn DOI nicht erfolgreich war
                    
                # Chunks in Vektordatenbank speichern
                if result['chunks'] and len(result['chunks']) > 0:
                    # User-ID zu Metadaten hinzufügen
                    metadata['user_id'] = user_id
                    
                    # Chunks in der Vektordatenbank speichern
                    store_document_chunks(
                        document_id=document_id,
                        chunks=result['chunks'],
                        metadata={
                            "user_id": user_id,
                            "document_id": document_id,
                            "title": metadata.get('title', ''),
                            "authors": metadata.get('authors', []),
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
                    
                    # Metadaten mit Chunk-Info aktualisieren
                    metadata['processed'] = True
                    metadata['num_chunks'] = len(result['chunks'])
                    metadata['chunk_size'] = processing_settings['chunkSize']
                    metadata['chunk_overlap'] = processing_settings['chunkOverlap']
                
                # Upload-Metadaten hinzufügen
                metadata['document_id'] = document_id
                metadata['filename'] = filename
                metadata['fileSize'] = os.path.getsize(filepath)
                metadata['uploadDate'] = datetime.utcnow().isoformat() + 'Z'
                metadata['filePath'] = filepath
                
                # Metadaten als JSON-Datei neben der PDF speichern
                metadata_path = f"{filepath}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return jsonify(metadata)
                
            except Exception as e:
                # Aufräumen bei Fehler
                if os.path.exists(filepath):
                    os.unlink(filepath)
                logger.error(f"Error processing document: {e}")
                return jsonify({"error": f"Failed to process document: {str(e)}"}), 500
                
        # Wenn nur Metadaten aktualisiert werden sollen (ohne Datei)
        else:
            try:
                # Dokument finden
                upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
                files = list(upload_folder.glob(f"{document_id}_*"))
                if not files:
                    return jsonify({"error": "Document not found"}), 404
                    
                # PDF-Datei finden
                pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
                if not pdf_files:
                    return jsonify({"error": "PDF file not found"}), 404
                
                filepath = str(pdf_files[0])
                
                # Metadaten aktualisieren
                metadata['document_id'] = document_id
                metadata['updateDate'] = datetime.utcnow().isoformat() + 'Z'
                
                # Metadaten als JSON-Datei speichern
                metadata_path = f"{filepath}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return jsonify(metadata)
                
            except Exception as e:
                logger.error(f"Error updating document metadata: {e}")
                return jsonify({"error": f"Failed to update document: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Error in save_document: {e}")
        return jsonify({"error": f"Failed to save document: {str(e)}"}), 500

@documents_bp.route('/<document_id>', methods=['DELETE'])
def delete_document_api(document_id):
    """Dokument löschen"""
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Alle Dateien für dieses Dokument suchen
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        files = list(upload_folder.glob(f"{document_id}_*"))
        
        if not files:
            return jsonify({"error": "Document not found"}), 404
        
        # PDF und Metadatendateien löschen
        for file in files:
            try:
                file.unlink()
            except Exception as e:
                logger.error(f"Error deleting file {file}: {e}")
        
        # Aus Vektordatenbank löschen
        delete_document(document_id, user_id)
        
        return jsonify({"success": True, "message": f"Document {document_id} deleted successfully"})
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        return jsonify({"error": f"Failed to delete document: {str(e)}"}), 500

@documents_bp.route('/<document_id>', methods=['PUT'])
def update_document(document_id):
    """Dokument aktualisieren"""
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        metadata = request.get_json()
        
        # Dokument finden
        upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
        files = list(upload_folder.glob(f"{document_id}_*"))
        
        if not files:
            return jsonify({"error": "Document not found"}), 404
            
        # PDF-Datei finden
        pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
        if not pdf_files:
            return jsonify({"error": "PDF file not found"}), 404
        
        filepath = str(pdf_files[0])
        
        # Bestehende Metadaten laden und aktualisieren
        metadata_path = f"{filepath}.json"
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                existing_metadata = json.load(f)
            # Metadaten aktualisieren, bestehende Werte beibehalten
            existing_metadata.update(metadata)
            metadata = existing_metadata
        
        # Update-Datum hinzufügen
        metadata['document_id'] = document_id
        metadata['updateDate'] = datetime.utcnow().isoformat() + 'Z'
        
        # Metadaten speichern
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify(metadata)
        
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}")
        return jsonify({"error": f"Failed to update document: {str(e)}"}), 500