# Backend/api/documents/document_validation.py
"""
Validation module for document metadata and processing
"""
import logging

# Import refactored utility modules
from utils.metadata_utils import validate_metadata, format_metadata_for_storage
from utils.author_utils import format_authors
from utils.identifier_utils import extract_doi, extract_isbn

logger = logging.getLogger(__name__)

# Exportiere die bereits verschobenen Funktionen, um Kompatibilität zu gewährleisten
# Diese Funktionen rufen nur noch die zentralisierten Versionen auf
# und können später entfernt werden, wenn alle Aufrufe aktualisiert wurden
def normalize_date(date_str):
    """
    DEPRECATED: Verwende stattdessen utils.metadata_utils.normalize_date
    """
    from utils.metadata_utils import normalize_date as normalize_date_util
    import warnings
    warnings.warn(
        "document_validation.normalize_date ist veraltet. "
        "Verwende stattdessen utils.metadata_utils.normalize_date",
        DeprecationWarning, stacklevel=2
    )
    return normalize_date_util(date_str)