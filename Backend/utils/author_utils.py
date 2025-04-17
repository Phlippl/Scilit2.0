# Backend/utils/author_utils.py
"""
Zentralisierte Funktionen zur Formatierung und Verarbeitung von Autorennamen und -listen.
Kombiniert und optimiert aus helpers.py und document_validation.py.
"""
import json
import logging
import re
from typing import List, Dict, Any, Union

# Configure logging
logger = logging.getLogger(__name__)

def format_authors(authors_data: Union[List[Dict[str, str]], List[str], str]) -> List[Dict[str, str]]:
    """
    Format authors into a standardized structure.
    Handles different input formats (string, list, dict) and returns a standardized list.
    
    Args:
        authors_data: Authors data in various formats
            - List of dictionaries with author information
            - List of strings with author names
            - String with comma/semicolon separated author names
            - JSON string representing a list of authors
            
    Returns:
        list: List of standardized author dictionaries with at least 'name' field
    """
    if not authors_data:
        return []
    
    # If already a list
    if isinstance(authors_data, list):
        formatted_authors = []
        for i, author in enumerate(authors_data):
            if isinstance(author, dict):
                # Ensure it has the proper structure
                if 'name' not in author:
                    # Try to construct name from given/family if available
                    if 'given' in author and 'family' in author:
                        author['name'] = f"{author['family']}, {author['given']}"
                    else:
                        logger.warning(f"Author at position {i} is missing required 'name' field")
                        continue
                
                # Create standardized author entry
                formatted_authors.append({
                    'name': author.get('name', ''),
                    'orcid': author.get('orcid', '')
                })
            elif isinstance(author, str):
                formatted_authors.append({
                    'name': author,
                    'orcid': ''
                })
            else:
                logger.warning(f"Invalid author format at position {i}")
        
        return formatted_authors
    
    # If a string, try to parse as JSON or as semicolon-separated
    if isinstance(authors_data, str):
        # Try to parse as JSON
        if authors_data.startswith('[') and authors_data.endswith(']'):
            try:
                author_list = json.loads(authors_data)
                return format_authors(author_list)
            except json.JSONDecodeError:
                logger.warning("Failed to parse authors JSON string")
        
        # Try as semicolon-separated list or comma-separated list
        if ';' in authors_data:
            author_list = authors_data.split(';')
        else:
            author_list = authors_data.split(',')
            
        return [{'name': name.strip(), 'orcid': ''} for name in author_list if name.strip()]
    
    # Fallback for unknown format
    logger.warning(f"Unsupported authors data format: {type(authors_data)}")
    return []

def normalize_author_name(author_name: str) -> Dict[str, str]:
    """
    Normalize a single author name into a standardized format
    
    Args:
        author_name: Author name string
        
    Returns:
        dict: Author information with name in normalized format
    """
    if not author_name or not isinstance(author_name, str):
        return {'name': '', 'given': '', 'family': ''}
    
    name = author_name.strip()
    
    # If already in "Last Name, First Name" format
    if ',' in name:
        parts = name.split(',', 1)
        family_name = parts[0].strip()
        given_name = parts[1].strip() if len(parts) > 1 else ""
    else:
        # Try to split into first and last name
        parts = name.split()
        if len(parts) > 1:
            family_name = parts[-1]
            given_name = ' '.join(parts[:-1])
        else:
            family_name = name
            given_name = ""
    
    return {
        'name': name,
        'given': given_name,
        'family': family_name
    }

def format_author_for_citation(author: Dict[str, str], style: str = 'apa') -> str:
    """
    Format an author name according to a specific citation style
    
    Args:
        author: Author information dictionary with at least 'name' field
        style: Citation style ('apa', 'chicago', 'harvard', etc.)
        
    Returns:
        str: Formatted author name
    """
    if not author or 'name' not in author:
        return ""
    
    name = author['name']
    
    # Normalize author data
    author_data = normalize_author_name(name)
    family_name = author_data['family']
    given_name = author_data['given']
    
    if style == 'apa':
        # APA: Family, Initials.
        if given_name:
            initials = ' '.join(f"{n[0]}." for n in given_name.split() if n)
            return f"{family_name}, {initials}"
        return family_name
    
    elif style == 'chicago':
        # Chicago: Family, Full Given
        if given_name:
            return f"{family_name}, {given_name}"
        return family_name
    
    elif style == 'harvard':
        # Harvard: Family, Initials with spaces
        if given_name:
            initials = ' '.join(f"{n[0]}." for n in given_name.split() if n)
            return f"{family_name}, {initials}"
        return family_name
    
    # Default format (apa)
    if given_name:
        initials = ' '.join(f"{n[0]}." for n in given_name.split() if n)
        return f"{family_name}, {initials}"
    return family_name

def format_authors_list(authors: List[Dict[str, str]], style: str = 'apa') -> str:
    """
    Format a list of authors according to a specific citation style
    
    Args:
        authors: List of author dictionaries with at least 'name' field
        style: Citation style ('apa', 'chicago', 'harvard', etc.)
        
    Returns:
        str: Formatted authors list as a string
    """
    if not authors:
        return "Unknown Author"
    
    # Format each author according to style
    formatted_authors = [format_author_for_citation(author, style) for author in authors]
    
    if style == 'apa':
        # APA style
        if len(formatted_authors) == 1:
            return formatted_authors[0]
        elif len(formatted_authors) == 2:
            return f"{formatted_authors[0]} & {formatted_authors[1]}"
        elif len(formatted_authors) <= 7:
            return f"{', '.join(formatted_authors[:-1])}, & {formatted_authors[-1]}"
        else:
            return f"{', '.join(formatted_authors[:6])}, ... & {formatted_authors[-1]}"
    
    elif style == 'chicago':
        # Chicago style
        if len(formatted_authors) == 1:
            return formatted_authors[0]
        elif len(formatted_authors) <= 3:
            return ", ".join(formatted_authors)
        else:
            return f"{formatted_authors[0]} et al."
    
    elif style == 'harvard':
        # Harvard style
        if len(formatted_authors) == 1:
            return formatted_authors[0]
        elif len(formatted_authors) == 2:
            return f"{formatted_authors[0]} & {formatted_authors[1]}"
        elif len(formatted_authors) <= 4:
            return f"{', '.join(formatted_authors[:-1])} & {formatted_authors[-1]}"
        else:
            return f"{formatted_authors[0]} et al."
    
    # Default format (simple)
    if len(formatted_authors) == 1:
        return formatted_authors[0]
    elif len(formatted_authors) == 2:
        return f"{formatted_authors[0]} & {formatted_authors[1]}"
    else:
        return f"{formatted_authors[0]} et al."