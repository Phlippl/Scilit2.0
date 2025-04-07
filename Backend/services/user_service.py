import os
import hashlib
import uuid
import json
import logging
from datetime import datetime
import mysql.connector
from mysql.connector import pooling

logger = logging.getLogger(__name__)

class UserService:
    """Service für Benutzerverwaltung mit MySQL"""
    
    def __init__(self):
        # Datenbankverbindungsdaten
        self.db_config = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASSWORD', ''),
            'database': os.environ.get('MYSQL_DATABASE', 'scilit2'),
            'port': int(os.environ.get('MYSQL_PORT', 3306))
        }
        
        # Verbindungspool erstellen
        self.pool = self._create_pool()
        
        # Datenbank initialisieren
        self._init_db()
    
    def _create_pool(self):
        """Datenbankverbindungspool erstellen"""
        try:
            return pooling.MySQLConnectionPool(
                pool_name="scilit2_pool",
                pool_size=5,
                **self.db_config
            )
        except mysql.connector.Error as err:
            logger.error(f"Fehler beim Erstellen des Verbindungspools: {err}")
            raise
    
    def _get_connection(self):
        """Verbindung aus dem Pool holen"""
        return self.pool.get_connection()
    
    def _init_db(self):
        """Datenbank initialisieren und Tabellen erstellen"""
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
                updated_at DATETIME NOT NULL
            )
            ''')
            
            # Dokumententabelle erstellen
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                title VARCHAR(255) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                file_size INT NOT NULL,
                upload_date DATETIME NOT NULL,
                processing_status VARCHAR(50) DEFAULT 'pending',
                metadata JSON,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            ''')
            
            connection.commit()
            logger.info("Datenbanktabellen erfolgreich initialisiert")
            
        except Exception as e:
            logger.error(f"Fehler bei der Initialisierung der Datenbank: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def _hash_password(self, password, salt=None):
        """Passwort hashen mit Salt"""
        if salt is None:
            salt = os.urandom(32)  # Salt generieren
        
        # PBKDF2 mit SHA-256 für Passwort-Hashing
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000  # Anzahl der Iterationen
        )
        
        return salt.hex(), key.hex()
    
    def create_user(self, email, password, name):
        """Neuen Benutzer erstellen"""
        connection = None
        cursor = None
        try:
            # Prüfen, ob Benutzer bereits existiert
            if self.get_user_by_email(email):
                return None, "Benutzer mit dieser E-Mail existiert bereits"
            
            # Benutzer-ID generieren
            user_id = str(uuid.uuid4())
            
            # Passwort hashen
            salt_hex, password_hash = self._hash_password(password)
            
            connection = self._get_connection()
            cursor = connection.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Benutzer in die Datenbank einfügen
            cursor.execute('''
            INSERT INTO users (id, email, password_hash, salt, name, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, email, password_hash, salt_hex, name, now, now))
            
            connection.commit()
            
            # Benutzerverzeichnis erstellen
            upload_folder = os.environ.get('UPLOAD_FOLDER', './uploads')
            user_folder = os.path.join(upload_folder, user_id)
            os.makedirs(user_folder, exist_ok=True)
            
            # Vektorsammlungen erstellen
            from services.vector_db import get_or_create_collection
            get_or_create_collection(f"user_{user_id}_documents")
            
            return {
                'id': user_id,
                'email': email,
                'name': name,
                'created_at': now
            }, None
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Benutzers: {str(e)}")
            if connection:
                connection.rollback()
            return None, f"Fehler beim Erstellen des Benutzers: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def authenticate_user(self, email, password):
        """Benutzer authentifizieren"""
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Benutzer aus der Datenbank abrufen
            cursor.execute('''
            SELECT id, email, password_hash, salt, name, created_at, updated_at
            FROM users WHERE email = %s
            ''', (email,))
            
            user = cursor.fetchone()
            
            if not user:
                return None, "Ungültige E-Mail oder Passwort"
            
            # Passwort verifizieren
            salt = bytes.fromhex(user['salt'])
            _, password_hash = self._hash_password(password, salt)
            
            if password_hash != user['password_hash']:
                return None, "Ungültige E-Mail oder Passwort"
            
            # Benutzerinformationen zurückgeben (ohne Passwort-Hash)
            return {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'created_at': user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            }, None
            
        except Exception as e:
            logger.error(f"Fehler bei der Authentifizierung: {str(e)}")
            return None, f"Authentifizierung fehlgeschlagen: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def get_user_by_email(self, email):
        """Benutzer über E-Mail abrufen"""
        connection = None
        cursor = None
        try:
            connection = self._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute('''
            SELECT id, email, name, created_at, updated_at
            FROM users WHERE email = %s
            ''', (email,))
            
            user = cursor.fetchone()
            
            if user and 'created_at' in user:
                user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                
            if user and 'updated_at' in user:
                user['updated_at'] = user['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
                
            return user
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Benutzers: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()