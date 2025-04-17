# Backend/config/config_manager.py
"""
Zentrales Konfigurationsmanagement für die gesamte Anwendung.
Enthält alle Umgebungsvariablen und Konfigurationseinstellungen.
"""
import os
import logging
import secrets
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Konfigurationswerte (werden einmalig beim Import initialisiert)
_config = {}
_initialized = False

def initialize():
    """Initialisiert die Konfiguration"""
    global _config, _initialized
    
    if _initialized:
        return _config
    
    # Lade .env-Datei
    load_dotenv()
    
    # Basis-Konfiguration
    _config = {
        # Pfade und Dateien
        'UPLOAD_FOLDER': os.environ.get('UPLOAD_FOLDER', './uploads'),
        'CHROMA_PERSIST_DIR': os.environ.get('CHROMA_PERSIST_DIR', './data/chroma'),
        'ALLOWED_EXTENSIONS': {'pdf'},
        
        # Limits
        'MAX_CONTENT_LENGTH': int(os.environ.get('MAX_CONTENT_LENGTH', 20 * 1024 * 1024)),
        
        # Sicherheit
        'SECRET_KEY': os.environ.get('SECRET_KEY', secrets.token_hex(32)),
        
        # Datenbank
        'DB_CONFIG': {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASSWORD', ''),
            'database': os.environ.get('MYSQL_DATABASE', 'scilit2'),
            'port': int(os.environ.get('MYSQL_PORT', 3306)),
        },
        
        # Embeddings
        'EMBEDDING_FUNCTION': os.environ.get('EMBEDDING_FUNCTION', 'ollama'),
        'OLLAMA_API_URL': os.environ.get('OLLAMA_API_URL', 'http://localhost:11434'),
        'OLLAMA_MODEL': os.environ.get('OLLAMA_MODEL', 'llama3'),
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY', ''),
        
        # LLM Integration
        'LLM_API_URL': os.environ.get('LLM_API_URL', 'https://api.openai.com/v1/chat/completions'),
        'LLM_API_KEY': os.environ.get('LLM_API_KEY', ''),
        'LLM_MODEL': os.environ.get('LLM_MODEL', 'gpt-3.5-turbo'),
        'LLM_TIMEOUT': int(os.environ.get('LLM_TIMEOUT', 60)),
        
        # Server
        'HOST': os.environ.get('HOST', '0.0.0.0'),
        'PORT': int(os.environ.get('PORT', 5000)),
        'DEBUG': os.environ.get('DEBUG', 'True').lower() == 'true',
        
        # Testen und Entwicklung
        'TEST_USER_ENABLED': os.environ.get('VITE_TEST_USER_ENABLED', 'false').lower() == 'true',
        'TEST_USER_ID': os.environ.get('TEST_USER_ID', 'test-user-id'),
        'TEST_USER_EMAIL': os.environ.get('VITE_TEST_USER_EMAIL', 'user@example.com'),
        'TEST_USER_PASSWORD': os.environ.get('VITE_TEST_USER_PASSWORD', 'password123'),
        'TEST_USER_NAME': os.environ.get('VITE_TEST_USER_NAME', 'Test User'),
        
        # Authentifizierung
        'AUTH_STORAGE_TYPE': os.environ.get('AUTH_STORAGE_TYPE', 'json').lower(),
    }
    
    _initialized = True
    logger.info("Konfiguration initialisiert")
    
    return _config

def get(key, default=None):
    """
    Holt einen Konfigurationswert
    
    Args:
        key: Schlüssel des Konfigurationswerts
        default: Standardwert, falls Schlüssel nicht existiert
        
    Returns:
        Konfigurationswert
    """
    global _config, _initialized
    
    if not _initialized:
        initialize()
    
    return _config.get(key, default)

def get_db_config():
    """
    Holt die Datenbankkonfiguration
    
    Returns:
        dict: Datenbankkonfiguration
    """
    return get('DB_CONFIG')

def update(key, value):
    """
    Aktualisiert einen Konfigurationswert zur Laufzeit
    
    Args:
        key: Schlüssel des Konfigurationswerts
        value: Neuer Wert
    """
    global _config, _initialized
    
    if not _initialized:
        initialize()
    
    _config[key] = value
    logger.debug(f"Konfiguration aktualisiert: {key}")

# Initialisiere Konfiguration beim Import
initialize()