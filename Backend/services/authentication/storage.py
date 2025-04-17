# Backend/services/authentication/storage.py
"""
Storage-Backends für die Authentifizierung
"""
import os
import json
import logging
import mysql.connector
from datetime import datetime
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from .user_model import User

logger = logging.getLogger(__name__)

class BaseAuthStorage(ABC):
    """
    Basis-Klasse für Auth-Storage-Backends
    """
    
    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Holt einen Benutzer anhand seiner E-Mail-Adresse"""
        pass
    
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Holt einen Benutzer anhand seiner ID"""
        pass
    
    @abstractmethod
    def save_user(self, user: User) -> bool:
        """Speichert einen Benutzer"""
        pass
    
    @abstractmethod
    def update_user(self, email: str, updates: Dict[str, Any]) -> bool:
        """Aktualisiert Benutzerinformationen"""
        pass
    
    @abstractmethod
    def update_password(self, user_id: str, password_hash: str, password_salt: bytes) -> bool:
        """Aktualisiert das Passwort eines Benutzers"""
        pass
    
    @abstractmethod
    def update_last_login(self, user_id: str) -> datetime:
        """Aktualisiert den letzten Login eines Benutzers"""
        pass
    
    @abstractmethod
    def delete_user(self, user_id: str) -> bool:
        """Löscht einen Benutzer"""
        pass


class JSONAuthStorage(BaseAuthStorage):
    """
    JSON-basiertes Storage-Backend für Authentifizierung
    """
    
    def __init__(self):
        """
        Initialisiert das JSON-Storage-Backend
        """
        self.data_dir = os.environ.get('DATA_DIR', './data')
        self.users_file = os.path.join(self.data_dir, 'users.json')
        
        # Stelle sicher, dass das Datenverzeichnis existiert
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Lade Benutzer aus Datei
        self.users = self._load_users()
    
    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Lädt Benutzer aus JSON-Datei
        
        Returns:
            dict: Dictionary mit Benutzerdaten (email -> user_data)
        """
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    
                    # Konvertiere zu email-indexiertem Dictionary für schnellere Lookups
                    users = {}
                    for user_id, user_data in users_data.items():
                        if 'email' in user_data:
                            users[user_data['email']] = user_data
                    
                    logger.info(f"Loaded {len(users)} users from storage")
                    return users
            else:
                logger.info("No users file found, starting with empty user database")
                return {}
        except Exception as e:
            logger.error(f"Error loading users data: {str(e)}")
            return {}
    
    def _save_users(self) -> bool:
        """
        Speichert Benutzer in JSON-Datei
        
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        try:
            # Konvertiere zu ID-indexiertem Format für Speicherung
            users_to_save = {}
            for user_data in self.users.values():
                if 'id' in user_data:
                    users_to_save[user_data['id']] = user_data
            
            # Erstelle temporäre Datei für sichereres Schreiben
            temp_file = f"{self.users_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(users_to_save, f, indent=2, default=str)
            
            # Benenne zu eigentlicher Datei um (atomare Operation)
            os.replace(temp_file, self.users_file)
            
            logger.info(f"Saved {len(users_to_save)} users to storage")
            return True
        except Exception as e:
            logger.error(f"Error saving users data: {str(e)}")
            return False
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Holt einen Benutzer anhand seiner E-Mail-Adresse
        
        Args:
            email: E-Mail-Adresse des Benutzers
            
        Returns:
            User: User-Objekt oder None wenn nicht gefunden
        """
        user_data = self.users.get(email)
        
        if not user_data:
            return None
        
        return User.from_dict(user_data)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Holt einen Benutzer anhand seiner ID
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            User: User-Objekt oder None wenn nicht gefunden
        """
        for user_data in self.users.values():
            if user_data.get('id') == user_id:
                return User.from_dict(user_data)
        
        return None
    
    def save_user(self, user: User) -> bool:
        """
        Speichert einen Benutzer
        
        Args:
            user: Zu speichernder Benutzer
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        try:
            user_dict = user.to_dict(include_sensitive=True)
            self.users[user.email] = user_dict
            return self._save_users()
        except Exception as e:
            logger.error(f"Error saving user: {str(e)}")
            return False
    
    def update_user(self, email: str, updates: Dict[str, Any]) -> bool:
        """
        Aktualisiert Benutzerinformationen
        
        Args:
            email: E-Mail-Adresse des Benutzers
            updates: Zu aktualisierende Felder
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        if email not in self.users:
            return False
        
        try:
            user = self.users[email]
            
            # Aktualisiere Felder
            allowed_fields = ['name', 'email']
            for field, value in updates.items():
                if field in allowed_fields:
                    user[field] = value
            
            # Aktualisiere Zeitstempel
            user['updated_at'] = datetime.utcnow()
            
            # Speichere Änderungen
            self.users[email] = user
            return self._save_users()
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False
    
    def update_password(self, user_id: str, password_hash: str, password_salt: bytes) -> bool:
        """
        Aktualisiert das Passwort eines Benutzers
        
        Args:
            user_id: ID des Benutzers
            password_hash: Neuer Passwort-Hash
            password_salt: Neues Passwort-Salt
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        try:
            # Finde Benutzer anhand der ID
            user_email = None
            for email, user in self.users.items():
                if user.get('id') == user_id:
                    user_email = email
                    break
            
            if not user_email:
                return False
            
            # Aktualisiere Passwort
            user = self.users[user_email]
            user['password_hash'] = password_hash
            user['password_salt'] = password_salt.hex()
            user['updated_at'] = datetime.utcnow()
            
            # Speichere Änderungen
            self.users[user_email] = user
            return self._save_users()
        except Exception as e:
            logger.error(f"Error updating password: {str(e)}")
            return False
    
    def update_last_login(self, user_id: str) -> datetime:
        """
        Aktualisiert den letzten Login eines Benutzers
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            datetime: Zeitstempel des letzten Logins
        """
        now = datetime.utcnow()
        
        try:
            # Finde Benutzer anhand der ID
            user_email = None
            for email, user in self.users.items():
                if user.get('id') == user_id:
                    user_email = email
                    break
            
            if user_email:
                user = self.users[user_email]
                user['last_login'] = now
                
                # Speichere Änderungen
                self.users[user_email] = user
                self._save_users()
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")
        
        return now
    
    def delete_user(self, user_id: str) -> bool:
        """
        Löscht einen Benutzer
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        try:
            # Finde Benutzer anhand der ID
            user_email = None
            for email, user in self.users.items():
                if user.get('id') == user_id:
                    user_email = email
                    break
            
            if not user_email:
                return False
            
            # Lösche Benutzer
            del self.users[user_email]
            return self._save_users()
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False


