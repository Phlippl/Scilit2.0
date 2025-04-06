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

# Logger einrichten
logger = logging.getLogger(__name__)

# Blueprint für Metadaten-API erstellen
metadata_bp = Blueprint('metadata', __name__, url_prefix='/api/metadata')

# Konfigurationswerte
CROSSREF_API_BASE_URL = "https://api.crossref.org/works"
CROSSREF_EMAIL = os.environ.get('CROSSREF_EMAIL', 'your.email@example.com')
OPENLIBRARY_API_BASE_URL = "https://openlibrary.org/api"
GOOGLE_BOOKS_API_BASE_URL = "https://www.googleapis.com/books/v1/volumes"

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
            
        # Metadaten formatieren
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
        
        # 1. Versuch: OpenLibrary
        openlibrary_result = search_isbn_openlibrary(clean_isbn)
        if openlibrary_result:
            return jsonify(openlibrary_result)
        
        # 2. Versuch: Google Books
        google_result = search_isbn_google_books(clean_isbn)
        if google_result:
            return jsonify(google_result)
        
        # Keine Ergebnisse
        return jsonify({'error': f'No metadata found for ISBN {isbn}'}), 404
            
    except Exception as e:
        logger.error(f"Error retrieving ISBN metadata: {e}")
        return jsonify({"error": str(e)}), 500

def search_isbn_openlibrary(isbn):
    """ISBN in Open Library suchen"""
    try:
        url = f"{OPENLIBRARY_API_BASE_URL}/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        
        logger.info(f"OpenLibrary search for ISBN: {isbn}")
        response = requests.get(url)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        key = f"ISBN:{isbn}"
        
        if key in data:
            book_data = data[key]
            
            # Autoren extrahieren
            authors = []
            if 'authors' in book_data:
                for author in book_data['authors']:
                    name = author.get('name', '')
                    # Name im Format "Nachname, Vorname" umwandeln, wenn möglich
                    name_parts = name.split(' ')
                    if len(name_parts) > 1:
                        formatted_name = f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
                        authors.append({'name': formatted_name})
                    else:
                        authors.append({'name': name})
            
            # Verlag und Jahr extrahieren
            publisher = ''
            publicationDate = ''
            if 'publishers' in book_data and len(book_data['publishers']) > 0:
                publisher = book_data['publishers'][0].get('name', '')
            
            if 'publish_date' in book_data:
                publicationDate = book_data['publish_date']
            
            return {
                'title': book_data.get('title', ''),
                'authors': authors,
                'publisher': publisher,
                'publicationDate': publicationDate,
                'isbn': isbn,
                'type': 'book',
                'subtitle': book_data.get('subtitle', ''),
                'abstract': book_data.get('notes', '')
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error in OpenLibrary ISBN search: {e}")
        return None

def search_isbn_google_books(isbn):
    """ISBN in Google Books suchen"""
    try:
        url = f"{GOOGLE_BOOKS_API_BASE_URL}?q=isbn:{isbn}"
        
        logger.info(f"Google Books search for ISBN: {isbn}")
        response = requests.get(url)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            book = data['items'][0]['volumeInfo']
            
            # Autoren extrahieren
            authors = []
            if 'authors' in book:
                for author_name in book['authors']:
                    # Name im Format "Nachname, Vorname" umwandeln, wenn möglich
                    name_parts = author_name.split(' ')
                    if len(name_parts) > 1:
                        formatted_name = f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
                        authors.append({'name': formatted_name})
                    else:
                        authors.append({'name': author_name})
            
            return {
                'title': book.get('title', ''),
                'authors': authors,
                'publisher': book.get('publisher', ''),
                'publicationDate': book.get('publishedDate', ''),
                'isbn': isbn,
                'type': 'book',
                'subtitle': book.get('subtitle', ''),
                'abstract': book.get('description', '')
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error in Google Books ISBN search: {e}")
        return None

def format_crossref_metadata(metadata):
    """CrossRef-Metadaten in einheitliches Format umwandeln"""
    if not metadata:
        return None
    
    try:
        # Grundlegende Informationen extrahieren
        title = ""
        if 'title' in metadata:
            if isinstance(metadata['title'], list) and metadata['title']:
                title = metadata['title'][0]
            else:
                title = metadata['title']
        
        # Dokumenttyp ermitteln
        document_type = 'other'
        crossref_type = metadata.get('type', '').lower()
        
        if 'journal-article' in crossref_type:
            document_type = 'article'
        elif 'proceedings' in crossref_type:
            document_type = 'conference'
        elif any(book_type in crossref_type for book_type in ['book', 'monograph']):
            document_type = 'book'
        elif 'dissertation' in crossref_type:
            document_type = 'thesis'
        
        # Publikationsdatum extrahieren
        publication_date = ''
        if 'published' in metadata:
            date_parts = metadata['published'].get('date-parts', [[]])[0]
            if date_parts:
                # Format als YYYY-MM-DD oder nur Jahr
                if len(date_parts) >= 3:
                    publication_date = f"{date_parts[0]}-{date_parts[1]:02d}-{date_parts[2]:02d}"
                elif len(date_parts) == 2:
                    publication_date = f"{date_parts[0]}-{date_parts[1]:02d}-01"
                elif len(date_parts) == 1:
                    publication_date = f"{date_parts[0]}-01-01"
        
        # Journal/Container-Titel extrahieren
        journal = ""
        if 'container-title' in metadata:
            if isinstance(metadata['container-title'], list) and metadata['container-title']:
                journal = metadata['container-title'][0]
            else:
                journal = metadata['container-title']
        
        # ISBN für Bücher extrahieren
        isbn = ""
        if 'ISBN' in metadata:
            if isinstance(metadata['ISBN'], list) and metadata['ISBN']:
                isbn = metadata['ISBN'][0].replace('-', '')
            else:
                isbn = metadata['ISBN'].replace('-', '')
        
        result = {
            'title': title,
            'authors': metadata.get('author', []),
            'type': document_type,
            'publicationDate': publication_date,
            'publisher': metadata.get('publisher', ''),
            'journal': journal,
            'volume': metadata.get('volume', ''),
            'issue': metadata.get('issue', ''),
            'pages': metadata.get('page', ''),
            'doi': metadata.get('DOI', ''),
            'isbn': isbn,
            'abstract': metadata.get('abstract', '')
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting CrossRef metadata: {e}")
        return None

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