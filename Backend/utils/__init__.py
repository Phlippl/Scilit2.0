# Backend/utils/__init__.py
"""
Package for utility functions used throughout the application.
"""

# Re-export common utilities for easier imports
from .helpers import allowed_file, get_safe_filepath, timeout_handler
from .error_handler import APIError, bad_request, unauthorized, forbidden, not_found, server_error

# Export refactored utility functions
from .identifier_utils import extract_doi, extract_isbn, extract_identifiers
from .author_utils import format_authors, format_author_for_citation, format_authors_list
from .metadata_utils import (
    format_metadata_for_storage, normalize_date, validate_metadata,
    format_crossref_metadata, merge_metadata
)