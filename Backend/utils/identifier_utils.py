# Backend/utils/identifier_utils.py
"""
Zentralisierte Funktionen zur Erkennung und Extraktion von DOI und ISBN aus Texten.
Kombiniert und optimiert aus helpers.py, pdf_processor.py und metadata_service.py.
"""
import re
import logging

# Configure logging
logger = logging.getLogger(__name__)

def extract_doi(text):
    """
    Extract DOI from text using optimized regex patterns
    
    Args:
        text: Text to search for DOI
        
    Returns:
        str: Found DOI or None
    """
    if not text:
        logger.debug("No text provided for DOI extraction")
        return None
    
    # DOI patterns - Enhanced for better matching
    doi_patterns = [
        # Standard DOI format with word boundary
        r'\b(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b',
        
        # DOI with label
        r'\bDOI:\s*(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b',
        
        # DOI with doi.org URL
        r'\bdoi\.org\/(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\b',
        
        # DOI in URL with https
        r'https?:\/\/doi\.org\/(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)',
        
        # DOI in parentheses - common in academic papers
        r'\(doi:\s*(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)\)',
        
        # DOI with Digital Object Identifier label
        r'Digital\s+Object\s+Identifier.{0,20}(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)',
        
        # DOI in German text
        r'(?:DOI|doi)[-:]?\s*(10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+)'
    ]
    
    for idx, pattern in enumerate(doi_patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            doi = match.group(1).strip()
            logger.debug(f"DOI found with pattern {idx+1}: {doi}")
            return doi
    
    logger.debug("No DOI found in text")
    return None

def extract_isbn(text):
    """
    Extract ISBN from text using enhanced regex patterns
    
    Args:
        text: Text to search for ISBN
        
    Returns:
        str: Found ISBN or None
    """
    if not text:
        logger.debug("No text provided for ISBN extraction")
        return None
    
    # ISBN patterns - Enhanced for better matching
    isbn_patterns = [
        # ISBN-13 with label
        r'\bISBN(?:-13)?[:\s]*(97[89][- ]?(?:\d[- ]?){9}\d)\b',
        
        # ISBN-10 with label
        r'\bISBN(?:-10)?[:\s]*(\d[- ]?(?:\d[- ]?){8}[\dX])\b',
        
        # Bare ISBN-13 with word boundary
        r'\b(97[89][- ]?(?:\d[- ]?){9}\d)\b',
        
        # Bare ISBN-10 with word boundary  
        r'\b(\d[- ]?(?:\d[- ]?){8}[\dX])\b',
        
        # ISBN in German text
        r'(?:ISBN|isbn)[-:]?\s*((?:97[89][- ]?)?(?:\d[- ]?){9}[\dX])',
        
        # ISBN with International Standard Book Number label
        r'International\s+Standard\s+Book\s+Number.{0,20}((?:97[89][- ]?)?(?:\d[- ]?){9}[\dX])'
    ]
    
    for idx, pattern in enumerate(isbn_patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            # Clean the ISBN by removing hyphens and spaces
            isbn = match.group(1).replace('-', '').replace(' ', '')
            logger.debug(f"ISBN found with pattern {idx+1}: {isbn}")
            return isbn
    
    logger.debug("No ISBN found in text")
    return None

def extract_identifiers(text):
    """
    Extract DOI and ISBN from text
    
    Args:
        text: Text to search
        
    Returns:
        dict: Dictionary with found identifiers {'doi': doi, 'isbn': isbn}
    """
    if not text:
        return {'doi': None, 'isbn': None}
    
    # Extract DOI and ISBN
    doi = extract_doi(text)
    isbn = extract_isbn(text)
    
    logger.debug(f"Extracted identifiers: DOI={doi}, ISBN={isbn}")
    
    return {'doi': doi, 'isbn': isbn}

def validate_doi(doi):
    """
    Validate DOI format
    
    Args:
        doi: DOI string to validate
        
    Returns:
        bool: True if DOI format is valid, else False
    """
    if not doi:
        return False
    
    # Basic DOI format validation
    return bool(re.match(r'^10\.\d{4,}(?:\.\d+)*\/(?:(?!["&\'<>])\S)+$', doi))

def validate_isbn(isbn):
    """
    Validate ISBN format and checksum
    
    Args:
        isbn: ISBN string to validate
        
    Returns:
        bool: True if ISBN format is valid, else False
    """
    if not isbn:
        return False
    
    # Clean the ISBN
    clean_isbn = isbn.replace('-', '').replace(' ', '')
    
    # Check length
    if len(clean_isbn) not in [10, 13]:
        return False
    
    # Check if all characters are digits (except last character of ISBN-10 which can be 'X')
    if len(clean_isbn) == 10:
        if not clean_isbn[:-1].isdigit() or not (clean_isbn[-1].isdigit() or clean_isbn[-1] == 'X'):
            return False
    elif not clean_isbn.isdigit():
        return False
    
    # Additional checksum validation could be added here
    
    return True