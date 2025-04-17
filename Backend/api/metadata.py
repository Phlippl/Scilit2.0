# Backend/api/metadata.py
"""
Blueprint für Metadaten-API-Endpunkte
"""
import requests
import time
import logging
import os
from flask import Blueprint, jsonify, request, current_app
from urllib.parse import quote

# Import refactored utility modules
from utils.metadata_utils import format_crossref_metadata

# Logger einrichten
logger = logging.getLogger(__name__)

# Blueprint für Metadaten-API erstellen
metadata_bp = Blueprint('metadata', __name__, url_prefix='/api/metadata')

# Konfigurationswerte
CROSSREF_API_BASE_URL = "https://api.crossref.org/works"
CROSSREF_EMAIL = os.environ.get('CROSSREF_EMAIL', 'your.email@example.com')

# Rate-Limiting - max. 1 Anfrage alle 2 Sekunden an CrossRef
last_crossref_request = 0

def respect_rate_limit():
    """Einfaches Rate-Limiting für CrossRef API"""
    global last_crossref_request
    current_time = time.time()
    time_since_last = current_time - last_crossref_request
    
    if time_since_last < 2.0:  # Mindestens 2 Sekunden zwischen Anfragen
        time.sleep(2.0 - time_since_last)
    
    last_crossref_request = time.time()

def fetch_metadata_from_crossref(doi):
    """
    Metadaten von CrossRef abrufen
    
    Args:
        doi (str): Der Digital Object Identifier
        
    Returns:
        dict: Metadaten oder None bei Fehler
    """
    if not doi:
        return None
    
    try:
        respect_rate_limit()
        
        url = f"{CROSSREF_API_BASE_URL}/{quote(doi, safe='')}"
        headers = {
            "User-Agent": f"SciLit2.0/1.0 ({CROSSREF_EMAIL})"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json().get('message')
            
        return None
    except Exception as e:
        logger.error(f"Error fetching CrossRef metadata: {e}")
        return None

@metadata_bp.route('/doi/<path:doi>', methods=['GET'])
def get_doi_metadata(doi):
    """DOI-Metadaten von CrossRef abrufen"""
    try:
        # DOI validieren
        if not doi or not doi.startswith('10.'):
            return jsonify({'error': 'Invalid DOI. DOIs start with "10."'}), 400
        
        # Metadaten abrufen
        crossref_metadata = fetch_metadata_from_crossref(doi)
        if not crossref_metadata:
            return jsonify({"error": "DOI not found"}), 404
            
        # Metadaten formatieren mit zentralisierter Funktion
        metadata = format_crossref_metadata(crossref_metadata)
        
        if metadata:
            return jsonify(metadata)
        else:
            return jsonify({"error": "Failed to format metadata"}), 500
            
    except Exception as e:
        logger.error(f"Error retrieving DOI metadata: {e}")
        return jsonify({"error": str(e)}), 500

@metadata_bp.route('/isbn/<isbn>', methods=['GET'])
def get_isbn_metadata(isbn):
    """ISBN-Metadaten abrufen"""
    try:
        # ISBN normalisieren
        clean_isbn = isbn.replace('-', '').replace(' ', '')
        
        if not clean_isbn or len(clean_isbn) not in [10, 13]:
            return jsonify({'error': 'Invalid ISBN. ISBN must be 10 or 13 digits.'}), 400
        
        # Keine Ergebnisse
        return jsonify({'error': f'No metadata found for ISBN {isbn}'}), 404
            
    except Exception as e:
        logger.error(f"Error retrieving ISBN metadata: {e}")
        return jsonify({"error": str(e)}), 500

@metadata_bp.route('/search', methods=['GET'])
def search_metadata():
    """
    Suche nach Metadaten mit Freitextsuche
    """
    query = request.args.get('q', '')
    
    if not query or len(query) < 3:
        return jsonify({'error': 'Search query must be at least 3 characters'}), 400
    
    try:
        respect_rate_limit()
        
        # CrossRef-Suche
        url = f"{CROSSREF_API_BASE_URL}?query={quote(query)}&rows=5"
        
        headers = {
            'User-Agent': f'SciLit2.0/1.0 ({CROSSREF_EMAIL})',
        }
        
        logger.info(f"CrossRef search for: {query}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return jsonify({'error': 'Error searching CrossRef'}), 500
        
        data = response.json()
        
        results = []
        if 'message' in data and 'items' in data['message']:
            for item in data['message']['items']:
                # Verwende zentralisierte Formatierungsfunktion
                formatted = format_crossref_metadata(item)
                if formatted:
                    results.append(formatted)
        
        return jsonify({'results': results, 'count': len(results)})
    
    except Exception as e:
        logger.error(f"Error in metadata search: {e}")
        return jsonify({'error': f'Search error: {str(e)}'}), 500

@metadata_bp.route('/citation-styles', methods=['GET'])
def get_citation_styles():
    """
    Verfügbare Zitationsstile abrufen
    """
    styles = [
        {"id": "apa", "name": "APA 7th Edition"},
        {"id": "chicago", "name": "Chicago 18th Edition"},
        {"id": "harvard", "name": "Harvard"}
    ]
    
    return jsonify(styles)