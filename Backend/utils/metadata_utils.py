# Backend/utils/metadata_utils.py
"""
Zentralisierte Funktionen für die Verarbeitung und Formatierung von Dokumentmetadaten.
Kombiniert und optimiert aus helpers.py, document_validation.py und metadata.py.
"""
import re
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

# Import zentralisierte Autor-Utilities
from utils.author_utils import format_authors
from utils.identifier_utils import validate_doi, validate_isbn

# Configure logging
logger = logging.getLogger(__name__)

def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date string to ISO format (YYYY-MM-DD)
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        str: Normalized date in ISO format or None
    """
    if not date_str:
        return None
    
    try:
        # If already in ISO format (YYYY-MM-DD)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
        
        # If only year (YYYY)
        if re.match(r'^\d{4}$', date_str):
            return f"{date_str}-01-01"
        
        # If year-month (YYYY-MM)
        if re.match(r'^\d{4}-\d{2}$', date_str):
            return f"{date_str}-01"
        
        # If in format DD.MM.YYYY
        if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', date_str):
            parts = date_str.split('.')
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        
        # If in format MM/DD/YYYY
        if re.match(r'^\d{1,2}\/\d{1,2}\/\d{4}$', date_str):
            parts = date_str.split('/')
            return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
        
        # If in format YYYY/MM/DD
        if re.match(r'^\d{4}\/\d{1,2}\/\d{1,2}$', date_str):
            parts = date_str.split('/')
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        
        # Try to extract year
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            year = year_match.group(1)
            return f"{year}-01-01"
        
        return None
    except Exception as e:
        logger.error(f"Error normalizing date: {e}")
        return None

def validate_metadata(metadata: Dict[str, Any]) -> tuple:
    """
    Validate document metadata structure and content
    
    Args:
        metadata: Document metadata to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(metadata, dict):
        return False, "Metadata must be a dictionary"
    
    # Required fields validation
    required_fields = ['title', 'type']
    for field in required_fields:
        if field not in metadata or not metadata[field]:
            return False, f"Required field '{field}' is missing or empty"
    
    # Title validation
    if len(metadata.get('title', '')) > 500:
        return False, "Title is too long (max 500 characters)"
    
    # Type validation
    valid_types = ['article', 'book', 'edited_book', 'conference', 'thesis', 
                   'report', 'newspaper', 'website', 'interview', 'press', 'other']
    if metadata.get('type') not in valid_types:
        return False, f"Invalid document type. Must be one of: {', '.join(valid_types)}"
    
    # Date validation
    date_fields = ['publicationDate', 'date', 'lastUpdated', 'accessDate']
    for field in date_fields:
        if field in metadata and metadata[field]:
            date_value = metadata[field]
            
            # Basic ISO date format validation (YYYY-MM-DD)
            if isinstance(date_value, str):
                valid_date_formats = [
                    r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
                    r'^\d{4}-\d{2}$',         # YYYY-MM
                    r'^\d{4}$'                # YYYY
                ]
                valid_format = any(re.match(pattern, date_value) for pattern in valid_date_formats)
                if not valid_format:
                    return False, f"Invalid date format for {field}. Use YYYY-MM-DD, YYYY-MM or YYYY"
            else:
                return False, f"Date field {field} must be a string"
    
    # DOI validation
    if 'doi' in metadata and metadata['doi']:
        if not validate_doi(metadata['doi']):
            return False, "Invalid DOI format. DOIs should start with '10.'"
    
    # ISBN validation
    if 'isbn' in metadata and metadata['isbn']:
        if not validate_isbn(metadata['isbn']):
            return False, "Invalid ISBN format. Must be 10 or 13 digits."
    
    # Check for excessive field lengths
    long_text_fields = {
        'abstract': 10000,
        'title': 500,
        'journal': 200,
        'publisher': 200
    }
    
    for field, max_length in long_text_fields.items():
        if field in metadata and isinstance(metadata[field], str) and len(metadata[field]) > max_length:
            return False, f"Field '{field}' exceeds maximum length of {max_length} characters"
    
    return True, None

