# Backend/api/documents/controller.py
"""
Zentrale Controller-Funktionen für Document-API-Endpunkte, die die Logik von document_api.py
vereinfachen und Wiederholungen reduzieren.
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, g, Response, stream_with_context
from werkzeug.utils import secure_filename
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
import concurrent.futures

from utils.auth_middleware import get_user_id
from utils.error_handler import APIError, bad_request, not_found, server_error
from utils.file_utils import (
    get_upload_folder, get_safe_filepath, allowed_file, save_uploaded_file,
    read_json, write_json, find_files, cleanup_file
)
from utils.metadata_utils import validate_metadata, format_metadata_for_storage
from services.status_service import get_status_service

# Importiere Services
from services.documents.processor import DocumentProcessor, process_document_background

# Thread-Pool für Hintergrundaufgaben
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Configure logging
logger = logging.getLogger(__name__)

def get_executor() -> concurrent.futures.ThreadPoolExecutor:
    """
    Holt den Thread-Pool-Executor für Hintergrundaufgaben
    
    Returns:
        ThreadPoolExecutor: Executor für Hintergrundaufgaben
    """
    return executor

def list_documents() -> Tuple[List[Dict[str, Any]], int]:
    """
    Listet alle Dokumente eines Benutzers auf
    
    Returns:
        tuple: (documents, status_code)
    """
    try:
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Liste Dokumente für Benutzer: {user_id}")
        
        documents = []
        
        # Benutzerspezifisches Verzeichnis
        user_upload_dir = get_upload_folder(user_id)
        if not os.path.exists(user_upload_dir):
            logger.info(f"Benutzerverzeichnis existiert nicht: {user_upload_dir}")
            return [], 200
        
        # Suche JSON-Metadaten-Dateien im Benutzerverzeichnis
        json_files = find_files("*.json", user_upload_dir)
        logger.debug(f"Gefundene Metadatendateien: {len(json_files)}")
        
        for file_path in json_files:
            # Ignoriere temporäre Dateien und Statusdateien
            if '_status.json' in file_path or '_results.json' in file_path:
                continue
                
            # Lade Metadaten
            metadata = read_json(file_path)
            if metadata:
                documents.append(metadata)
                logger.debug(f"Dokument hinzugefügt: {metadata.get('id', 'unbekannt')}")
        
        # Nach Uploaddatum sortieren, neueste zuerst
        return sorted(
            documents, 
            key=lambda x: x.get('uploadDate', ''), 
            reverse=True
        ), 200
        
    except Exception as e:
        logger.error(f"Fehler beim Auflisten der Dokumente: {e}", exc_info=True)
        raise APIError(f"Fehler beim Auflisten der Dokumente: {str(e)}", 500)

def get_document(document_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Holt ein spezifisches Dokument anhand der ID
    
    Args:
        document_id: Dokument-ID
        
    Returns:
        tuple: (document, status_code)
    """
    try:
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Hole Dokument {document_id} für Benutzer {user_id}")
        
        # Suche Metadaten-Datei
        user_upload_dir = get_upload_folder(user_id)
        metadata_files = find_files(f"{document_id}_*.json", user_upload_dir)
        
        if not metadata_files:
            raise APIError(f"Dokument {document_id} nicht gefunden", 404)
            
        # Lade Metadaten
        metadata = read_json(metadata_files[0])
        if not metadata:
            raise APIError("Ungültige Dokument-Metadaten", 500)
        
        # Verarbeitungsstatus hinzufügen
        metadata['processing_status'] = get_status_service().get_status(document_id)
            
        return metadata, 200
        
    except APIError as e:
        # APIError durchreichen
        raise
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Dokuments {document_id}: {e}", exc_info=True)
        raise APIError(f"Fehler beim Abrufen des Dokuments: {str(e)}", 500)

