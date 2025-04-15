# Backend/api/documents/document_validation.py
"""
Validation module for document metadata and processing
"""
import re
import json
import logging

logger = logging.getLogger(__name__)

def validate_metadata(metadata):
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
    
    # Authors validation
    if 'authors' in metadata:
        authors = metadata['authors']
        if not isinstance(authors, list):
            return False, "Authors must be a list"
        
        for i, author in enumerate(authors):
            if isinstance(author, dict):
                if 'name' not in author:
                    return False, f"Author at position {i} is missing required 'name' field"
            elif isinstance(author, str):
                # Convert string authors to dict format for consistency
                authors[i] = {'name': author}
            else:
                return False, f"Invalid author format at position {i}"
    
    # Date validation
    date_fields = ['publicationDate', 'date', 'lastUpdated', 'accessDate']
    for field in date_fields:
        if field in metadata and metadata[field]:
            date_value = metadata[field]
            
            # Basic ISO date format validation (YYYY-MM-DD)
            if isinstance(date_value, str):
                # Full ISO date
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_value):
                    # Year only
                    if not re.match(r'^\d{4}$', date_value):
                        # Year-Month
                        if not re.match(r'^\d{4}-\d{2}$', date_value):
                            return False, f"Invalid date format for {field}. Use YYYY-MM-DD, YYYY-MM or YYYY"
            else:
                return False, f"Date field {field} must be a string"
    
    # DOI validation
    if 'doi' in metadata and metadata['doi']:
        doi = metadata['doi']
        if not re.match(r'^10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+$', doi):
            return False, "Invalid DOI format. DOIs should start with '10.'"
    
    # ISBN validation
    if 'isbn' in metadata and metadata['isbn']:
        isbn = metadata['isbn'].replace('-', '').replace(' ', '')
        if not (len(isbn) == 10 or len(isbn) == 13):
            return False, "Invalid ISBN length. Must be 10 or 13 digits."
        if not isbn.isdigit() and not (isbn[:-1].isdigit() and isbn[-1] in '0123456789Xx'):
            return False, "Invalid ISBN format. Must contain only digits (except for ISBN-10 check digit 'X')"
    
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

def format_authors(authors):
    """
    Format authors into a standardized structure
    
    Args:
        authors: Authors data (string, list, or dict)
        
    Returns:
        list: List of author dictionaries
    """
    if not authors:
        return []
    
    # If already a list
    if isinstance(authors, list):
        formatted_authors = []
        for author in authors:
            if isinstance(author, dict):
                # Ensure it has the proper structure
                if 'name' not in author:
                    # Try to construct name from given/family if available
                    if 'given' in author and 'family' in author:
                        author['name'] = f"{author['family']}, {author['given']}"
                    else:
                        continue
                
                formatted_authors.append({
                    'name': author.get('name', ''),
                    'orcid': author.get('orcid', '')
                })
            elif isinstance(author, str):
                formatted_authors.append({
                    'name': author,
                    'orcid': ''
                })
        
        return formatted_authors
    
    # If a string, try to parse as semicolon-separated
    if isinstance(authors, str):
        # Try to parse as JSON
        if authors.startswith('[') and authors.endswith(']'):
            try:
                author_list = json.loads(authors)
                return format_authors(author_list)
            except json.JSONDecodeError:
                pass
        
        # Try as semicolon-separated list
        author_list = authors.split(';')
        return [{'name': name.strip(), 'orcid': ''} for name in author_list if name.strip()]
    
    # Fallback
    return []

def normalize_date(date_str):
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
        
        # If in format DD.MM.YYYY
        if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', date_str):
            parts = date_str.split('.')
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        
        # If in format MM/DD/YYYY
        if re.match(r'^\d{1,2}\/\d{1,2}\/\d{4}$', date_str):
            parts = date_str.split('/')
            return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
        
        # Try to extract year
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            year = year_match.group(1)
            return f"{year}-01-01"
        
        return None
    except Exception as e:
        logger.error(f"Error normalizing date: {e}")
        return None

def format_metadata_for_storage(metadata):
    """
    Format metadata for consistent storage format
    
    Args:
        metadata: Raw metadata
        
    Returns:
        dict: Formatted metadata
    """
    formatted = {}
    
    # Copy basic fields
    for field in ['title', 'type', 'journal', 'publisher', 'doi', 'isbn', 'abstract', 'volume', 'issue', 'pages']:
        if field in metadata:
            formatted[field] = metadata[field]
    
    # Format authors
    if 'authors' in metadata:
        formatted['authors'] = format_authors(metadata['authors'])
    
    # Normalize dates
    for date_field in ['publicationDate', 'date', 'lastUpdated', 'accessDate']:
        if date_field in metadata:
            formatted[date_field] = normalize_date(metadata[date_field])
    
    return formatted