def format_metadata_for_storage(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format metadata for consistent storage format
    
    Args:
        metadata: Raw metadata
        
    Returns:
        dict: Formatted metadata
    """
    if not metadata:
        return {}
        
    formatted = {}
    
    # Copy basic fields
    basic_fields = [
        'title', 'type', 'journal', 'publisher', 'doi', 'isbn', 'abstract', 
        'volume', 'issue', 'pages', 'document_id', 'user_id'
    ]
    
    for field in basic_fields:
        if field in metadata:
            formatted[field] = metadata[field]
    
    # Format authors
    if 'authors' in metadata:
        formatted['authors'] = format_authors(metadata['authors'])
    
    # Normalize dates
    date_fields = ['publicationDate', 'date', 'lastUpdated', 'accessDate', 'uploadDate']
    for field in date_fields:
        if field in metadata:
            formatted[field] = normalize_date(metadata[field])
    
    # Add processing information if available
    processing_fields = [
        'processingComplete', 'processedDate', 'processingError', 
        'num_chunks', 'chunk_size', 'chunk_overlap'
    ]
    
    for field in processing_fields:
        if field in metadata:
            formatted[field] = metadata[field]
    
    return formatted

def format_crossref_metadata(crossref_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format CrossRef metadata into standard format
    
    Args:
        crossref_data: Metadata from CrossRef API
        
    Returns:
        dict: Standardized metadata
    """
    if not crossref_data:
        return {}
    
    try:
        # Extract title
        title = ""
        if 'title' in crossref_data:
            if isinstance(crossref_data['title'], list) and crossref_data['title']:
                title = crossref_data['title'][0]
            else:
                title = crossref_data['title']
        
        # Determine document type
        document_type = 'article'  # Default
        crossref_type = crossref_data.get('type', '').lower()
        
        # Mapping from CrossRef types to our application types
        type_mapping = {
            'journal-article': 'article',
            'book': 'book',
            'book-chapter': 'book',
            'monograph': 'book',
            'edited-book': 'edited_book',
            'proceedings-article': 'conference',
            'proceedings': 'conference',
            'conference-paper': 'conference',
            'dissertation': 'thesis',
            'report': 'report',
            'report-component': 'report',
            'journal': 'article',
            'newspaper-article': 'newspaper',
            'website': 'website',
            'peer-review': 'article',
            'standard': 'report',
            'posted-content': 'other',
            'reference-entry': 'other'
        }
        
        # Try to map the type
        if crossref_type in type_mapping:
            document_type = type_mapping[crossref_type]
        # Fallback to type inference
        elif 'book' in crossref_type:
            document_type = 'book'
        elif 'journal' in crossref_type or 'article' in crossref_type:
            document_type = 'article'
        elif 'conference' in crossref_type or 'proceedings' in crossref_type:
            document_type = 'conference'
        elif 'thesis' in crossref_type or 'dissertation' in crossref_type:
            document_type = 'thesis'
        
        logger.debug(f"Mapped document type from CrossRef '{crossref_type}' to '{document_type}'")
        
        # Extract publication date
        publication_date = ''
        if 'published' in crossref_data:
            date_parts = crossref_data['published'].get('date-parts', [[]])[0]
            if date_parts:
                # Format as YYYY-MM-DD or only year
                if len(date_parts) >= 3:
                    publication_date = f"{date_parts[0]}-{date_parts[1]:02d}-{date_parts[2]:02d}"
                elif len(date_parts) == 2:
                    publication_date = f"{date_parts[0]}-{date_parts[1]:02d}-01"
                elif len(date_parts) == 1:
                    publication_date = f"{date_parts[0]}-01-01"
        
        # Extract journal/container title
        journal = ""
        if 'container-title' in crossref_data:
            if isinstance(crossref_data['container-title'], list) and crossref_data['container-title']:
                journal = crossref_data['container-title'][0]
            else:
                journal = crossref_data['container-title']
        
        # Extract ISBN for books
        isbn = ""
        if 'ISBN' in crossref_data:
            if isinstance(crossref_data['ISBN'], list) and crossref_data['ISBN']:
                isbn = crossref_data['ISBN'][0].replace('-', '')
            else:
                isbn = crossref_data['ISBN'].replace('-', '')
        
        # Create standardized metadata
        result = {
            'title': title,
            'authors': crossref_data.get('author', []),
            'type': document_type,
            'publicationDate': publication_date,
            'publisher': crossref_data.get('publisher', ''),
            'journal': journal,
            'volume': crossref_data.get('volume', ''),
            'issue': crossref_data.get('issue', ''),
            'pages': crossref_data.get('page', ''),
            'doi': crossref_data.get('DOI', ''),
            'isbn': isbn,
            'abstract': crossref_data.get('abstract', '')
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting CrossRef metadata: {e}")
        return {}

def merge_metadata(base_metadata: Dict[str, Any], new_metadata: Dict[str, Any], 
                 priority: str = 'new') -> Dict[str, Any]:
    """
    Merge two metadata dictionaries with priority handling
    
    Args:
        base_metadata: Base metadata dictionary
        new_metadata: New metadata to merge
        priority: Which metadata to prioritize in conflicts ('new' or 'base')
        
    Returns:
        dict: Merged metadata
    """
    if not base_metadata:
        return new_metadata or {}
    if not new_metadata:
        return base_metadata
    
    merged = base_metadata.copy()
    
    for key, value in new_metadata.items():
        # Skip None or empty values
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
            
        # Handle priority for existing fields
        if key in merged and merged[key]:
            if priority == 'new':
                merged[key] = value
        else:
            # Always add new fields
            merged[key] = value
    
    return merged