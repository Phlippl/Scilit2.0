# Backend/utils/error_handler.py
"""
Zentralisierte Fehlerbehandlung für Flask-Anwendungen mit standardisierten Fehlermeldungen.
Verbesserte Version mit Handling für HTTP-Streams und Artefakten.
"""
import logging
import traceback
import sys
import uuid
from flask import jsonify, Blueprint, current_app, g, request, Response
from werkzeug.exceptions import HTTPException
import requests
from typing import Dict, Any, List, Optional, Union, Callable, Tuple

# Import timeout_handler from performance_utils (instead of helpers) if needed
from utils.performance_utils import timeout_handler

# Logging konfigurieren
logger = logging.getLogger(__name__)

class APIError(Exception):
    """
    Benutzerdefinierte API-Ausnahmen mit Statuscode und optionalen Details
    """
    def __init__(self, message: str, status_code: int = 400, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Fehler in ein Dictionary für JSON-Antworten"""
        error_dict = {
            'error': self.message
        }
        
        # Details hinzufügen, falls vorhanden
        if self.details:
            error_dict['details'] = self.details
            
        # Request-ID hinzufügen, falls vorhanden
        if hasattr(g, 'request_id'):
            error_dict['request_id'] = g.request_id
            
        return error_dict

def configure_error_handlers(app):
    """
    Konfiguriert globale Fehlerbehandlung für die Flask-Anwendung
    
    Args:
        app: Flask-Anwendungsinstanz
    """
    # HTTP-Header für CORS in Fehlerantworten hinzufügen
    @app.after_request
    def add_cors_headers(response):
        """Fügt CORS-Header zu Antworten hinzu"""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        return response
    
    # Generiere Request-ID für jede Anfrage
    @app.before_request
    def add_request_id():
        """Fügt Request-ID zu jeder Anfrage hinzu"""
        g.request_id = str(uuid.uuid4())
    
    # APIError-Handler
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = error.to_dict()
        
        # Details für Fehler loggen
        if error.status_code >= 500:
            # Server-Fehler ausführlich loggen
            logger.error(f"API Error: {error.message} [Status: {error.status_code}]")
        else:
            # Client-Fehler kurz loggen
            logger.info(f"API Error: {error.message} [Status: {error.status_code}]")
        
        return jsonify(response), error.status_code
    
    # Handler für HTTP-Exceptions (z.B. 404, 405)
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        response = {
            'error': error.description
        }
        
        # Request-ID hinzufügen, falls vorhanden
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        # Fehler loggen
        logger.info(f"HTTP Exception: {error.description} [Status: {error.code}]")
        
        return jsonify(response), error.code
    
    # Handler für allgemeine Exceptions
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        # In Entwicklung vollständigen Stacktrace einfügen
        if app.debug:
            error_details = ''.join(traceback.format_exception(
                type(error), error, error.__traceback__))
            
            response = {
                'error': 'Internal server error',
                'message': str(error),
                'traceback': error_details
            }
        else:
            # In Produktion nur generische Meldung zurückgeben
            response = {
                'error': 'Internal server error'
            }
        
        # Request-ID hinzufügen, falls vorhanden
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
        
        # Immer vollständigen Stacktrace loggen
        logger.error(f"Unhandled Exception: {str(error)}", exc_info=True)
        
        return jsonify(response), 500
    
    # Spezifische Fehlerbehandlung für häufige Fälle
    
    # Not Found (404)
    @app.errorhandler(404)
    def not_found(error):
        response = {
            'error': 'Resource not found',
            'path': request.path
        }
        
        # Request-ID hinzufügen, falls vorhanden
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        return jsonify(response), 404
    
    # Method Not Allowed (405)
    @app.errorhandler(405)
    def method_not_allowed(error):
        response = {
            'error': 'Method not allowed',
            'message': f"Die Methode {request.method} ist für diesen Endpunkt nicht erlaubt"
        }
        
        # Request-ID hinzufügen, falls vorhanden
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        return jsonify(response), 405
    
    # Payload Too Large (413)
    @app.errorhandler(413)
    def payload_too_large(error):
        max_content_length = current_app.config.get('MAX_CONTENT_LENGTH', 0)
        max_content_length_mb = max_content_length / (1024 * 1024) if max_content_length else 'unbekannt'
        
        response = {
            'error': 'Payload too large',
            'message': f"Die hochgeladene Datei überschreitet die maximale Größe von {max_content_length_mb}MB"
        }
        
        # Request-ID hinzufügen, falls vorhanden
        if hasattr(g, 'request_id'):
            response['request_id'] = g.request_id
            
        return jsonify(response), 413

# Hilfsfunktionen für häufige API-Fehlerfälle

def bad_request(message: str, details: Any = None) -> None:
    """
    Löst einen 400 Bad Request-Fehler aus
    
    Args:
        message: Fehlermeldung
        details: Optionale Details
    
    Raises:
        APIError: mit Statuscode 400
    """
    raise APIError(message, status_code=400, details=details)

def unauthorized(message: str = "Authentifizierung erforderlich", details: Any = None) -> None:
    """
    Löst einen 401 Unauthorized-Fehler aus
    
    Args:
        message: Fehlermeldung
        details: Optionale Details
    
    Raises:
        APIError: mit Statuscode 401
    """
    raise APIError(message, status_code=401, details=details)

def forbidden(message: str = "Zugriff verboten", details: Any = None) -> None:
    """
    Löst einen 403 Forbidden-Fehler aus
    
    Args:
        message: Fehlermeldung
        details: Optionale Details
    
    Raises:
        APIError: mit Statuscode 403
    """
    raise APIError(message, status_code=403, details=details)

def not_found(message: str = "Ressource nicht gefunden", details: Any = None) -> None:
    """
    Löst einen 404 Not Found-Fehler aus
    
    Args:
        message: Fehlermeldung
        details: Optionale Details
    
    Raises:
        APIError: mit Statuscode 404
    """
    raise APIError(message, status_code=404, details=details)

def server_error(message: str = "Interner Serverfehler", details: Any = None) -> None:
    """
    Löst einen 500 Internal Server Error aus
    
    Args:
        message: Fehlermeldung
        details: Optionale Details
    
    Raises:
        APIError: mit Statuscode 500
    """
    raise APIError(message, status_code=500, details=details)

def validation_error(errors: Dict[str, str]) -> None:
    """
    Löst einen 422 Validation Error aus
    
    Args:
        errors: Dictionary mit Feld/Fehlermeldungen
    
    Raises:
        APIError: mit Statuscode 422
    """
    raise APIError("Validierungsfehler", status_code=422, details=errors)

def safe_execution(func: Callable, error_handler: Callable = None, **kwargs) -> Any:
    """
    Führt eine Funktion sicher aus und behandelt Fehler
    
    Args:
        func: Auszuführende Funktion
        error_handler: Optionale Fehlerbehandlungsfunktion, die den Fehler erhält
        **kwargs: Zusätzliche Parameter für die Fehlerbehandlung
    
    Returns:
        Rückgabewert der Funktion oder der Fehlerbehandlung
        
    Beispiel:
        @app.route('/api/example')
        def example():
            return safe_execution(
                do_something_risky,
                error_handler=lambda e: jsonify({"error": str(e)}),
                status_code=500
            )
    """
    try:
        return func()
    except Exception as e:
        logger.error(f"Error in safe_execution: {e}", exc_info=True)
        
        if error_handler:
            return error_handler(e, **kwargs)
        
        # Standard-Fehlerbehandlung, falls keine angegeben
        if isinstance(e, APIError):
            return jsonify(e.to_dict()), e.status_code
        
        return jsonify({"error": str(e)}), kwargs.get('status_code', 500)

# Zusätzliche Hilfsfunktionen für Stream-Fehlerbehandlung

def error_to_stream(error: Union[Exception, str]) -> Tuple[Dict[str, Any], int]:
    """
    Konvertiert einen Fehler in ein Stream-freundliches Format
    
    Args:
        error: Fehler oder Fehlermeldung
    
    Returns:
        tuple: (Fehler-Dictionary, Statuscode)
    """
    if isinstance(error, APIError):
        return error.to_dict(), error.status_code
    elif isinstance(error, Exception):
        return {"error": str(error)}, 500
    else:
        return {"error": error}, 500