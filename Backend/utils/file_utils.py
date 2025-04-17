# Backend/utils/file_utils.py
"""
Zentralisierte Dateioperationen mit Caching-Unterstützung,
einheitlicher Fehlerbehandlung und optimierter Performance.
"""
import os
import json
import logging
import tempfile
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, BinaryIO
from werkzeug.utils import secure_filename
from flask import current_app

from config import config_manager
from utils.error_handler import APIError

logger = logging.getLogger(__name__)

# In-Memory-Cache für häufig gelesene Dateien
_file_cache: Dict[str, Any] = {}
_json_cache: Dict[str, Dict[str, Any]] = {}
_cache_enabled = True
_max_cache_size = 100  # Maximale Anzahl von Cache-Einträgen

def get_upload_folder(user_id: str = None) -> str:
    """
    Erstellt und gibt den Pfad zum Upload-Verzeichnis zurück
    
    Args:
        user_id: Optionale Benutzer-ID für benutzerspezifisches Verzeichnis
        
    Returns:
        str: Pfad zum Upload-Verzeichnis
    """
    upload_folder = config_manager.get('UPLOAD_FOLDER', './uploads')
    
    if user_id:
        user_folder = os.path.join(upload_folder, user_id)
        os.makedirs(user_folder, exist_ok=True)
        return user_folder
    
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

def get_status_folder() -> str:
    """
    Erstellt und gibt den Pfad zum Status-Verzeichnis zurück
    
    Returns:
        str: Pfad zum Status-Verzeichnis
    """
    upload_folder = config_manager.get('UPLOAD_FOLDER', './uploads')
    status_folder = os.path.join(upload_folder, 'status')
    os.makedirs(status_folder, exist_ok=True)
    return status_folder

def get_safe_filepath(document_id: str, filename: str, user_id: str = None) -> str:
    """
    Erstellt einen sicheren Dateipfad für hochgeladene Dateien
    
    Args:
        document_id: Dokument-ID
        filename: Originaldateiname
        user_id: Optionale Benutzer-ID
        
    Returns:
        str: Sicherer Dateipfad
    """
    upload_folder = get_upload_folder(user_id)
    safe_filename = secure_filename(filename)
    return os.path.join(upload_folder, f"{document_id}_{safe_filename}")

def save_uploaded_file(file: BinaryIO, document_id: str, user_id: str = None) -> dict:
    """
    Speichert eine hochgeladene Datei sicher
    
    Args:
        file: Dateiobjekt (z.B. aus request.files)
        document_id: Dokument-ID
        user_id: Optionale Benutzer-ID
        
    Returns:
        dict: Informationen zur gespeicherten Datei
        
    Raises:
        APIError: Wenn die Datei nicht gespeichert werden konnte
    """
    if not file or file.filename == '':
        raise APIError("Keine Datei ausgewählt", 400)
    
    # Prüfe Dateierweiterung
    allowed_extensions = config_manager.get('ALLOWED_EXTENSIONS', {'pdf'})
    extension = Path(file.filename).suffix.lower().lstrip('.')
    
    if extension not in allowed_extensions:
        raise APIError(f"Dateityp nicht erlaubt. Erlaubte Typen: {', '.join(allowed_extensions)}", 400)
    
    # Sichere Datei speichern
    try:
        filename = secure_filename(file.filename)
        filepath = get_safe_filepath(document_id, filename, user_id)
        file.save(filepath)
        
        return {
            'document_id': document_id,
            'filename': filename,
            'filepath': filepath,
            'filesize': os.path.getsize(filepath),
            'extension': extension
        }
        
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Datei: {e}")
        raise APIError(f"Datei konnte nicht gespeichert werden: {str(e)}", 500)