def save_document(file, metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Speichert ein neues Dokument
    
    Args:
        file: Datei-Objekt
        metadata: Dokument-Metadaten
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Metadaten validieren
        is_valid, error_message = validate_metadata(metadata)
        if not is_valid:
            raise APIError(error_message, 400)
        
        # Dokument-ID generieren, falls nicht vorhanden
        document_id = metadata.get('id', str(uuid.uuid4()))
        logger.info(f"Verarbeite Dokument {document_id}")
        
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Benutzer-ID: {user_id}")
        
        metadata['user_id'] = user_id
        
        # Prüfe auf temp_document_id für bereits hochgeladene Datei
        temp_document_id = metadata.get('temp_document_id')
        filepath = None
        
        if temp_document_id:
            logger.info(f"Temporäre Dokument-ID vorhanden: {temp_document_id}")
            temp_files = find_files(f"temp_{temp_document_id}_*", get_upload_folder(user_id))
            if temp_files:
                temp_filepath = temp_files[0]
                filename = os.path.basename(temp_filepath).replace(f"temp_{temp_document_id}_", "")
                filepath = get_safe_filepath(document_id, filename, user_id)
                
                # Benenne temporäre Datei in permanente Datei um
                os.rename(temp_filepath, filepath)
                logger.info(f"Temporäre Datei wiederverwendet: {temp_filepath} -> {filepath}")
        
        # Wenn Datei hochgeladen oder keine temporäre Datei gefunden, verarbeite hochgeladene Datei
        if file and file.filename and file.filename != '' and not filepath:
            if not allowed_file(file.filename):
                raise APIError("Dateityp nicht erlaubt. Nur PDF-Dateien werden akzeptiert.", 400)
            
            # Datei sicher speichern
            filename = secure_filename(file.filename)
            filepath = get_safe_filepath(document_id, filename, user_id)
            
            try:
                file.save(filepath)
                logger.info(f"Hochgeladene Datei gespeichert unter: {filepath}")
            except Exception as e:
                logger.error(f"Fehler beim Speichern der Datei: {e}")
                raise APIError(f"Datei-Upload fehlgeschlagen: {str(e)}", 500)
        
        if not filepath:
            raise APIError("Keine Datei bereitgestellt", 400)
        
        try:
            # Verarbeitungseinstellungen aus Metadaten extrahieren
            processing_settings = {
                'maxPages': int(metadata.get('maxPages', 0)),
                'performOCR': bool(metadata.get('performOCR', False)),
                'chunkSize': int(metadata.get('chunkSize', 1000)),
                'chunkOverlap': int(metadata.get('chunkOverlap', 200))
            }
            logger.debug(f"Verarbeitungseinstellungen: {processing_settings}")
            
            # Upload-spezifische Metadaten hinzufügen
            metadata['document_id'] = document_id
            metadata['filename'] = os.path.basename(filepath)
            metadata['fileSize'] = os.path.getsize(filepath)
            metadata['uploadDate'] = datetime.utcnow().isoformat() + 'Z'
            metadata['filePath'] = filepath
            metadata['processingComplete'] = False
            
            # Initialen Status speichern
            get_status_service().update_status(
                status_id=document_id,
                status="processing",
                progress=0,
                message="Dokument-Upload abgeschlossen. Verarbeitung gestartet..."
            )
            
            # Speichere initiale Metadaten in JSON-Datei
            metadata_path = f"{filepath}.json"
            write_json(metadata_path, metadata)
            
            # Starte Hintergrundverarbeitung
            logger.info(f"Starte Hintergrundverarbeitung für Dokument {document_id}")
            get_executor().submit(
                process_document_background,
                filepath,
                document_id,
                metadata,
                processing_settings
            )
            
            # Aktuellen Verarbeitungsstatus holen
            current_status = get_status_service().get_status(document_id)
            
            logger.info(f"Dokument {document_id} erfolgreich hochgeladen und Verarbeitung gestartet")
            return {
                **metadata,
                "document_id": document_id,
                "processing_status": current_status
            }, 200
            
        except Exception as e:
            # Bei Fehler aufräumen
            if os.path.exists(filepath):
                cleanup_file(filepath)
                logger.warning(f"Datei {filepath} aufgrund eines Fehlers gelöscht")
            raise APIError(f"Fehler bei der Dokumentverarbeitung: {str(e)}", 500)
        
    except APIError as e:
        # APIError durchreichen
        raise
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Dokuments: {e}", exc_info=True)
        raise APIError(f"Fehler beim Speichern des Dokuments: {str(e)}", 500)

def delete_document(document_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Löscht ein Dokument
    
    Args:
        document_id: Dokument-ID
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Lösche Dokument {document_id} für Benutzer {user_id}")
        
        # Suche alle Dateien für dieses Dokument im Benutzerverzeichnis
        user_upload_dir = get_upload_folder(user_id)
        files = find_files(f"{document_id}_*", user_upload_dir)
        
        if not files:
            raise APIError(f"Dokument {document_id} nicht gefunden", 404)
        
        # Lösche PDF- und Metadaten-Dateien
        for file_path in files:
            try:
                cleanup_file(file_path)
                logger.debug(f"Datei gelöscht: {file_path}")
            except Exception as e:
                logger.error(f"Fehler beim Löschen der Datei {file_path}: {e}")
        
        # Lösche Statusdatei, falls vorhanden
        status_file = os.path.join(get_upload_folder(), 'status', f"{document_id}_status.json")
        if os.path.exists(status_file):
            try:
                cleanup_file(status_file)
                logger.debug(f"Statusdatei gelöscht: {status_file}")
            except Exception as e:
                logger.error(f"Fehler beim Löschen der Statusdatei {status_file}: {e}")
        
        # Aus Vektordatenbank löschen
        try:
            from services.vector_storage import get_vector_storage
            get_vector_storage().delete_document(document_id, user_id)
            logger.info(f"Dokument {document_id} aus Vektordatenbank gelöscht")
        except Exception as e:
            logger.error(f"Fehler beim Löschen aus Vektordatenbank: {e}")
        
        # Verarbeitungsstatus bereinigen
        get_status_service().cleanup_status(document_id, 0)  # Sofortige Bereinigung
        logger.debug(f"Verarbeitungsstatus für Dokument {document_id} bereinigt")
        
        logger.info(f"Dokument {document_id} erfolgreich gelöscht")
        return {
            "success": True, 
            "message": f"Dokument {document_id} erfolgreich gelöscht"
        }, 200
        
    except APIError as e:
        # APIError durchreichen
        raise
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Dokuments {document_id}: {e}", exc_info=True)
        raise APIError(f"Fehler beim Löschen des Dokuments: {str(e)}", 500)

def update_document(document_id: str, updated_metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Aktualisiert ein Dokument
    
    Args:
        document_id: Dokument-ID
        updated_metadata: Aktualisierte Metadaten
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Aktualisiere Dokument {document_id} für Benutzer {user_id}")
        
        # Suche Dokument im Benutzerverzeichnis
        user_upload_dir = get_upload_folder(user_id)
        files = find_files(f"{document_id}_*", user_upload_dir)
        
        if not files:
            raise APIError(f"Dokument {document_id} nicht gefunden", 404)
            
        # Suche PDF-Datei
        pdf_files = [f for f in files if f.endswith('.pdf')]
        if not pdf_files:
            raise APIError("PDF-Datei nicht gefunden", 404)
        
        filepath = pdf_files[0]
        logger.debug(f"PDF-Datei gefunden unter: {filepath}")
        
        # Lade existierende Metadaten
        metadata_path = f"{filepath}.json"
        if os.path.exists(metadata_path):
            existing_metadata = read_json(metadata_path)
            
            if not existing_metadata:
                raise APIError("Fehler beim Laden der existierenden Metadaten", 500)
            
            # Prüfe auf Änderungen bei kritischen Feldern, die eine Aktualisierung
            # in der Vektordatenbank erfordern
            update_chunks = False
            critical_fields = ['title', 'authors', 'publicationDate', 'journal', 'publisher', 'doi', 'isbn']
            
            for field in critical_fields:
                if field in updated_metadata and updated_metadata[field] != existing_metadata.get(field):
                    logger.info(f"Kritisches Feld '{field}' geändert, Vektordatenbank wird aktualisiert")
                    update_chunks = True
                    break
            
            # Zusammenführen mit existierenden Metadaten
            merged_metadata = {**existing_metadata, **updated_metadata}
            
            # Wenn kritische Felder aktualisiert wurden, aktualisiere Vektordatenbank
            if update_chunks and merged_metadata.get('processed') and merged_metadata.get('num_chunks', 0) > 0:
                logger.info(f"Kritische Metadaten geändert, aktualisiere Vektordatenbank für Dokument {document_id}")
                try:
                    # Verarbeitungseinstellungen holen
                    processing_settings = {
                        'maxPages': merged_metadata.get('maxPages', 0),
                        'performOCR': merged_metadata.get('performOCR', False),
                        'chunkSize': merged_metadata.get('chunk_size', 1000),
                        'chunkOverlap': merged_metadata.get('chunk_overlap', 200)
                    }
                    
                    # Status aktualisieren
                    get_status_service().update_status(
                        status_id=document_id,
                        status="processing",
                        progress=0,
                        message="Aktualisiere Dokumentmetadaten..."
                    )
                    
                    # Starte Hintergrundverarbeitung
                    logger.info(f"Starte Hintergrundverarbeitung für Dokumentaktualisierung {document_id}")
                    get_executor().submit(
                        process_document_background,
                        filepath,
                        document_id,
                        merged_metadata,
                        processing_settings
                    )
                    
                    merged_metadata['processingComplete'] = False
                except Exception as e:
                    logger.error(f"Fehler beim Aktualisieren der Vektordatenbank: {e}", exc_info=True)
        else:
            # Keine existierenden Metadaten gefunden
            merged_metadata = updated_metadata
            merged_metadata['document_id'] = document_id
        
        # Aktualisierungszeitstempel hinzufügen
        merged_metadata['updateDate'] = datetime.utcnow().isoformat() + 'Z'
        
        # Metadaten speichern
        write_json(metadata_path, merged_metadata)
        logger.info(f"Aktualisierte Metadaten für Dokument {document_id} gespeichert")
        
        return merged_metadata, 200
        
    except APIError as e:
        # APIError durchreichen
        raise
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Dokuments {document_id}: {e}", exc_info=True)
        raise APIError(f"Fehler beim Aktualisieren des Dokuments: {str(e)}", 500)

def quick_analyze(file) -> Tuple[Dict[str, Any], int]:
    """
    Führt eine schnelle Analyse für DOI/ISBN-Extraktion durch
    
    Args:
        file: Datei-Objekt
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        if not file or file.filename == '':
            raise APIError("Keine Datei bereitgestellt", 400)
            
        if not allowed_file(file.filename):
            raise APIError("Dateityp nicht erlaubt. Nur PDF-Dateien werden akzeptiert.", 400)
        
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Führe Quick-Analyze für Benutzer {user_id} durch")
        
        # Temporäre Datei speichern
        temp_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        user_upload_dir = get_upload_folder(user_id)
        filepath = os.path.join(user_upload_dir, f"temp_{temp_id}_{filename}")
        file.save(filepath)
        logger.info(f"Datei temporär gespeichert unter: {filepath}")
        
        # Extraktionseinstellungen konfigurieren
        max_pages = 10
        perform_ocr = False
        
        # PDF-Processor für Extraktion verwenden
        from services.pdf import get_pdf_processor
        pdf_processor = get_pdf_processor()
        
        try:
            logger.info(f"Starte Identifikator-Extraktion aus {filepath}")
            result = pdf_processor.extract_identifiers_only(filepath, max_pages)
            logger.info(f"Extraktionsergebnis: {result}")
            
            # Metadaten abrufen, falls DOI gefunden wurde
            metadata = {}
            if result.get('doi'):
                doi = result['doi']
                logger.info(f"DOI gefunden: {doi}, versuche Metadaten abzurufen")
                try:
                    from api.metadata import fetch_metadata_from_crossref
                    
                    crossref_metadata = fetch_metadata_from_crossref(doi)
                    
                    # Wenn Metadaten abgerufen wurden
                    if crossref_metadata:
                        logger.info(f"Metadaten für DOI {doi} erfolgreich abgerufen")
                        from utils.metadata_utils import format_metadata_for_storage
                        metadata = format_metadata_for_storage(crossref_metadata)
                except ImportError as e:
                    logger.warning(f"Metadata-API nicht verfügbar: {e}")
                except Exception as e:
                    logger.warning(f"Fehler beim Abrufen der DOI-Metadaten: {e}", exc_info=True)
            
            # Falls ISBN gefunden, versuche OpenLibrary
            elif result.get('isbn'):
                isbn = result['isbn']
                logger.info(f"ISBN gefunden: {isbn}, versuche Metadaten abzurufen")
                try:
                    import requests
                    isbn = isbn.replace('-', '').replace(' ', '')
                    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
                    
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
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
                            logger.info(f"Buchmetadaten erfolgreich von OpenLibrary abgerufen")
                except Exception as e:
                    logger.warning(f"Fehler beim Abrufen der ISBN-Metadaten: {e}", exc_info=True)
            
            logger.info(f"Quick-Analyze erfolgreich abgeschlossen für temp_id: {temp_id}")
            return {
                "temp_id": temp_id,
                "filename": filename,
                "metadata": metadata,
                "identifiers": result
            }, 200
            
        except Exception as e:
            logger.error(f"Fehler bei der Identifikator-Extraktion: {e}", exc_info=True)
            
            # Gib auch bei Fehler ein Teilergebnis zurück
            return {
                "temp_id": temp_id,
                "filename": filename,
                "metadata": {},
                "identifiers": {"error": str(e)}
            }, 200
            
    except APIError as e:
        # APIError durchreichen
        raise
    except Exception as e:
        logger.error(f"Fehler bei Quick-Analyze: {e}", exc_info=True)
        raise APIError(f"Fehler bei der Analyse: {str(e)}", 500)

def analyze_document(file, settings: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Analysiert ein Dokument ohne dauerhafte Speicherung
    
    Args:
        file: Datei-Objekt
        settings: Verarbeitungseinstellungen
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Prüfe, ob Datei hochgeladen wurde
        if not file or file.filename == '':
            raise APIError("Keine Datei bereitgestellt", 400)
            
        if not allowed_file(file.filename):
            raise APIError("Dateityp nicht erlaubt. Nur PDF-Dateien werden akzeptiert.", 400)
        
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Starte Dokumentenanalyse für Benutzer {user_id}")
        
        # Dokument-ID erstellen
        document_id = str(uuid.uuid4())
        
        # Datei temporär speichern
        filename = secure_filename(file.filename)
        temp_filepath = os.path.join(get_upload_folder(user_id), f"temp_{document_id}_{filename}")
        file.save(temp_filepath)
        logger.info(f"Temporäre Datei für Analyse gespeichert: {temp_filepath}")
        
        # Job-Eintrag für asynchrone Verarbeitung erstellen
        get_status_service().update_status(
            status_id=document_id,
            status="processing",
            progress=0,
            message="Starte Analyse..."
        )
        
        # Analyse im Hintergrund-Thread starten
        document_processor = DocumentProcessor()
        get_executor().submit(
            lambda: document_processor.analyze(
                filepath=temp_filepath,
                document_id=document_id,
                settings=settings,
                cleanup_file_after=True
            )
        )
        
        # Job-ID für Status-Polling zurückgeben
        return {
            "jobId": document_id,
            "status": "processing",
            "message": "Dokumentenanalyse gestartet"
        }, 200
        
    except APIError as e:
        # APIError durchreichen
        raise
    except Exception as e:
        logger.error(f"Fehler beim Starten der Dokumentenanalyse: {e}", exc_info=True)
        raise APIError(f"Fehler bei der Dokumentenanalyse: {str(e)}", 500)

def get_analysis_status(document_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Holt den Status und die Ergebnisse einer Dokumentenanalyse
    
    Args:
        document_id: Dokument-ID
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Status abrufen
        status_data = get_status_service().get_status(document_id)
        
        # Wenn abgeschlossen, Ergebnisse zurückgeben
        if status_data.get("status") == "completed" and "result" in status_data:
            return {
                "status": "completed",
                "result": status_data["result"]
            }, 200
        
        # Wenn nicht abgeschlossen, nur Status zurückgeben
        return status_data, 200
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Analysestatus: {e}", exc_info=True)
        raise APIError(f"Fehler beim Abrufen des Analysestatus: {str(e)}", 500)

def cancel_processing(document_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Bricht einen laufenden Verarbeitungsprozess ab
    
    Args:
        document_id: Dokument-ID
        
    Returns:
        tuple: (response, status_code)
    """
    try:
        # Benutzer-ID holen
        user_id = get_user_id()
        logger.info(f"Breche Verarbeitung für Dokument {document_id} durch Benutzer {user_id} ab")
        
        # Status auf abgebrochen setzen
        get_status_service().update_status(
            status_id=document_id,
            status="canceled",
            progress=0,
            message="Verarbeitung durch Benutzer abgebrochen"
        )
        logger.info(f"Verarbeitung für Dokument {document_id} erfolgreich abgebrochen")
        
        return {"success": True, "message": "Verarbeitung abgebrochen"}, 200
    except Exception as e:
        logger.error(f"Fehler beim Abbrechen der Verarbeitung: {e}", exc_info=True)
        raise APIError(f"Fehler beim Abbrechen der Verarbeitung: {str(e)}", 500)