# Backend/api/documents.py
import os
import json
import logging
import uuid
import tempfile
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename

# Eigene Services importieren
from services.pdf_processor import PDFProcessor
from services.vector_db import store_document_chunks, delete_document

# Metadaten-API für DOI/ISBN-Abfragen
from api.metadata import get_doi_metadata, get_isbn_metadata, format_crossref_metadata

logger = logging.getLogger(__name__)

# Blueprint für Dokument-API erstellen
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

# Konfiguration
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 20 * 1024 * 1024))  # 20 MB Standardgröße

# Upload-Verzeichnis erstellen, falls nicht vorhanden
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Prüft, ob die Datei eine zulässige Erweiterung hat"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@documents_bp.route('', methods=['GET'])
def get_documents():
    """
    Alle Dokumente des aktuellen Benutzers abrufen
    """
    try:
        # TODO: Benutzerauthentifizierung
        # In einer echten Implementierung würde hier der Benutzer aus dem JWT-Token extrahiert
        # Für dieses Beispiel verwenden wir einen Dummy-Benutzer
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # TODO: Aus Datenbank laden
        # Hier würden die Dokumente normalerweise aus einer Datenbank geladen
        # Für dieses Beispiel erstellen wir eine Dummy-Liste
        
        # Dummy-Dokumente für Testzwecke
        documents = [
            {
                "id": "doc1",
                "title": "Climate Change Effects on Agricultural Systems",
                "authors": [
                    {"name": "Smith, John", "orcid": "0000-0001-2345-6789"},
                    {"name": "Johnson, Maria", "orcid": "0000-0002-3456-7890"}
                ],
                "type": "article",
                "publicationDate": "2023-04-15",
                "journal": "Journal of Environmental Science",
                "doi": "10.1234/jes.2023.01.001", 
                "publisher": "Academic Press",
                "uploadDate": "2024-04-01T12:30:45Z",
                "abstract": "This paper examines the impact of climate change on agricultural systems worldwide..."
            },
            {
                "id": "doc2",
                "title": "Machine Learning Applications in Medicine",
                "authors": [
                    {"name": "Brown, Robert", "orcid": "0000-0003-4567-8901"},
                    {"name": "Davis, Sarah", "orcid": "0000-0004-5678-9012"}
                ],
                "type": "article",
                "publicationDate": "2023-08-22",
                "journal": "Medical Informatics Journal",
                "doi": "10.5678/mij.2023.02.005",
                "publisher": "Medical Science Publications",
                "uploadDate": "2024-04-02T09:15:30Z",
                "abstract": "This review explores the current and future applications of machine learning in clinical settings..."
            }
        ]
        
        return jsonify(documents)
    
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return jsonify({"error": "Failed to retrieve documents"}), 500


@documents_bp.route('/<document_id>', methods=['GET'])
def get_document(document_id):
    """
    Einzelnes Dokument anhand der ID abrufen
    """
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # TODO: Aus Datenbank laden
        # Hier würde das Dokument normalerweise aus einer Datenbank geladen
        
        # Dummy-Dokument für Testzwecke
        if document_id == "doc1":
            document = {
                "id": "doc1",
                "title": "Climate Change Effects on Agricultural Systems",
                "authors": [
                    {"name": "Smith, John", "orcid": "0000-0001-2345-6789"},
                    {"name": "Johnson, Maria", "orcid": "0000-0002-3456-7890"}
                ],
                "type": "article",
                "publicationDate": "2023-04-15",
                "journal": "Journal of Environmental Science",
                "doi": "10.1234/jes.2023.01.001",
                "publisher": "Academic Press",
                "uploadDate": "2024-04-01T12:30:45Z",
                "abstract": "This paper examines the impact of climate change on agricultural systems worldwide..."
            }
            return jsonify(document)
        else:
            return jsonify({"error": "Document not found"}), 404
    
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        return jsonify({"error": f"Failed to retrieve document {document_id}"}), 500