def read_json(filepath: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Liest eine JSON-Datei mit Caching-Unterstützung
    
    Args:
        filepath: Pfad zur JSON-Datei
        use_cache: Ob der Cache verwendet werden soll
        
    Returns:
        dict: Geladene JSON-Daten oder None bei Fehler
    """
    global _json_cache, _cache_enabled
    
    # Cache-Prüfung
    cache_key = filepath
    if _cache_enabled and use_cache and cache_key in _json_cache:
        # Gib eine Kopie zurück, um Modifikationen zu verhindern
        return _json_cache[cache_key].copy()
    
    # Datei lesen
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
            # Im Cache speichern, wenn aktiviert
            if _cache_enabled and use_cache:
                # Cache-Größe begrenzen
                if len(_json_cache) >= _max_cache_size:
                    # Entferne ältesten Eintrag (erste Schlüssel)
                    oldest_key = next(iter(_json_cache))
                    del _json_cache[oldest_key]
                
                _json_cache[cache_key] = data.copy()
            
            return data
            
    except json.JSONDecodeError:
        logger.error(f"Ungültiges JSON-Format in {filepath}")
        return None
    except FileNotFoundError:
        logger.error(f"Datei nicht gefunden: {filepath}")
        return None
    except Exception as e:
        logger.error(f"Fehler beim Lesen der JSON-Datei {filepath}: {e}")
        return None

def write_json(filepath: str, data: Dict[str, Any], atomic: bool = True) -> bool:
    """
    Schreibt Daten in eine JSON-Datei mit atomaren Schreiboperationen
    
    Args:
        filepath: Pfad zur JSON-Datei
        data: Zu schreibende Daten
        atomic: Ob atomares Schreiben verwendet werden soll
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    global _json_cache, _cache_enabled
    
    try:
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        if atomic:
            # Atomares Schreiben mit temporärer Datei
            temp_file = f"{filepath}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomare Ersetzung
            os.replace(temp_file, filepath)
        else:
            # Direktes Schreiben
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        # Cache aktualisieren
        if _cache_enabled:
            _json_cache[filepath] = data.copy()
        
        return True
        
    except Exception as e:
        logger.error(f"Fehler beim Schreiben der JSON-Datei {filepath}: {e}")
        return False

def create_temp_file(content: Union[str, bytes], suffix: str = None) -> str:
    """
    Erstellt eine temporäre Datei mit dem angegebenen Inhalt
    
    Args:
        content: Dateiinhalt (Text oder Bytes)
        suffix: Optionale Dateiendung
        
    Returns:
        str: Pfad zur temporären Datei
        
    Raises:
        APIError: Wenn die Datei nicht erstellt werden konnte
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        if isinstance(content, str):
            temp_file.write(content.encode('utf-8'))
        else:
            temp_file.write(content)
            
        temp_file.close()
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der temporären Datei: {e}")
        raise APIError(f"Temporäre Datei konnte nicht erstellt werden: {str(e)}", 500)

def cleanup_file(filepath: str) -> bool:
    """
    Löscht eine Datei sicher
    
    Args:
        filepath: Pfad zur Datei
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
            
            # Cache-Einträge entfernen
            if filepath in _json_cache:
                del _json_cache[filepath]
            if filepath in _file_cache:
                del _file_cache[filepath]
                
            return True
        return False
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Datei {filepath}: {e}")
        return False

def find_files(pattern: str, directory: str = None, recursive: bool = False) -> List[str]:
    """
    Findet Dateien anhand eines Musters
    
    Args:
        pattern: Glob-Muster für die Dateisuche
        directory: Optionales Verzeichnis (Standard: Upload-Verzeichnis)
        recursive: Ob rekursiv gesucht werden soll
        
    Returns:
        list: Liste gefundener Dateipfade
    """
    if not directory:
        directory = get_upload_folder()
    
    try:
        path = Path(directory)
        if recursive:
            files = list(path.glob(f"**/{pattern}"))
        else:
            files = list(path.glob(pattern))
        
        return [str(f) for f in files]
    except Exception as e:
        logger.error(f"Fehler bei der Dateisuche mit Muster '{pattern}': {e}")
        return []

def allowed_file(filename: str) -> bool:
    """
    Prüft, ob die Dateierweiterung erlaubt ist
    
    Args:
        filename: Dateiname
        
    Returns:
        bool: True wenn Datei erlaubt, sonst False
    """
    allowed_extensions = config_manager.get('ALLOWED_EXTENSIONS', {'pdf'})
    extension = Path(filename).suffix.lower().lstrip('.')
    return extension in allowed_extensions

def disable_cache():
    """Deaktiviert den Datei-Cache (z.B. für Tests)"""
    global _cache_enabled
    _cache_enabled = False
    _json_cache.clear()
    _file_cache.clear()

def enable_cache():
    """Aktiviert den Datei-Cache"""
    global _cache_enabled
    _cache_enabled = True

def clear_cache():
    """Leert den Datei-Cache"""
    global _json_cache, _file_cache
    _json_cache.clear()
    _file_cache.clear()