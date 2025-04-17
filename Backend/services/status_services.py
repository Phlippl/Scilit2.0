# Backend/services/status_service.py
import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class StatusService:
    """Zentraler Service für Statusverwaltung mit Observer-Pattern"""
    
    def __init__(self, storage_dir: str = None):
        self._status_data = {}  # In-Memory-Status
        self._status_lock = threading.Lock()
        self._observers = {}  # Callbacks nach Status-ID
        self._storage_dir = storage_dir
    
    def set_storage_dir(self, storage_dir: str):
        """Setzt das Verzeichnis für Statusdateien"""
        self._storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def get_status(self, status_id: str) -> Dict[str, Any]:
        """Gibt den aktuellen Status zurück"""
        with self._status_lock:
            # Zuerst im Memory-Cache nachsehen
            if status_id in self._status_data:
                return self._status_data[status_id].copy()
            
            # Falls nicht im Cache, aus Datei laden
            if self._storage_dir:
                status_file = os.path.join(self._storage_dir, f"{status_id}_status.json")
                if os.path.exists(status_file):
                    try:
                        with open(status_file, 'r') as f:
                            status_data = json.load(f)
                            # In Cache laden
                            self._status_data[status_id] = status_data
                            return status_data.copy()
                    except Exception as e:
                        logger.error(f"Error loading status from file: {e}")
        
        # Standardstatus, wenn nichts gefunden wurde
        return {
            "status": "unknown",
            "message": "Status not found",
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
        """Aktualisiert den Status und benachrichtigt Observer"""
        try:
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
            logger.error(f"Error updating status: {e}")
            return False
    
    def _save_to_file(self, status_id: str, status_data: Dict[str, Any]) -> bool:
        """Speichert Status in Datei"""
        try:
            if not self._storage_dir:
                return False
                
            status_file = os.path.join(self._storage_dir, f"{status_id}_status.json")
            
            # Temporäre Datei für atomares Schreiben
            temp_file = f"{status_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(status_data, f, indent=2, default=str)
            
            # Atomares Ersetzen
            os.replace(temp_file, status_file)
            
            # Ergebnisse separat speichern falls vorhanden (für große Objekte)
            if "result" in status_data and status_data["status"] == "completed":
                results_file = os.path.join(self._storage_dir, f"{status_id}_results.json")
                with open(results_file, 'w') as f:
                    json.dump(status_data["result"], f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Error saving status to file: {e}")
            return False
    
    def register_observer(self, status_id: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Registriert einen Observer für Status-Updates"""
        try:
            with self._status_lock:
                if status_id not in self._observers:
                    self._observers[status_id] = []
                self._observers[status_id].append(callback)
            return True
        except Exception as e:
            logger.error(f"Error registering observer: {e}")
            return False
    
    def _notify_observers(self, status_id: str, status_data: Dict[str, Any]):
        """Benachrichtigt alle Observer eines Status"""
        if status_id in self._observers:
            for callback in self._observers[status_id]:
                try:
                    # In eigenem Thread, um Blockieren zu vermeiden
                    threading.Thread(
                        target=callback,
                        args=(status_data.copy(),),
                        daemon=True
                    ).start()
                except Exception as e:
                    logger.error(f"Error notifying observer: {e}")
    
    def cleanup_status(self, status_id: str, delay_seconds: int = 0):
        """Bereinigt Status nach optionaler Verzögerung"""
        def _delayed_cleanup():
            if delay_seconds > 0:
                time.sleep(delay_seconds)
                
            with self._status_lock:
                if status_id in self._status_data:
                    del self._status_data[status_id]
                    logger.debug(f"Cleaned up status for {status_id}")
                
                if status_id in self._observers:
                    del self._observers[status_id]
                    logger.debug(f"Cleaned up observers for {status_id}")
        
        # In Hintergrund-Thread starten
        cleanup_thread = threading.Thread(target=_delayed_cleanup, daemon=True)
        cleanup_thread.start()

# Globale Instanz für einfachen Zugriff
_status_service = StatusService()

def get_status_service() -> StatusService:
    """Gibt die globale StatusService-Instanz zurück"""
    return _status_service