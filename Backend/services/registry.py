# Backend/services/registry.py
"""
Zentrales Service-Registry-Modul zur Verwaltung aller Dienste.
Implementiert ein Singleton-Muster für Services, um konsistente Instanzen zu gewährleisten.
"""
import logging
from typing import Dict, Any, Optional, Type, Callable

logger = logging.getLogger(__name__)

# Speicher für Service-Instanzen
_services: Dict[str, Any] = {}
_factories: Dict[str, Callable[[], Any]] = {}

def register_factory(service_name: str, factory: Callable[[], Any]) -> None:
    """
    Registriert eine Factory-Funktion für einen Service
    
    Args:
        service_name: Name des Services
        factory: Factory-Funktion zur Erstellung der Service-Instanz
    """
    global _factories
    _factories[service_name] = factory
    logger.debug(f"Factory für Service '{service_name}' registriert")

def register(service_name: str, instance: Any) -> None:
    """
    Registriert eine Service-Instanz direkt
    
    Args:
        service_name: Name des Services
        instance: Service-Instanz
    """
    global _services
    _services[service_name] = instance
    logger.debug(f"Service '{service_name}' direkt registriert")

def get(service_name: str) -> Any:
    """
    Holt eine Service-Instanz, erstellt sie bei Bedarf
    
    Args:
        service_name: Name des Services
        
    Returns:
        Service-Instanz
        
    Raises:
        KeyError: Wenn kein Service oder Factory mit diesem Namen registriert ist
    """
    global _services, _factories
    
    # Prüfe, ob Service bereits existiert
    if service_name in _services:
        return _services[service_name]
    
    # Erstelle Service mit Factory, wenn registriert
    if service_name in _factories:
        logger.debug(f"Erstelle Service '{service_name}' mit Factory")
        instance = _factories[service_name]()
        _services[service_name] = instance
        return instance
    
    # Kein Service oder Factory gefunden
    raise KeyError(f"Kein Service oder Factory mit Namen '{service_name}' registriert")

def initialize_services() -> None:
    """
    Initialisiert Standard-Services mit ihren Factory-Funktionen
    """
    from services.document_storage_service import DocumentStorageService
    from services.document_analysis_service import DocumentAnalysisService
    from services.document_db_service import DocumentDBService
    from Backend.services.status_service import get_status_service
    from services.authentication import get_auth_manager
    from services.pdf import get_pdf_processor
    
    # Registriere Document-Services
    register_factory('document_storage', lambda: DocumentStorageService())
    register_factory('document_analysis', lambda: DocumentAnalysisService())
    register_factory('document_db', lambda: DocumentDBService())
    
    # Registriere andere Services als Factory-Funktionen
    register_factory('status', get_status_service)
    register_factory('auth', get_auth_manager)
    register_factory('pdf_processor', get_pdf_processor)
    
    logger.info("Standard-Services initialisiert")

def reset() -> None:
    """
    Setzt alle Services zurück (primär für Tests)
    """
    global _services
    _services.clear()
    logger.debug("Alle Services zurückgesetzt")