@documents_bp.route('', methods=['POST'])
def save_document():
    """
    Neues Dokument speichern (PDF hochladen und verarbeiten)
    """
    try:
        # Prüfen, ob Anfrage eine Datei oder JSON enthält
        has_file = 'file' in request.files
        has_data = 'data' in request.form or request.is_json
        
        if not (has_file or has_data):
            return jsonify({"error": "No file or document data provided"}), 400
        
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Metadaten extrahieren (entweder aus Form-Daten oder JSON-Body)
        if has_data:
            if 'data' in request.form:
                document_data = json.loads(request.form['data'])
            elif request.is_json:
                document_data = request.get_json()
        else:
            document_data = {}
        
        # PDF-Datei verarbeiten
        pdf_file = None
        file_path = None
        extracted_text = None
        chunks = []
        pdf_metadata = {}
        
        if has_file:
            file = request.files['file']
            
            # Dateiname validieren
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            
            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed. Only PDF files are accepted."}), 400
            
            # Datei sicher speichern
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{filename}")
            file.save(file_path)
            
            # Verarbeitungseinstellungen
            max_pages = int(document_data.get('maxPages', 0))
            perform_ocr = bool(document_data.get('performOCR', False))
            chunk_size = int(document_data.get('chunkSize', 1000))
            chunk_overlap = int(document_data.get('chunkOverlap', 200))
            
            # PDF verarbeiten
            extraction_result = PDFProcessor.extract_text_from_pdf(
                file_path, 
                max_pages=max_pages,
                perform_ocr=perform_ocr
            )
            
            # Extrahierten Text speichern
            extracted_text = extraction_result['text']
            
            # Chunks erstellen
            chunks = PDFProcessor.chunk_text_semantic(
                extracted_text,
                chunk_size=chunk_size,
                overlap_size=chunk_overlap
            )
            
            # DOI und ISBN extrahieren
            doi = PDFProcessor.extract_doi(extracted_text)
            isbn = PDFProcessor.extract_isbn(extracted_text)
            
            pdf_metadata = {
                "doi": doi,
                "isbn": isbn,
                "pages": extraction_result['pages'],
                "totalPages": extraction_result['totalPages'],
                "processedPages": extraction_result['processedPages']
            }
            
            # Metadaten über DOI oder ISBN abrufen, falls nicht bereits angegeben
            metadata = document_data.get('metadata', {})
            
            if not metadata.get('title') and (doi or isbn):
                fetched_metadata = None
                
                # Zuerst DOI versuchen
                if doi:
                    try:
                        response = get_doi_metadata(doi)
                        if response and response.status_code == 200:
                            fetched_metadata = response.get_json()
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for DOI {doi}: {e}")
                
                # Falls keine DOI-Metadaten, ISBN versuchen
                if not fetched_metadata and isbn:
                    try:
                        response = get_isbn_metadata(isbn)
                        if response and response.status_code == 200:
                            fetched_metadata = response.get_json()
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for ISBN {isbn}: {e}")
                
                # Gefundene Metadaten verwenden
                if fetched_metadata:
                    metadata = fetched_metadata
            
            # Metadaten mit PDF-Metadaten ergänzen
            metadata.update(pdf_metadata)
            document_data['metadata'] = metadata
        
        # Dokument-ID generieren
        document_id = str(uuid.uuid4())
        
        # Speicherzeit setzen
        upload_date = datetime.utcnow().isoformat() + 'Z'
        
        # Dokument-Objekt erstellen
        document = {
            "id": document_id,
            "user_id": user_id,
            "title": document_data.get('metadata', {}).get('title', "Untitled Document"),
            "authors": document_data.get('metadata', {}).get('authors', []),
            "type": document_data.get('metadata', {}).get('type', 'other'),
            "publicationDate": document_data.get('metadata', {}).get('publicationDate', ''),
            "journal": document_data.get('metadata', {}).get('journal', ''),
            "volume": document_data.get('metadata', {}).get('volume', ''),
            "issue": document_data.get('metadata', {}).get('issue', ''),
            "pages": document_data.get('metadata', {}).get('pages', ''),
            "publisher": document_data.get('metadata', {}).get('publisher', ''),
            "doi": document_data.get('metadata', {}).get('doi', ''),
            "isbn": document_data.get('metadata', {}).get('isbn', ''),
            "abstract": document_data.get('metadata', {}).get('abstract', ''),
            "uploadDate": upload_date,
            "fileName": os.path.basename(file_path) if file_path else '',
            "fileSize": os.path.getsize(file_path) if file_path else 0,
            "processingSettings": {
                "maxPages": document_data.get('maxPages', 0),
                "performOCR": document_data.get('performOCR', False),
                "chunkSize": document_data.get('chunkSize', 1000),
                "chunkOverlap": document_data.get('chunkOverlap', 200)
            }
        }
        
        # Optional: Volltext und Chunks speichern (in einer echten Implementierung)
        # document['fullText'] = extracted_text
        
        # In Vektordatenbank speichern
        if chunks and len(chunks) > 0:
            store_success = store_document_chunks(
                document_id=document_id,
                chunks=chunks,
                metadata={
                    "user_id": user_id,
                    "title": document["title"],
                    "authors": document["authors"],
                    "type": document["type"],
                    "publicationDate": document["publicationDate"],
                    "journal": document["journal"],
                    "publisher": document["publisher"],
                    "doi": document["doi"],
                    "isbn": document["isbn"],
                    "pages": pdf_metadata.get("pages", [])
                }
            )
            
            if not store_success:
                logger.warning(f"Failed to store chunks for document {document_id} in vector database")
        
        # TODO: In Datenbank speichern
        # In einer echten Implementierung würde das Dokument hier in einer Datenbank gespeichert
        
        # Aufräumen: Temporäre Datei löschen
        if file_path and os.path.exists(file_path):
            # In einer echten Implementierung könnte die Datei behalten werden
            # Hier löschen wir sie nach der Verarbeitung
            os.unlink(file_path)
        
        return jsonify(document)
    
    except Exception as e:
        logger.error(f"Error saving document: {e}")
        # Aufräumen bei Fehler
        if 'file_path' in locals() and file_path and os.path.exists(file_path):
            os.unlink(file_path)
        return jsonify({"error": f"Failed to save document: {str(e)}"}), 500


