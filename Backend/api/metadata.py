# Backend/api/metadata.py
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


@metadata_bp.route('/doi/<path:doi>', methods=['GET'])
def get_doi_metadata(doi):
    """DOI-Metadaten von CrossRef abrufen"""
    try:
        # DOI validieren
        if not doi or not doi.startswith('10.'):
            return jsonify({'error': 'Ungültige DOI. DOIs beginnen mit "10."'}), 400
        
        # Rate-Limiting einhalten
        respect_rate_limit()
        
        # URL-kodierte DOI für API-Aufruf
        encoded_doi = quote(doi, safe='')
        url = f"{CROSSREF_API_BASE_URL}/{encoded_doi}"
        
        # Anfrage mit User-Agent und E-Mail (gute Praxis bei CrossRef)
        headers = {
            'User-Agent': f'SciLit2.0/1.0 ({CROSSREF_EMAIL})',
        }
        
        logger.info(f"CrossRef-Anfrage für DOI: {doi}")
        response = requests.get(url, headers=headers)
        
        # Fehler überprüfen
        if response.status_code == 404:
            logger.warning(f"DOI nicht gefunden: {doi}")
            return jsonify({'error': 'DOI nicht gefunden'}), 404
        
        response.raise_for_status()
        crossref_data = response.json()
        
        # Metadaten formatieren
        if 'message' in crossref_data:
            metadata = format_crossref_metadata(crossref_data['message'])
            return jsonify(metadata)
        else:
            return jsonify({'error': 'Unerwartetes Antwortformat von CrossRef'}), 500
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Fehler bei CrossRef-Anfrage: {str(e)}")
        return jsonify({'error': f'CrossRef API-Fehler: {str(e)}'}), 500
    
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei DOI-Metadatenabfrage: {str(e)}")
        return jsonify({'error': f'Fehler bei Metadatenverarbeitung: {str(e)}'}), 500


@metadata_bp.route('/isbn/<isbn>', methods=['GET'])
def get_isbn_metadata(isbn):
    """ISBN-Metadaten abrufen, zunächst von CrossRef, bei Misserfolg von OpenLibrary/Google Books"""
    try:
        # ISBN normalisieren (Bindestriche und Leerzeichen entfernen)
        isbn = isbn.replace('-', '').replace(' ', '')
        
        if not isbn or len(isbn) not in [10, 13]:
            return jsonify({'error': 'Ungültige ISBN. ISBN muss 10 oder 13 Zeichen haben.'}), 400
        
        # 1. Versuch: CrossRef
        crossref_result = search_isbn_crossref(isbn)
        if crossref_result:
            return jsonify(crossref_result)
        
        # 2. Versuch: OpenLibrary
        openlibrary_result = search_isbn_openlibrary(isbn)
        if openlibrary_result:
            return jsonify(openlibrary_result)
        
        # 3. Versuch: Google Books
        google_result = search_isbn_google_books(isbn)
        if google_result:
            return jsonify(google_result)
        
        # Keine Ergebnisse
        return jsonify({'error': f'Keine Metadaten für ISBN {isbn} gefunden'}), 404
    
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei ISBN-Metadatenabfrage: {str(e)}")
        return jsonify({'error': f'Fehler bei Metadatenverarbeitung: {str(e)}'}), 500


