# Backend/api/documents/routes.py
"""
API-Routes für die Document-API, die den Controller verwenden.
Diese Datei ersetzt document_api.py und verwendet den neuen Controller für eine sauberere Trennung
zwischen Routing und Geschäftslogik.
"""
import os
import json
import logging
from flask import Blueprint, jsonify, request, current_app, g
from werkzeug.utils import secure_filename
from typing import Dict, Any

from utils.auth_middleware import optional_auth, requires_auth
from utils.error_handler import APIError, safe_execution
from . import controller

# Logger konfigurieren
logger = logging.getLogger(__name__)

# Blueprint für Document-API erstellen
documents_bp = Blueprint('documents', __name__, url_prefix='/api/documents')

@documents_bp.route('', methods=['GET'])
@optional_auth
def list_documents():
    """Listet alle Dokumente des Benutzers auf"""
    try:
        documents, status_code = controller.list_documents()
        return jsonify(documents), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Auflisten der Dokumente: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/<document_id>', methods=['GET'])
@optional_auth
def get_document(document_id):
    """Holt ein spezifisches Dokument anhand der ID"""
    try:
        document, status_code = controller.get_document(document_id)
        return jsonify(document), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Abrufen des Dokuments {document_id}: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('', methods=['POST'])
@optional_auth
def save_document():
    """Lädt ein neues Dokument hoch und verarbeitet es"""
    try:
        # Prüfe, ob Datei oder Metadaten bereitgestellt werden
        if 'file' not in request.files and not request.form.get('data'):
            return jsonify({"error": "Keine Datei oder Daten bereitgestellt"}), 400
        
        # Extrahiere Metadaten aus dem Formular
        metadata = {}
        if 'data' in request.form:
            try:
                metadata = json.loads(request.form.get('data', '{}'))
                
                # Prüfe auf Titel direkt im Formular (Fix)
                if 'title' in request.form and request.form['title']:
                    metadata['title'] = request.form['title']
                
                # Prüfe auf Typ direkt im Formular (Fix)
                if 'type' in request.form and request.form['type']:
                    metadata['type'] = request.form['type']
                
                # Prüfe auf Autoren direkt im Formular (Fix)
                if 'authors' in request.form and request.form['authors']:
                    try:
                        metadata['authors'] = json.loads(request.form['authors'])
                    except:
                        logger.warning("JSON für Autoren im Formularfeld konnte nicht geparst werden")
                
            except json.JSONDecodeError:
                return jsonify({"error": "Ungültige JSON-Daten"}), 400
        
        # Datei aus dem Request holen
        file = request.files.get('file')
        
        # Dokument speichern
        response, status_code = controller.save_document(file, metadata)
        return jsonify(response), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Speichern des Dokuments: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/<document_id>', methods=['DELETE'])
@optional_auth
def delete_document(document_id):
    """Löscht ein Dokument"""
    try:
        response, status_code = controller.delete_document(document_id)
        return jsonify(response), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Löschen des Dokuments {document_id}: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/<document_id>', methods=['PUT'])
@optional_auth
def update_document(document_id):
    """Aktualisiert ein Dokument"""
    try:
        if not request.is_json:
            return jsonify({"error": "Anfrage muss JSON sein"}), 400
        
        updated_metadata = request.get_json()
        response, status_code = controller.update_document(document_id, updated_metadata)
        return jsonify(response), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Aktualisieren des Dokuments {document_id}: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/quick-analyze', methods=['POST'])
@optional_auth
def quick_analyze():
    """Schnelle Analyse für DOI/ISBN-Extraktion"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Keine Datei bereitgestellt"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Keine Datei ausgewählt"}), 400
        
        response, status_code = controller.quick_analyze(file)
        return jsonify(response), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei Quick-Analyze: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/analyze', methods=['POST'])
@optional_auth
def analyze_document():
    """Analysiert ein Dokument ohne dauerhafte Speicherung"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Keine Datei bereitgestellt"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Keine Datei ausgewählt"}), 400
        
        # Parse request settings
        settings = {}
        if 'data' in request.form:
            try:
                settings = json.loads(request.form.get('data', '{}'))
            except json.JSONDecodeError:
                return jsonify({"error": "Ungültige JSON-Daten"}), 400
        
        response, status_code = controller.analyze_document(file, settings)
        return jsonify(response), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Starten der Dokumentenanalyse: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/analyze/<document_id>', methods=['GET'])
@optional_auth
def get_analysis_status(document_id):
    """Holt den Status und die Ergebnisse einer Dokumentenanalyse"""
    try:
        response, status_code = controller.get_analysis_status(document_id)
        return jsonify(response), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Abrufen des Analysestatus: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/cancel-processing/<document_id>', methods=['POST'])
@optional_auth
def cancel_processing(document_id):
    """Bricht einen laufenden Verarbeitungsprozess ab"""
    try:
        response, status_code = controller.cancel_processing(document_id)
        return jsonify(response), status_code
    except APIError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Abbrechen der Verarbeitung: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500

@documents_bp.route('/status/<document_id>', methods=['GET'])
@optional_auth
def get_document_status(document_id):
    """Holt den Verarbeitungsstatus eines Dokuments"""
    try:
        from services.status_service import get_document_status
        status = get_document_status(document_id)
        return jsonify(status)
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Dokumentstatus: {e}", exc_info=True)
        return jsonify({"error": "Interner Serverfehler"}), 500