@documents_bp.route('/<document_id>', methods=['PUT'])
def update_document(document_id):
    """
    Dokument aktualisieren
    """
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        document_data = request.get_json()
        
        # TODO: In Datenbank aktualisieren
        # In einer echten Implementierung würde das Dokument hier in der Datenbank aktualisiert
        
        # Dummy-Antwort für dieses Beispiel
        document = {
            "id": document_id,
            "title": document_data.get('title', "Untitled Document"),
            "authors": document_data.get('authors', []),
            "type": document_data.get('type', 'other'),
            "publicationDate": document_data.get('publicationDate', ''),
            "journal": document_data.get('journal', ''),
            "publisher": document_data.get('publisher', ''),
            "doi": document_data.get('doi', ''),
            "isbn": document_data.get('isbn', ''),
            "abstract": document_data.get('abstract', ''),
            "updatedAt": datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(document)
    
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}")
        return jsonify({"error": f"Failed to update document {document_id}"}), 500


@documents_bp.route('/<document_id>', methods=['DELETE'])
def delete_document_api(document_id):
    """
    Dokument löschen
    """
    try:
        # TODO: Benutzerauthentifizierung
        user_id = request.headers.get('X-User-ID', 'default_user')
        
        # Dokument aus Vektordatenbank löschen
        vector_db_delete = delete_document(document_id, user_id)
        
        # TODO: Aus Datenbank löschen
        # In einer echten Implementierung würde das Dokument hier aus der Datenbank gelöscht
        
        # TODO: PDF-Datei löschen, falls vorhanden
        
        return jsonify({"success": True, "message": f"Document {document_id} deleted"})
    
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        return jsonify({"error": f"Failed to delete document {document_id}"}), 500