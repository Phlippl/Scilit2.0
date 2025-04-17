# Backend/services/status_service.py
"""
Zentralisierter Status-Management-Service mit Observer-Pattern und verbesserten 
Speicher-Funktionen. Dient als Ersatz für das alte Status-Tracking-System.
"""
import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime
from config import config_manager
from utils import file_utils

logger = logging.getLogger(__name__)

class StatusService:
    """Zentraler Service für Statusverwaltung mit Observer-Pattern"""
    
    def __init__(self, storage_dir: str = None):
        """
        Initialisiert den StatusService
        
        Args:
            storage_dir: Optionales Verzeichnis für Statusdateien
        """
        self._status_data = {}  # In-Memory-Status
        self._status_lock = threading.RLock()  # RLock für Thread-Sicherheit
        self._observers = {}  # Callbacks nach Status-ID
        self._storage_dir = storage_dir
        self._inactive_ids = set()  # IDs inaktiver Status
    
    def set_storage_dir(self, storage_dir: str):
        """
        Setzt das Verzeichnis für Statusdateien
        
        Args:
            storage_dir: Verzeichnis für Statusdateien
        """
        self._storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        logger.info(f"StatusService Speicherverzeichnis gesetzt: {storage_dir}")
    
    def get_status(self, status_id: str) -> Dict[str, Any]:
        """
        Gibt den aktuellen Status zurück
        
        Args:
            status_id: Status-ID
            
        Returns:
            dict: Aktueller Status
        """
        with self._status_lock:
            # Prüfe, ob Status inaktiv ist
            if status_id in self._inactive_ids:
                return {
                    "status": "inactive",
                    "message": "Status ist nicht mehr aktiv",
                    "updated_at": datetime.utcnow().isoformat() + 'Z'
                }
            
            # Zuerst im Memory-Cache nachsehen
            if status_id in self._status_data:
                return self._status_data[status_id].copy()
            
            # Falls nicht im Cache, aus Datei laden
            if self._storage_dir:
                status_file = os.path.join(self._storage_dir, f"{status_id}_status.json")
                try:
                    status_data = file_utils.read_json(status_file)
                    if status_data:
                        # In Cache laden
                        self._status_data[status_id] = status_data
                        return status_data.copy()
                except Exception as e:
                    logger.error(f"Fehler beim Laden des Status aus Datei: {e}")
        
        # Standardstatus, wenn nichts gefunden wurde
        return {
            "status": "unknown",
            "message": "Status nicht gefunden",
            "updated_at": datetime.utcnow().isoformat() + 'Z'
        }
    
    def update_status(
        self, 
        status_id: str, 
        status: str,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Aktualisiert den Status und benachrichtigt Observer
        
        Args:
            status_id: Status-ID
            status: Statustext (z.B. "processing", "completed", "error")
            progress: Optionaler Fortschritt (0-100)
            message: Optionale Nachricht
            result: Optionales Ergebnis
            
        Returns:
            bool: True bei Erfolg
        """
        try:
            # Prüfe, ob Status inaktiv ist
            with self._status_lock:
                if status_id in self._inactive_ids:
                    logger.warning(f"Versuch, inaktiven Status zu aktualisieren: {status_id}")
                    return False
            
            # Status-Objekt erstellen
            status_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat() + 'Z'
            }
            
            # Optionale Felder hinzufügen
            if progress is not None:
                status_data["progress"] = progress
                
            if message is not None:
                status_data["message"] = message
                
            if result is not None:
                status_data["result"] = result
            
            # Status aktualisieren mit Lock
            with self._status_lock:
                self._status_data[status_id] = status_data
                
                # In Datei speichern, falls Verzeichnis konfiguriert
                if self._storage_dir:
                    self._save_to_file(status_id, status_data)
            
            # Observer benachrichtigen (außerhalb des Locks)
            self._notify_observers(status_id, status_data)
            
            return True
        except Exception as e:
            logger.error(f"Fehler bei Status-Aktualisierung: {e}")
            return False
    
    def _save_to_file(self, status_id: str, status_data: Dict[str, Any]) -> bool:
        """
        Speichert Status in Datei
        
        Args:
            status_id: Status-ID
            status_data: Status-Daten
            
        Returns:
            bool: True bei Erfolg
        """
        try:
            if not self._storage_dir:
                return False
                
            status_file = os.path.join(self._storage_dir, f"{status_id}_status.json")
            
            # Verwende file_utils für atomares Schreiben
            success = file_utils.write_json(status_file, status_data, atomic=True)
            
            # Ergebnisse separat speichern falls vorhanden (für große Objekte)
            if success and "result" in status_data and status_data["status"] == "completed":
                results_file = os.path.join(self._storage_dir, f"{status_id}_results.json")
                file_utils.write_json(results_file, status_data["result"], atomic=True)
            
            return success
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Status in Datei: {e}")
            return False
    
    def register_observer(self, status_id: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Registriert einen Observer für Status-Updates
        
        Args:
            status_id: Status-ID
            callback: Callback-Funktion für Status-Updates
            
        Returns:
            bool: True bei Erfolg
        """
        try:
            with self._status_lock:
                # Prüfe, ob Status inaktiv ist
                if status_id in self._inactive_ids:
                    logger.warning(f"Versuch, Observer für inaktiven Status zu registrieren: {status_id}")
                    return False
                    
                if status_id not in self._observers:
                    self._observers[status_id] = []
                self._observers[status_id].append(callback)
            return True
        except Exception as e:
            logger.error(f"Fehler beim Registrieren des Observers: {e}")
            return False
    
    def _notify_observers(self, status_id: str, status_data: Dict[str, Any]):
        """
        Benachrichtigt alle Observer eines Status
        
        Args:
            status_id: Status-ID
            status_data: Status-Daten
        """
        observers = []
        
        # Hole alle Observer mit Lock
        with self._status_lock:
            if status_id in self._observers:
                observers = self._observers[status_id].copy()
        
        # Benachrichtige Observer außerhalb des Locks
        for callback in observers:
            try:
                # In eigenem Thread, um Blockieren zu vermeiden
                threading.Thread(
                    target=callback,
                    args=(status_data.copy(),),
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"Fehler bei Observer-Benachrichtigung: {e}")
    
    def cleanup_status(self, status_id: str, delay_seconds: int = 0):
        """
        Bereinigt Status nach optionaler Verzögerung
        
        Args:
            status_id: Status-ID
            delay_seconds: Verzögerung in Sekunden
        """
        def _delayed_cleanup():
            if delay_seconds > 0:
                time.sleep(delay_seconds)
                
            with self._status_lock:
                # Markiere als inaktiv
                self._inactive_ids.add(status_id)
                
                # Entferne aus dem Cache
                if status_id in self._status_data:
                    del self._status_data[status_id]
                    logger.debug(f"Status-Cache bereinigt für {status_id}")
                
                # Entferne Observer
                if status_id in self._observers:
                    del self._observers[status_id]
                    logger.debug(f"Observer bereinigt für {status_id}")
                
                # Begrenze die Anzahl inaktiver IDs
                if len(self._inactive_ids) > 1000:
                    # Konvertiere zu Liste, entferne älteste 100 Einträge
                    inactive_list = list(self._inactive_ids)
                    self._inactive_ids = set(inactive_list[-900:])
        
        # In Hintergrund-Thread starten
        cleanup_thread = threading.Thread(target=_delayed_cleanup, daemon=True)
        cleanup_thread.start()
        
    def clear_inactive_ids(self):
        """Leert die Liste der inaktiven Status-IDs"""
        with self._status_lock:
            self._inactive_ids.clear()
            logger.debug("Liste der inaktiven Status-IDs geleert")
    
    def get_all_active_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Gibt alle aktiven Status zurück
        
        Returns:
            dict: Alle aktiven Status
        """
        with self._status_lock:
            return {status_id: status.copy() for status_id, status in self._status_data.items()}

# Globale Instanz für einfachen Zugriff
_status_service = StatusService()

def get_status_service() -> StatusService:
    """
    Gibt die globale StatusService-Instanz zurück
    
    Returns:
        StatusService: Globale Instanz
    """
    return _status_service

def initialize_status_service():
    """Initialisiert den globalen StatusService"""
    storage_dir = file_utils.get_status_folder()
    _status_service.set_storage_dir(storage_dir)
    logger.info(f"StatusService initialisiert mit Verzeichnis: {storage_dir}")


# Kompabilitätsfunktionen für alte Status-API
# Diese Funktionen dienen als Wrapper für die neue StatusService-API

def update_document_status(
    document_id: str, 
    status: str, 
    progress: Optional[int] = None, 
    message: Optional[str] = None, 
    result: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Aktualisiert den Dokumentenstatus über den zentralen Service
    (Kompabilitätsfunktion für altes System)
    
    Args:
        document_id: Dokument-ID
        status: Status
        progress: Fortschritt
        message: Nachricht
        result: Ergebnis
        
    Returns:
        bool: True bei Erfolg
    """
    return get_status_service().update_status(
        status_id=document_id,
        status=status,
        progress=progress,
        message=message,
        result=result
    )

def get_document_status(document_id: str) -> Dict[str, Any]:
    """
    Ruft den Dokumentenstatus ab
    (Kompabilitätsfunktion für altes System)
    
    Args:
        document_id: Dokument-ID
        
    Returns:
        dict: Status-Daten
    """
    return get_status_service().get_status(document_id)

def cleanup_status(document_id: str, delay_seconds: int = 600) -> None:
    """
    Bereinigt Status nach Verzögerung
    (Kompabilitätsfunktion für altes System)
    
    Args:
        document_id: Dokument-ID
        delay_seconds: Verzögerung in Sekunden
    """
    get_status_service().cleanup_status(document_id, delay_seconds)

def register_status_callback(document_id: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
    """
    Registriert einen Callback für Status-Updates
    (Kompabilitätsfunktion für altes System)
    
    Args:
        document_id: Dokument-ID
        callback: Callback-Funktion
        
    Returns:
        bool: True bei Erfolg
    """
    return get_status_service().register_observer(document_id, callback)