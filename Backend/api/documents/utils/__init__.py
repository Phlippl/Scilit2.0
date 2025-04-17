# Backend/api/documents/utils/__init__.py
"""
Utility functions for document processing
"""

# Re-export status management functions
from ..document_status import (
    update_document_status,
    get_document_status,
    cleanup_status,
    register_status_callback
)