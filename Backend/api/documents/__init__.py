# Backend/api/documents/__init__.py
"""
Package für Dokument-API-Endpunkte und zugehörige Funktionen
"""

# Import the blueprint from routes.py
from .routes import documents_bp

# Import functions directly from status_service
from services.status_service import (
    get_status_service,
    initialize_status_service
)

from utils.metadata_utils import (
    validate_metadata, 
    format_metadata_for_storage
)

from .document_analysis import (
    analyze_document_background, 
    get_analysis_results
)

__all__ = [
    'documents_bp',
    'get_status_service',
    'initialize_status_service',
    'validate_metadata',
    'format_metadata_for_storage',
    'analyze_document_background',
    'get_analysis_results'
]