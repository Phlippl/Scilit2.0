# Backend/utils/helpers.py
"""
Verschiedene Hilfsfunktionen für das SciLit2.0-Backend
"""
import re
import os
from flask import current_app
from werkzeug.utils import secure_filename

def allowed_file(filename):
    """
    Prüft, ob die Dateiendung erlaubt ist
    
    Args:
        filename (str): Der Dateiname
        
    Returns:
        bool: True, wenn die Datei erlaubt ist, sonst False
    """
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_doi(text):
    """
    Extrahiert DOI aus Text mittels Regex
    
    Args:
        text (str): Text, in dem nach DOI gesucht werden soll
        
    Returns:
        str: Gefundene DOI oder None
    """
    if not text:
        return None
    
    # DOI-Muster (verbessert für bessere Übereinstimmung)
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

def extract_isbn(text):
    """
    Extrahiert ISBN aus Text mittels Regex
    
    Args:
        text (str): Text, in dem nach ISBN gesucht werden soll
        
    Returns:
        str: Gefundene ISBN oder None
    """
    if not text:
        return None
    
    # ISBN-Muster
    isbn_patterns = [
        r'ISBN(?:-13)?[:\s]*(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # ISBN-13
        r'ISBN(?:-10)?[:\s]*(\d[- ]?(?:\d[- ]?){8}[\dX])\b',   # ISBN-10
        r'\b(97[89][- ]?(?:\d[- ]?){9}\d)\b',  # Bare ISBN-13
        r'\b(\d[- ]?(?:\d[- ]?){8}[\dX])\b'    # Bare ISBN-10
    ]
    
    for pattern in isbn_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            # Bindestriche und Leerzeichen entfernen
            return match.group(1).replace('-', '').replace(' ', '')
    
    return None

def get_safe_filepath(document_id, filename):
    """
    Erstellt einen sicheren Dateipfad für hochgeladene Dateien
    
    Args:
        document_id (str): ID des Dokuments
        filename (str): Ursprünglicher Dateiname
        
    Returns:
        str: Sicherer Dateipfad
    """
    safe_filename = secure_filename(filename)
    return os.path.join(current_app.config['UPLOAD_FOLDER'], f"{document_id}_{safe_filename}")