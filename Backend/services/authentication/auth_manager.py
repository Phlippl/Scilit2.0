# Backend/services/authentication/auth_manager.py
"""
Zentraler Authentication Manager mit austauschbaren Storage-Backends
"""
import os
import logging
from typing import Dict, Any, Tuple, Optional, Union

from .password_utils import hash_password, verify_password
from .user_model import User
from .storage import BaseAuthStorage, JSONAuthStorage, SQLAuthStorage

logger = logging.getLogger(__name__)

# Globale Default-Instanz für Situationen ohne App-Kontext
_default_auth_manager = None

class AuthManager:
    """
    Zentraler Authentication Manager mit austauschbaren Storage-Backends
    """
    
    def __init__(self, storage: BaseAuthStorage = None):
        """
        Initialisiert den Authentication Manager
        
        Args:
            storage: Storage-Backend für Benutzerdaten
        """
        self.storage = storage or self._get_default_storage()
        
        # Globale Instanz setzen, wenn noch keine existiert
        global _default_auth_manager
        if _default_auth_manager is None:
            _default_auth_manager = self
    
    def _get_default_storage(self) -> BaseAuthStorage:
        """
        Bestimmt das Default-Storage-Backend basierend auf Umgebungsvariablen
        """
        storage_type = os.environ.get('AUTH_STORAGE_TYPE', 'json').lower()
        
        if storage_type == 'mysql':
            try:
                return SQLAuthStorage()
            except Exception as e:
                logger.warning(f"MySQL-Storage konnte nicht initialisiert werden: {e}")
                logger.warning("Fallback auf JSON-Storage")
                return JSONAuthStorage()
        else:
            return JSONAuthStorage()
    
    def create_user(self, email: str, password: str, name: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Erstellt einen neuen Benutzer
        
        Args:
            email: E-Mail-Adresse des Benutzers
            password: Passwort des Benutzers
            name: Name des Benutzers
            
        Returns:
            tuple: (User-Objekt bei Erfolg, Fehlermeldung bei Fehler)
        """
        # Prüfe, ob Benutzer bereits existiert
        existing_user = self.get_user_by_email(email)
        if existing_user:
            return None, "Ein Benutzer mit dieser E-Mail existiert bereits"
        
        try:
            # Erstelle Benutzerverzeichnisse
            user_id = self._create_user_directories()
            
            # Erstelle Benutzer im Storage
            salt, hashed_password = hash_password(password)
            
            user = User(
                id=user_id,
                email=email,
                name=name,
                password_hash=hashed_password,
                password_salt=salt
            )
            
            success = self.storage.save_user(user)
            
            if not success:
                return None, "Fehler beim Speichern des Benutzers"
            
            # Erstelle Vektorsammlungen für den Benutzer
            self._create_vector_collections(user_id)
            
            return user, None
        
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Benutzers: {e}")
            return None, f"Fehler beim Erstellen des Benutzers: {str(e)}"
    
    def _create_user_directories(self) -> str:
        """
        Erstellt Benutzerverzeichnisse und gibt eine neue User-ID zurück
        
        Returns:
            str: Neue User-ID
        """
        import uuid
        import os
        
        user_id = str(uuid.uuid4())
        upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
        user_folder = os.path.join(upload_folder, user_id)
        
        os.makedirs(user_folder, exist_ok=True)
        
        return user_id
    
    def _create_vector_collections(self, user_id: str) -> None:
        """
        Erstellt Vektorsammlungen für einen Benutzer
        
        Args:
            user_id: ID des Benutzers
        """
        try:
            from services.vector_db import get_or_create_collection
            get_or_create_collection(f"user_{user_id}_documents")
        except Exception as e:
            logger.warning(f"Fehler beim Erstellen der Vektorsammlungen: {e}")
    
    def authenticate_user(self, email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Authentifiziert einen Benutzer
        
        Args:
            email: E-Mail-Adresse des Benutzers
            password: Passwort des Benutzers
            
        Returns:
            tuple: (User-Objekt bei Erfolg, Fehlermeldung bei Fehler)
        """
        user = self.storage.get_user_by_email(email)
        
        if not user:
            return None, "Ungültige E-Mail oder Passwort"
        
        try:
            # Verifiziere Passwort
            salt = user.password_salt
            password_valid = verify_password(password, salt, user.password_hash)
            
            if not password_valid:
                return None, "Ungültige E-Mail oder Passwort"
            
            # Aktualisiere last_login
            user.last_login = self.storage.update_last_login(user.id)
            
            return user, None
            
        except Exception as e:
            logger.error(f"Fehler bei der Authentifizierung: {e}")
            return None, f"Authentifizierung fehlgeschlagen: {str(e)}"
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Holt einen Benutzer anhand seiner E-Mail-Adresse
        
        Args:
            email: E-Mail-Adresse des Benutzers
            
        Returns:
            User: User-Objekt oder None wenn nicht gefunden
        """
        return self.storage.get_user_by_email(email)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Holt einen Benutzer anhand seiner ID
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            User: User-Objekt oder None wenn nicht gefunden
        """
        return self.storage.get_user_by_id(user_id)
    
    def update_user(self, email: str, updates: Dict[str, Any]) -> Tuple[Optional[User], Optional[str]]:
        """
        Aktualisiert Benutzerinformationen
        
        Args:
            email: E-Mail-Adresse des Benutzers
            updates: Zu aktualisierende Felder
            
        Returns:
            tuple: (User-Objekt bei Erfolg, Fehlermeldung bei Fehler)
        """
        return self.storage.update_user(email, updates)
    
    def change_password(self, email: str, current_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Ändert das Passwort eines Benutzers
        
        Args:
            email: E-Mail-Adresse des Benutzers
            current_password: Aktuelles Passwort
            new_password: Neues Passwort
            
        Returns:
            tuple: (Erfolg, Fehlermeldung bei Fehler)
        """
        # Verifiziere aktuelles Passwort
        user, error = self.authenticate_user(email, current_password)
        
        if not user:
            return False, error
        
        try:
            # Generiere neuen Passwort-Hash
            salt, hashed_password = hash_password(new_password)
            
            # Aktualisiere Passwort im Storage
            success = self.storage.update_password(
                user_id=user.id, 
                password_hash=hashed_password,
                password_salt=salt
            )
            
            if not success:
                return False, "Fehler beim Aktualisieren des Passworts"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Fehler beim Ändern des Passworts: {e}")
            return False, f"Passwortänderung fehlgeschlagen: {str(e)}"
    
    def delete_user(self, email: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        Löscht einen Benutzer
        
        Args:
            email: E-Mail-Adresse des Benutzers
            password: Passwort zur Bestätigung
            
        Returns:
            tuple: (Erfolg, Fehlermeldung bei Fehler)
        """
        # Verifiziere Passwort
        user, error = self.authenticate_user(email, password)
        
        if not user:
            return False, error
        
        try:
            # Lösche Benutzer aus Storage
            success = self.storage.delete_user(user.id)
            
            if not success:
                return False, "Fehler beim Löschen des Benutzers"
            
            # Lösche Benutzerverzeichnisse
            self._delete_user_directories(user.id)
            
            # Lösche Vektorsammlungen
            self._delete_vector_collections(user.id)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Benutzers: {e}")
            return False, f"Benutzer konnte nicht gelöscht werden: {str(e)}"
    
    def _delete_user_directories(self, user_id: str) -> None:
        """
        Löscht Benutzerverzeichnisse
        
        Args:
            user_id: ID des Benutzers
        """
        import shutil
        import os
        
        upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
        user_folder = os.path.join(upload_folder, user_id)
        
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
    
    def _delete_vector_collections(self, user_id: str) -> None:
        """
        Löscht Vektorsammlungen eines Benutzers
        
        Args:
            user_id: ID des Benutzers
        """
        try:
            from services.vector_db import client
            collection_name = f"user_{user_id}_documents"
            
            if client.get_collection(collection_name):
                client.delete_collection(collection_name)
        except Exception as e:
            logger.warning(f"Fehler beim Löschen der Vektorsammlungen: {e}")