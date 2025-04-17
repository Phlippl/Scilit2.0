# Backend/api/documents/__init__.py
"""
Package für Dokument-API-Endpunkte und zugehörige Funktionen
"""

# Import the blueprint from document_api.py
from .document_api import documents_bp

# Import other functions
from .document_processing import (
    process_pdf_background, 
    get_executor
)
from .document_status import (
    update_document_status,
    cleanup_status,
    get_document_status,
    register_status_callback
)

from utils.metadata_utils import validate_metadata, format_metadata_for_storage

from .document_analysis import (
    analyze_document_background, 
    get_analysis_results
)

__all__ = [
    'documents_bp',
    'process_pdf_background',
    'get_executor',
    'get_document_status',
    'update_document_status',
    'cleanup_status',
    'validate_metadata',
    'format_metadata_for_storage',
    'analyze_document_background',
    'get_analysis_results',
    'register_status_callback'
]