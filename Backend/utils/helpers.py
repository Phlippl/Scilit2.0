# Backend/utils/helpers.py
"""
Various helper functions for the SciLit2.0 backend with centralized implementations
"""
import re
import os
import logging
import threading
import time
import psutil
import functools
from flask import current_app
from werkzeug.utils import secure_filename
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed
    
    Args:
        filename: The filename
        
    Returns:
        bool: True if file is allowed, else False
    """
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_doi(text: str) -> Optional[str]:
    """
    Extract DOI from text using regex
    
    Args:
        text: Text to search for DOI
        
    Returns:
        str: Found DOI or None
    """
    if not text:
        return None
    
    # DOI patterns (improved for better matching)
    # Format: 10.XXXX/XXXXX
    doi_patterns = [
        r'\b(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b',
        r'\bDOI:\s*(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b',
        r'\bdoi\.org\/(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b'
    ]
    
    for pattern in doi_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            return match.group(1)
    
    return None

def extract_isbn(text: str) -> Optional[str]:
    """
    Extract ISBN from text using regex
    
    Args:
        text: Text to search for ISBN
        
    Returns:
        str: Found ISBN or None
    """
    if not text:
        return None
    
    # ISBN patterns
    isbn_patterns = [
        r'ISBN(?:-13)?[:\s]*(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # ISBN-13
        r'ISBN(?:-10)?[:\s]*(\d[- ]?(?:\d[- ]?){8}[\dX])\b',   # ISBN-10
        r'\b(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # Bare ISBN-13
        r'\b(\d[- ]?(?:\d[- ]?){8}[\dX])\b'    # Bare ISBN-10
    ]
    
    for pattern in isbn_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            # Remove hyphens and spaces
            return match.group(1).replace('-', '').replace(' ', '')
    
    return None

def get_safe_filepath(document_id: str, filename: str) -> str:
    """
    Create a safe file path for uploaded files
    
    Args:
        document_id: Document ID
        filename: Original filename
        
    Returns:
        str: Safe file path
    """
    # Ensure upload folder exists
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    
    safe_filename = secure_filename(filename)
    return os.path.join(upload_folder, f"{document_id}_{safe_filename}")

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

def format_authors(authors) -> List[Dict[str, str]]:
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
                import json
                author_list = json.loads(authors)
                return format_authors(author_list)
            except json.JSONDecodeError:
                pass
        
        # Try as semicolon-separated list
        author_list = authors.split(';')
        return [{'name': name.strip(), 'orcid': ''} for name in author_list if name.strip()]
    
    # Fallback
    return []

def format_metadata_for_storage(metadata: Dict[str, Any]) -> Dict[str, Any]:
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

def timeout_handler(max_seconds=120, cpu_limit=70):
    """
    Decorator to limit function execution time and CPU usage
    
    Args:
        max_seconds: Maximum execution time in seconds
        cpu_limit: CPU usage limit in percent
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e
            
            # Start function in a separate thread
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            
            # Monitor execution time and CPU usage
            start_time = time.time()
            process = psutil.Process(os.getpid())
            
            while thread.is_alive():
                thread.join(timeout=1.0)
                elapsed = time.time() - start_time
                
                # Check time limit
                if elapsed > max_seconds:
                    error[0] = TimeoutError(f"Function execution exceeded {max_seconds} seconds")
                    break
                
                # Check CPU usage
                try:
                    cpu_percent = process.cpu_percent(interval=0.5)
                    if cpu_percent > cpu_limit:
                        error[0] = Exception(f"CPU usage too high: {cpu_percent}% (limit: {cpu_limit}%)")
                        break
                except Exception:
                    pass
            
            if error[0]:
                raise error[0]
            
            return result[0]
        
        return wrapper
    return decorator