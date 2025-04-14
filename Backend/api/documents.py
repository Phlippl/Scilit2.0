# api/documents.py
from flask import Blueprint, request, jsonify, current_app
import os
import uuid
import json
from datetime import datetime
from werkzeug.utils import secure_filename

from services.pdf_processor import PDFProcessor
from services.vector_db import store_document_chunks
from api.metadata import fetch_metadata_from_crossref
from utils.helpers import allowed_file

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")

processor = PDFProcessor()

# In-Memory-Status (später Redis nutzen!)
processing_status = {}

@documents_bp.route('/status/<document_id>', methods=['GET'])
def get_status(document_id):
    return jsonify(processing_status.get(document_id, {
        "status": "pending",
        "progress": 0,
        "message": "Warte auf Start..."
    }))


@documents_bp.route('', methods=['POST'])
def upload_document():
    try:
        # Datei und Metadaten extrahieren
        if 'file' not in request.files:
            return jsonify({"error": "Keine Datei übergeben"}), 400
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({"error": "Nur PDF-Dateien erlaubt"}), 400

        # Metadaten
        data = request.form.get("data", "{}")
        try:
            metadata = json.loads(data)
        except json.JSONDecodeError:
            return jsonify({"error": "Ungültige Metadaten"}), 400

        # Benutzerdaten
        user_id = metadata.get("user_id", "default_user")
        document_id = metadata.get("document_id", str(uuid.uuid4()))

        filename = secure_filename(file.filename)
        upload_folder = os.environ.get("UPLOAD_FOLDER", "./uploads")
        user_folder = os.path.join(upload_folder, user_id)
        os.makedirs(user_folder, exist_ok=True)
        file_path = os.path.join(user_folder, f"{document_id}_{filename}")
        file.save(file_path)

        # Verarbeitungseinstellungen
        settings = {
            "performOCR": metadata.get("performOCR", True)
        }

        # Fortschrittsfunktion
        def progress_callback(msg, percent):
            processing_status[document_id] = {
                "status": "processing",
                "progress": int(percent),
                "message": msg
            }

        progress_callback("Starte Verarbeitung", 0)

        # PDF verarbeiten
        result = processor.process_file(file_path, settings=settings, progress_callback=progress_callback)

        progress_callback("Hole Metadaten (CrossRef)...", 90)

        # Metadaten anreichern
        doi = result['metadata'].get('doi')
        isbn = result['metadata'].get('isbn')

        if doi:
            crossref_data = fetch_metadata_from_crossref(doi)
            if crossref_data:
                metadata.update(crossref_data)
        elif isbn:
            metadata['isbn'] = isbn

        metadata.setdefault("title", os.path.splitext(filename)[0])
        metadata["user_id"] = user_id
        metadata["document_id"] = document_id
        metadata["uploadDate"] = datetime.utcnow().isoformat()
        metadata["processedDate"] = datetime.utcnow().isoformat()

        # Chunks speichern
        progress_callback("Speichere Chunks in Vektordatenbank...", 95)
        store_document_chunks(document_id=document_id, chunks=result["chunks"], metadata=metadata)

        # Finaler Status
        processing_status[document_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Verarbeitung abgeschlossen"
        }

        return jsonify({
            "document_id": document_id,
            "title": metadata.get("title", ""),
            "pages": result["metadata"]["totalPages"],
            "num_chunks": len(result["chunks"]),
            "doi": doi,
            "isbn": isbn,
            "status": "completed"
        })

    except Exception as e:
        document_id = metadata.get("document_id", "unknown")
        processing_status[document_id] = {
            "status": "error",
            "progress": 0,
            "message": f"Fehler: {str(e)}"
        }
        return jsonify({"error": f"Verarbeitung fehlgeschlagen: {str(e)}"}), 500