class SQLAuthStorage(BaseAuthStorage):
    """
    SQL-basiertes Storage-Backend für Authentifizierung
    """
    
    def __init__(self):
        """
        Initialisiert das SQL-Storage-Backend
        """
        # Datenbankverbindungsdaten
        self.db_config = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASSWORD', ''),
            'database': os.environ.get('MYSQL_DATABASE', 'scilit2'),
            'port': int(os.environ.get('MYSQL_PORT', 3306))
        }
        
        # Verbindungspool erstellen
        try:
            import mysql.connector.pooling
            self.pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="scilit2_pool",
                pool_size=5,
                **self.db_config
            )
            logger.info("MySQL connection pool created")
        except Exception as e:
            logger.error(f"Error creating MySQL connection pool: {str(e)}")
            raise
        
        # Datenbank initialisieren
        self._init_db()
    
    def _get_connection(self):
        """
        Holt eine Verbindung aus dem Pool
        
        Returns:
            MySQLConnection: Datenbankverbindung
        """
        return self.pool.get_connection()
    
    def _init_db(self) -> None:
        """
        Initialisiert die Datenbank und erstellt benötigte Tabellen
        """
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Benutzertabelle erstellen
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                last_login DATETIME NULL
            )
            ''')
            
            connection.commit()
            logger.info("Database tables initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Holt einen Benutzer anhand seiner E-Mail-Adresse
        
        Args:
            email: E-Mail-Adresse des Benutzers
            
        Returns:
            User: User-Objekt oder None wenn nicht gefunden
        """
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute('''
            SELECT id, email, password_hash, salt as password_salt, name, created_at, updated_at, last_login
            FROM users WHERE email = %s
            ''', (email,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
            
            # Konvertiere binary salt zu hex string
            if 'password_salt' in user_data and user_data['password_salt']:
                user_data['password_salt'] = user_data['password_salt']
            
            return User.from_dict(user_data)
            
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Holt einen Benutzer anhand seiner ID
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            User: User-Objekt oder None wenn nicht gefunden
        """
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute('''
            SELECT id, email, password_hash, salt as password_salt, name, created_at, updated_at, last_login
            FROM users WHERE id = %s
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
            
            # Konvertiere binary salt zu hex string
            if 'password_salt' in user_data and user_data['password_salt']:
                user_data['password_salt'] = user_data['password_salt']
            
            return User.from_dict(user_data)
            
        except Exception as e:
            logger.error(f"Error getting user by id: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def save_user(self, user: User) -> bool:
        """
        Speichert einen neuen Benutzer
        
        Args:
            user: Zu speichernder Benutzer
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        connection = None
        cursor = None
        try:
            # Prüfe, ob Benutzer bereits existiert
            existing_user = self.get_user_by_email(user.email)
            if existing_user:
                return False
            
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Konvertiere datetime zu string
            created_at = user.created_at.strftime('%Y-%m-%d %H:%M:%S')
            updated_at = user.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            
            # Konvertiere salt zu hex für Speicherung
            salt_hex = user.password_salt if isinstance(user.password_salt, str) else user.password_salt.hex()
            
            # Füge Benutzer in die Datenbank ein
            cursor.execute('''
            INSERT INTO users (id, email, password_hash, salt, name, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user.id, user.email, user.password_hash, salt_hex, user.name, created_at, updated_at))
            
            connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving user: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def update_user(self, email: str, updates: Dict[str, Any]) -> bool:
        """
        Aktualisiert Benutzerinformationen
        
        Args:
            email: E-Mail-Adresse des Benutzers
            updates: Zu aktualisierende Felder
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        connection = None
        cursor = None
        try:
            # Hole Benutzer
            user = self.get_user_by_email(email)
            if not user:
                return False
            
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Aktualisiere Felder
            allowed_fields = ['name', 'email']
            for field, value in updates.items():
                if field not in allowed_fields:
                    continue
                
                # Aktualisiere in der Datenbank
                cursor.execute(f'''
                UPDATE users SET {field} = %s, updated_at = %s
                WHERE email = %s
                ''', (value, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), email))
            
            connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def update_password(self, user_id: str, password_hash: str, password_salt: bytes) -> bool:
        """
        Aktualisiert das Passwort eines Benutzers
        
        Args:
            user_id: ID des Benutzers
            password_hash: Neuer Passwort-Hash
            password_salt: Neues Passwort-Salt
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Konvertiere salt zu hex für Speicherung
            salt_hex = password_salt.hex() if isinstance(password_salt, bytes) else password_salt
            
            # Aktualisiere Passwort
            cursor.execute('''
            UPDATE users SET password_hash = %s, salt = %s, updated_at = %s
            WHERE id = %s
            ''', (password_hash, salt_hex, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), user_id))
            
            connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error updating password: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def update_last_login(self, user_id: str) -> datetime:
        """
        Aktualisiert den letzten Login eines Benutzers
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            datetime: Zeitstempel des letzten Logins
        """
        connection = None
        cursor = None
        now = datetime.utcnow()
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Aktualisiere letzten Login
            cursor.execute('''
            UPDATE users SET last_login = %s
            WHERE id = %s
            ''', (now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            
            connection.commit()
            
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")
            if connection:
                connection.rollback()
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        
        return now
    
    def delete_user(self, user_id: str) -> bool:
        """
        Löscht einen Benutzer
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            bool: True bei Erfolg, False bei Fehler
        """
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Lösche Benutzer
            cursor.execute('''
            DELETE FROM users WHERE id = %s
            ''', (user_id,))
            
            connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            if connection:
                connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()