def search_isbn_crossref(isbn):
    """ISBN in CrossRef suchen"""
    try:
        respect_rate_limit()
        
        # CrossRef-Suche nach ISBN
        url = f"{CROSSREF_API_BASE_URL}?query={isbn}&filter=type:book&rows=1"
        
        headers = {
            'User-Agent': f'SciLit2.0/1.0 ({CROSSREF_EMAIL})',
        }
        
        logger.info(f"CrossRef-Suche nach ISBN: {isbn}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"CrossRef ISBN-Suche fehlgeschlagen: {response.status_code}")
            return None
        
        data = response.json()
        
        if 'message' in data and 'items' in data['message'] and len(data['message']['items']) > 0:
            # Erstes Ergebnis nehmen
            item = data['message']['items'][0]
            
            # ISBN überprüfen
            if 'ISBN' in item and isinstance(item['ISBN'], list) and isbn in [i.replace('-', '') for i in item['ISBN']]:
                return format_crossref_metadata(item)
        
        return None
    
    except Exception as e:
        logger.error(f"Fehler bei CrossRef ISBN-Suche: {str(e)}")
        return None


def search_isbn_openlibrary(isbn):
    """ISBN in Open Library suchen"""
    try:
        url = f"{OPENLIBRARY_API_BASE_URL}/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        
        logger.info(f"OpenLibrary-Suche nach ISBN: {isbn}")
        response = requests.get(url)
        
        if response.status_code != 200:
            logger.warning(f"OpenLibrary ISBN-Suche fehlgeschlagen: {response.status_code}")
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
            publication_date = ''
            if 'publishers' in book_data and len(book_data['publishers']) > 0:
                publisher = book_data['publishers'][0].get('name', '')
            
            if 'publish_date' in book_data:
                publication_date = book_data['publish_date']
                # Wenn nur Jahr vorhanden, ISO-Format verwenden
                if len(publication_date) == 4 and publication_date.isdigit():
                    publication_date = f"{publication_date}-01-01"
            
            return {
                'title': book_data.get('title', ''),
                'authors': authors,
                'publisher': publisher,
                'publicationDate': publication_date,
                'isbn': isbn,
                'type': 'book',
                'subtitle': book_data.get('subtitle', ''),
                'abstract': book_data.get('notes', '')
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Fehler bei OpenLibrary ISBN-Suche: {str(e)}")
        return None


def search_isbn_google_books(isbn):
    """ISBN in Google Books suchen"""
    try:
        url = f"{GOOGLE_BOOKS_API_BASE_URL}?q=isbn:{isbn}"
        
        logger.info(f"Google Books-Suche nach ISBN: {isbn}")
        response = requests.get(url)
        
        if response.status_code != 200:
            logger.warning(f"Google Books ISBN-Suche fehlgeschlagen: {response.status_code}")
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
            
            # Erscheinungsdatum extrahieren
            publication_date = book.get('publishedDate', '')
            # Wenn nur Jahr vorhanden, ISO-Format verwenden
            if len(publication_date) == 4 and publication_date.isdigit():
                publication_date = f"{publication_date}-01-01"
            
            return {
                'title': book.get('title', ''),
                'authors': authors,
                'publisher': book.get('publisher', ''),
                'publicationDate': publication_date,
                'isbn': isbn,
                'type': 'book',
                'subtitle': book.get('subtitle', ''),
                'abstract': book.get('description', '')
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Fehler bei Google Books ISBN-Suche: {str(e)}")
        return None


def format_crossref_metadata(metadata):
    """CrossRef-Metadaten in einheitliches Format umwandeln"""
    if not metadata:
        return None
    
    try:
        # Grundlegende Informationen extrahieren
        result = {
            'title': metadata['title'][0] if 'title' in metadata and metadata['title'] else '',
            'doi': metadata.get('DOI', ''),
            'url': metadata.get('URL', ''),
            'type': determine_document_type(metadata),
            'publicationDate': '',
            'authors': [],
            'journal': metadata['container-title'][0] if 'container-title' in metadata and metadata['container-title'] else '',
            'volume': metadata.get('volume', ''),
            'issue': metadata.get('issue', ''),
            'pages': metadata.get('page', ''),
            'publisher': metadata.get('publisher', ''),
            'abstract': metadata.get('abstract', ''),
            'isbn': '',
            'issn': '',
            'subtitle': '', 
            'edition': '',
            'publisherLocation': '',
            'series': '',
            'seriesNumber': '',
        }
        
        # Autoren extrahieren
        if 'author' in metadata and isinstance(metadata['author'], list):
            for author in metadata['author']:
                author_info = {
                    'given': author.get('given', ''),
                    'family': author.get('family', ''),
                    'name': '',
                    'orcid': author.get('ORCID', '')
                }
                
                # Vollständigen Namen im Format "Nachname, Vorname" generieren
                if author.get('family') and author.get('given'):
                    author_info['name'] = f"{author['family']}, {author['given']}"
                elif author.get('name'):
                    author_info['name'] = author['name']
                else:
                    name_parts = []
                    if author.get('family'):
                        name_parts.append(author['family'])
                    if author.get('given'):
                        name_parts.append(author['given'])
                    author_info['name'] = ", ".join(name_parts)
                
                result['authors'].append(author_info)
        
        # Publikationsdatum extrahieren
        if 'published' in metadata:
            date_parts = metadata['published'].get('date-parts', [[]])[0]
            if date_parts:
                # Format als YYYY-MM-DD oder Teildatum
                result['publicationDate'] = '-'.join(str(part) for part in date_parts)
                
                # Wenn nur das Jahr angegeben ist, ein vollständiges Datum erstellen
                if len(date_parts) == 1:
                    result['publicationDate'] = f"{date_parts[0]}-01-01"
        
        # ISBN für Bücher extrahieren
        if 'ISBN' in metadata and isinstance(metadata['ISBN'], list) and metadata['ISBN']:
            result['isbn'] = metadata['ISBN'][0]
        
        # ISSN für Zeitschriften extrahieren
        if 'ISSN' in metadata and isinstance(metadata['ISSN'], list) and metadata['ISSN']:
            result['issn'] = metadata['ISSN'][0]
        
        # Sonstige Felder
        if 'subtitle' in metadata and metadata['subtitle']:
            result['subtitle'] = metadata['subtitle'][0]
        
        return result
    
    except Exception as e:
        logger.error(f"Fehler beim Formatieren der CrossRef-Metadaten: {str(e)}")
        return None


def determine_document_type(metadata):
    """Dokumenttyp basierend auf CrossRef-Metadaten bestimmen"""
    if not metadata:
        return 'other'
    
    crossref_type = metadata.get('type', '').lower()
    
    # Mapping von CrossRef-Typen zu unseren Dokumenttypen
    type_mapping = {
        'journal-article': 'article',
        'proceedings-article': 'conference',
        'book': 'book',
        'book-chapter': 'book',
        'edited-book': 'edited_book',
        'monograph': 'book',
        'reference-book': 'book',
        'dissertation': 'thesis',
        'report': 'report',
        'journal': 'article',
        'journal-issue': 'article',
        'journal-volume': 'article'
    }
    
    return type_mapping.get(crossref_type, 'other')


@metadata_bp.route('/search', methods=['GET'])
def search_metadata():
    """Suche nach Metadaten mit Freitextsuche"""
    query = request.args.get('q', '')
    
    if not query or len(query) < 3:
        return jsonify({'error': 'Suchbegriff muss mindestens 3 Zeichen haben'}), 400
    
    try:
        respect_rate_limit()
        
        # CrossRef-Suche
        url = f"{CROSSREF_API_BASE_URL}?query={quote(query)}&rows=5"
        
        headers = {
            'User-Agent': f'SciLit2.0/1.0 ({CROSSREF_EMAIL})',
        }
        
        logger.info(f"CrossRef-Suche nach: {query}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return jsonify({'error': 'Fehler bei CrossRef-Suche'}), 500
        
        data = response.json()
        
        results = []
        if 'message' in data and 'items' in data['message']:
            for item in data['message']['items']:
                formatted = format_crossref_metadata(item)
                if formatted:
                    results.append(formatted)
        
        return jsonify({'results': results, 'count': len(results)})
    
    except Exception as e:
        logger.error(f"Fehler bei Metadaten-Suche: {str(e)}")
        return jsonify({'error': f'Fehler bei Suche: {str(e)}'}), 500