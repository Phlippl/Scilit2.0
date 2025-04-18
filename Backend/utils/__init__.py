# Backend/utils/__init__.py
"""
Package for utility functions used throughout the application.
"""

# Re-export file utilities
from .file_utils import allowed_file, get_safe_filepath, cleanup_file, read_json, write_json

# Re-export error handling utilities
from .error_handler import APIError, bad_request, unauthorized, forbidden, not_found, server_error

# Re-export performance utilities
from .performance_utils import timeout_handler, memory_profile

# Re-export identifier utilities
from .identifier_utils import extract_doi, extract_isbn, extract_identifiers

# Re-export author utilities
from .author_utils import format_authors, format_author_for_citation, format_authors_list

# Re-export metadata utilities
from .metadata_utils import (
    format_metadata_for_storage, normalize_date, validate_metadata,
    format_crossref_metadata, merge_metadata
)