# Backend/utils/auth_middleware.py
"""
Authentifizierungs-Middleware für Flask zur Reduzierung von Code-Duplikation über Endpunkte.
Verbesserte Version mit zentralisierter Konfiguration und Fehlerbehandlung.
"""
import os
import jwt
from functools import wraps
from flask import request, jsonify, current_app, g
import logging
from typing import Optional, Callable, Dict, Any, Union

from utils.error_handler import unauthorized, APIError
from config import config_manager

logger = logging.getLogger(__name__)

def get_token_from_header() -> Optional[str]:
    """
    Extrahiert JWT-Token aus Authorization-Header
    
    Returns:
        str: Token oder None, wenn kein gültiger Header gefunden wurde
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    
    # Validiere Token-Format
    if not token or token.count('.') != 2:
        logger.warning("Ungültiges Token-Format erhalten")
        return None
    
    return token

def get_user_id() -> str:
    """
    Holt Benutzer-ID aus JWT-Token oder X-User-ID-Header mit Test-Benutzer-Unterstützung
    
    Returns:
        str: Benutzer-ID oder 'default_user', wenn nicht authentifiziert
    """
    user_id = 'default_user'
    
    # Prüfe, ob bereits in g gesetzt
    if hasattr(g, 'user_id'):
        return g.user_id
    
    # Aus Authorization-Header holen
    token = get_token_from_header()
    if token:
        try:
            # Hole Secret-Key aus Konfiguration
            secret_key = config_manager.get('SECRET_KEY')
            if not secret_key:
                logger.warning("SECRET_KEY nicht konfiguriert")
                return user_id
                
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload.get('sub', user_id)
            
            # Speichere in g für spätere Verwendung
            g.user_id = user_id
            g.user_email = payload.get('email')
            g.user_name = payload.get('name')
            
            logger.debug(f"Benutzer aus Token erkannt: {user_id}")
        except jwt.ExpiredSignatureError:
            logger.warning("Token abgelaufen")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Ungültiges Token: {e}")
        except Exception as e:
            logger.error(f"Fehler beim Decodieren des Tokens: {e}")
    
    # Fallback auf X-User-ID-Header
    header_user_id = request.headers.get('X-User-ID')
    if header_user_id:
        user_id = header_user_id
        logger.debug(f"Benutzer aus X-User-ID-Header: {user_id}")
    
    # Test-Modus-Behandlung
    test_user_enabled = config_manager.get('TEST_USER_ENABLED', False)
    if test_user_enabled and (user_id == 'default_user'):
        test_user_id = config_manager.get('TEST_USER_ID', 'test-user-id')
        logger.info(f"Verwende Test-Benutzer-ID: {test_user_id}")
        user_id = test_user_id
    
    # Speichere in g für spätere Verwendung
    g.user_id = user_id
    
    return user_id

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verifiziert ein JWT-Token
    
    Args:
        token: JWT-Token
        
    Returns:
        dict: Token-Payload
        
    Raises:
        jwt.ExpiredSignatureError: Wenn Token abgelaufen ist
        jwt.InvalidTokenError: Wenn Token ungültig ist
    """
    secret_key = config_manager.get('SECRET_KEY')
    if not secret_key:
        raise APIError("Serverkonfigurationsfehler", 500)
    
    return jwt.decode(token, secret_key, algorithms=['HS256'])

def verify_token_with_options(token: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Verifiziert ein JWT-Token mit optionalen Optionen
    
    Args:
        token: JWT-Token
        options: Zusätzliche Optionen für jwt.decode
        
    Returns:
        dict: Token-Payload
        
    Raises:
        jwt.ExpiredSignatureError: Wenn Token abgelaufen ist
        jwt.InvalidTokenError: Wenn Token ungültig ist
        APIError: Bei Konfigurationsfehlern
    """
    secret_key = config_manager.get('SECRET_KEY')
    if not secret_key:
        raise APIError("Serverkonfigurationsfehler", 500)
    
    decode_options = {}
    if options:
        decode_options.update(options)
    
    return jwt.decode(token, secret_key, algorithms=['HS256'], options=decode_options)

def requires_auth(f: Callable) -> Callable:
    """
    Dekorator für Endpunkte, die Authentifizierung erfordern
    Speichert g.user_id für Verwendung im dekorierten Endpunkt
    Gibt 401 zurück, wenn keine gültige Authentifizierung vorhanden ist
    
    Args:
        f: Zu dekorierende Funktion
        
    Returns:
        Dekorierte Funktion
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        
        if not token:
            # Spezifische Fehlermeldung für fehlende Authentifizierung
            return jsonify({"error": "Authentifizierung erforderlich"}), 401
        
        try:
            # Token decodieren
            payload = verify_token(token)
            
            # Benutzer-ID in Flask's g-Objekt speichern
            g.user_id = payload.get('sub')
            g.user_email = payload.get('email')
            g.user_name = payload.get('name')
            
            # Originale Funktion aufrufen
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token abgelaufen"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Ungültiges Token: {str(e)}"}), 401
        except Exception as e:
            logger.error(f"Authentifizierungsfehler: {e}")
            return jsonify({"error": "Authentifizierung fehlgeschlagen"}), 401
    
    return decorated

def optional_auth(f: Callable) -> Callable:
    """
    Dekorator für Endpunkte, die mit oder ohne Authentifizierung funktionieren
    Setzt g.user_id auf die erkannte ID oder 'default_user'
    Gibt niemals 401 zurück
    
    Args:
        f: Zu dekorierende Funktion
        
    Returns:
        Dekorierte Funktion
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Benutzer-ID setzen und in g speichern
        g.user_id = get_user_id()
        
        # Originale Funktion aufrufen
        return f(*args, **kwargs)
    
    return decorated

def is_admin(f: Callable) -> Callable:
    """
    Dekorator für Admin-Privilegien
    Muss mit requires_auth verwendet werden
    
    Args:
        f: Zu dekorierende Funktion
        
    Returns:
        Dekorierte Funktion
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Dieser Dekorator geht davon aus, dass requires_auth bereits angewendet wurde
        # und g.user_id gesetzt ist
        
        # Admin-Benutzer aus Konfiguration holen
        admin_users = config_manager.get('ADMIN_USERS', '').split(',')
        
        if not hasattr(g, 'user_id') or g.user_id not in admin_users:
            return jsonify({"error": "Admin-Privilegien erforderlich"}), 403
        
        return f(*args, **kwargs)
    
    return decorated

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Holt Informationen zum aktuellen Benutzer aus dem Token
    
    Returns:
        dict: Benutzerinformationen oder None
    """
    token = get_token_from_header()
    if not token:
        return None
    
    try:
        payload = verify_token(token)
        return {
            'id': payload.get('sub'),
            'email': payload.get('email'),
            'name': payload.get('name')
        }
    except Exception:
        return None