# Backend/services/citation_service.py
import logging
import json
from datetime import datetime
import re

logger = logging.getLogger(__name__)

def format_citation(document, style='apa'):
    """
    Formatiert eine Zitation im angegebenen Stil
    
    Args:
        document: Dokument-Metadaten
        style: Zitationsstil ('apa', 'chicago', 'harvard')
    
    Returns:
        str: Formatierte Zitation
    """
    try:
        if not document:
            return None
        
        # Prüfen, ob minimale Daten vorhanden sind
        if not document.get('title'):
            return None
        
        # Autoren vorbereiten
        authors = document.get('authors', [])
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except:
                authors = []
        
        # Jahr extrahieren
        publication_date = document.get('publication_date', '')
        year = ''
        if publication_date:
            # YYYY-MM-DD Format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', publication_date):
                year = publication_date[:4]
            # Nur Jahr
            elif re.match(r'^\d{4}$', publication_date):
                year = publication_date
            # Andere Formate
            else:
                try:
                    date_obj = datetime.strptime(publication_date, '%Y-%m-%d')
                    year = date_obj.strftime('%Y')
                except:
                    try:
                        # Versuche zu extrahieren
                        year_match = re.search(r'\b(19|20)\d{2}\b', publication_date)
                        if year_match:
                            year = year_match.group(0)
                    except:
                        year = ''
        
        if not year:
            year = "n.d."  # no date
        
        # Nach Dokumenttyp und Stil formatieren
        doc_type = document.get('type', 'other')
        
        if style.lower() == 'apa':
            return format_apa_citation(document, authors, year, doc_type)
        elif style.lower() == 'chicago':
            return format_chicago_citation(document, authors, year, doc_type)
        elif style.lower() == 'harvard':
            return format_harvard_citation(document, authors, year, doc_type)
        else:
            # Standardmäßig APA verwenden
            return format_apa_citation(document, authors, year, doc_type)
    
    except Exception as e:
        logger.error(f"Error formatting citation: {e}")
        return None


def format_apa_citation(document, authors, year, doc_type):
    """
    Formatiert Zitation im APA-Stil (7. Auflage)
    """
    try:
        title = document.get('title', '')
        
        # Autorenliste formatieren
        author_text = format_authors_apa(authors)
        
        if doc_type == 'article':
            # Zeitschriftenartikel
            journal = document.get('journal', '')
            volume = document.get('volume', '')
            issue = document.get('issue', '')
            pages = document.get('pages', '')
            doi = document.get('doi', '')
            
            # Journal, Volume und Issue
            journal_info = journal
            if volume:
                journal_info += f", {volume}"
                if issue:
                    journal_info += f"({issue})"
            
            # Seitenbereich
            if pages:
                journal_info += f", {pages}"
            
            # DOI
            doi_text = f" https://doi.org/{doi}" if doi else ""
            
            return f"{author_text} ({year}). {title}. {journal_info}.{doi_text}"
        
        elif doc_type in ['book', 'edited_book']:
            # Buch
            publisher = document.get('publisher', '')
            publisher_location = document.get('publisherLocation', '')
            
            # Verlagsinfo
            publisher_info = ''
            if publisher_location and publisher:
                publisher_info = f"{publisher_location}: {publisher}"
            elif publisher:
                publisher_info = publisher
            
            return f"{author_text} ({year}). {title}. {publisher_info}."
        
        elif doc_type == 'conference':
            # Konferenzpaper
            conference = document.get('conference', '')
            publisher = document.get('publisher', '')
            pages = document.get('pages', '')
            
            conference_info = conference
            if publisher:
                conference_info += f". {publisher}"
            if pages:
                conference_info += f", {pages}"
            
            return f"{author_text} ({year}). {title}. In {conference_info}."
        
        elif doc_type == 'thesis':
            # Hochschulschrift
            university = document.get('university', '')
            thesis_type = document.get('thesisType', 'Dissertation')
            
            return f"{author_text} ({year}). {title} [{thesis_type}]. {university}."
        
        else:
            # Generischer Zitierstil für andere Dokumenttypen
            publisher = document.get('publisher', '')
            return f"{author_text} ({year}). {title}. {publisher}."
    
    except Exception as e:
        logger.error(f"Error formatting APA citation: {e}")
        return f"{format_authors_fallback(authors)} ({year}). {document.get('title', '')}."


def format_chicago_citation(document, authors, year, doc_type):
    """
    Formatiert Zitation im Chicago-Stil (18. Auflage)
    """
    try:
        title = document.get('title', '')
        
        # Autorenliste formatieren
        author_text = format_authors_chicago(authors)
        
        if doc_type == 'article':
            # Zeitschriftenartikel
            journal = document.get('journal', '')
            volume = document.get('volume', '')
            issue = document.get('issue', '')
            pages = document.get('pages', '')
            
            # Journal, Volume und Issue
            journal_info = f'"{title}." {journal}'
            if volume:
                journal_info += f" {volume}"
                if issue:
                    journal_info += f", no. {issue}"
            
            # Seitenbereich
            if pages:
                journal_info += f" ({year}): {pages}"
            else:
                journal_info += f" ({year})"
            
            return f"{author_text}. {journal_info}."
        
        elif doc_type in ['book', 'edited_book']:
            # Buch
            publisher = document.get('publisher', '')
            publisher_location = document.get('publisherLocation', '')
            
            # Verlagsinfo
            publisher_info = ''
            if publisher_location and publisher:
                publisher_info = f"{publisher_location}: {publisher}, {year}"
            elif publisher:
                publisher_info = f"{publisher}, {year}"
            else:
                publisher_info = year
            
            return f"{author_text}. {title}. {publisher_info}."
        
        elif doc_type == 'conference':
            # Konferenzpaper
            conference = document.get('conference', '')
            publisher = document.get('publisher', '')
            
            return f"{author_text}. \"{title}.\" Paper presented at {conference}, {year}."
        
        elif doc_type == 'thesis':
            # Hochschulschrift
            university = document.get('university', '')
            thesis_type = document.get('thesisType', 'PhD diss.')
            
            return f"{author_text}. \"{title}.\" {thesis_type}, {university}, {year}."
        
        else:
            # Generischer Zitierstil für andere Dokumenttypen
            publisher = document.get('publisher', '')
            return f"{author_text}. {title}. {publisher}, {year}."
    
    except Exception as e:
        logger.error(f"Error formatting Chicago citation: {e}")
        return f"{format_authors_fallback(authors)}. \"{document.get('title', '')}.\" {year}."


def format_harvard_citation(document, authors, year, doc_type):
    """
    Formatiert Zitation im Harvard-Stil
    """
    try:
        title = document.get('title', '')
        
        # Autorenliste formatieren
        author_text = format_authors_harvard(authors)
        
        if doc_type == 'article':
            # Zeitschriftenartikel
            journal = document.get('journal', '')
            volume = document.get('volume', '')
            issue = document.get('issue', '')
            pages = document.get('pages', '')
            
            # Journal, Volume und Issue
            journal_info = journal
            if volume:
                journal_info += f", {volume}"
                if issue:
                    journal_info += f"({issue})"
            
            # Seitenbereich
            if pages:
                journal_info += f", pp. {pages}"
            
            return f"{author_text} {year}, '{title}', {journal_info}."
        
        elif doc_type in ['book', 'edited_book']:
            # Buch
            publisher = document.get('publisher', '')
            publisher_location = document.get('publisherLocation', '')
            
            # Verlagsinfo
            publisher_info = ''
            if publisher_location and publisher:
                publisher_info = f"{publisher}, {publisher_location}"
            elif publisher:
                publisher_info = publisher
            
            return f"{author_text} {year}, {title}, {publisher_info}."
        
        elif doc_type == 'conference':
            # Konferenzpaper
            conference = document.get('conference', '')
            publisher = document.get('publisher', '')
            
            return f"{author_text} {year}, '{title}', {conference}, {publisher}."
        
        elif doc_type == 'thesis':
            # Hochschulschrift
            university = document.get('university', '')
            thesis_type = document.get('thesisType', 'PhD thesis')
            
            return f"{author_text} {year}, '{title}', {thesis_type}, {university}."
        
        else:
            # Generischer Zitierstil für andere Dokumenttypen
            publisher = document.get('publisher', '')
            return f"{author_text} {year}, {title}, {publisher}."
    
    except Exception as e:
        logger.error(f"Error formatting Harvard citation: {e}")
        return f"{format_authors_fallback(authors)} {year}, '{document.get('title', '')}'."


def format_authors_apa(authors):
    """
    Formatiert Autoren im APA-Stil
    """
    if not authors or len(authors) == 0:
        return "Unbekannter Autor"
    
    if len(authors) == 1:
        author = authors[0]
        # Format: Nachname, Initialen
        name = author.get('name', '')
        if ',' in name:
            # Name ist bereits im Format "Nachname, Vorname"
            parts = name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
            # Initialen erstellen
            initials = "".join([f"{n[0]}." for n in first_name.split() if n])
            return f"{last_name}, {initials}"
        else:
            # Name ist nicht im erwarteten Format
            return name
    
    elif len(authors) == 2:
        # Zwei Autoren: Autor1 & Autor2
        author1 = format_author_name_apa(authors[0])
        author2 = format_author_name_apa(authors[1])
        return f"{author1} & {author2}"
    
    elif len(authors) <= 7:
        # Bis zu 7 Autoren: Autor1, Autor2, Autor3, ..., & LetztAutor
        authors_text = [format_author_name_apa(author) for author in authors[:-1]]
        last_author = format_author_name_apa(authors[-1])
        return f"{', '.join(authors_text)}, & {last_author}"
    
    else:
        # Mehr als 7 Autoren: Erste 6 Autoren, ..., LetztAutor
        authors_text = [format_author_name_apa(author) for author in authors[:6]]
        last_author = format_author_name_apa(authors[-1])
        return f"{', '.join(authors_text)}, ... & {last_author}"


def format_author_name_apa(author):
    """
    Formatiert einen einzelnen Autor im APA-Stil
    """
    name = author.get('name', '')
    
    if ',' in name:
        # Name ist bereits im Format "Nachname, Vorname"
        parts = name.split(',', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ""
        # Initialen erstellen
        initials = "".join([f"{n[0]}." for n in first_name.split() if n])
        return f"{last_name}, {initials}"
    else:
        # Versuche, Vor- und Nachnamen zu trennen
        parts = name.split()
        if len(parts) > 1:
            last_name = parts[-1]
            first_names = parts[:-1]
            initials = "".join([f"{n[0]}." for n in first_names if n])
            return f"{last_name}, {initials}"
        else:
            return name


def format_authors_chicago(authors):
    """
    Formatiert Autoren im Chicago-Stil
    """
    if not authors or len(authors) == 0:
        return "Unbekannter Autor"
    
    if len(authors) == 1:
        # Ein Autor: Nachname, Vorname
        return format_author_name_chicago(authors[0])
    
    elif len(authors) <= 3:
        # Bis zu drei Autoren: vollständige Namen, in Reihenfolge des Erscheinens
        authors_text = [format_author_name_chicago(author) for author in authors]
        return ", ".join(authors_text)
    
    else:
        # Mehr als drei Autoren: Erster Autor + "et al."
        first_author = format_author_name_chicago(authors[0])
        return f"{first_author} et al."


def format_author_name_chicago(author):
    """
    Formatiert einen einzelnen Autor im Chicago-Stil
    """
    name = author.get('name', '')
    
    if ',' in name:
        # Name ist bereits im Format "Nachname, Vorname"
        return name
    else:
        # Versuche, Vor- und Nachnamen zu trennen
        parts = name.split()
        if len(parts) > 1:
            last_name = parts[-1]
            first_names = " ".join(parts[:-1])
            return f"{last_name}, {first_names}"
        else:
            return name


def format_authors_harvard(authors):
    """
    Formatiert Autoren im Harvard-Stil
    """
    if not authors or len(authors) == 0:
        return "Anon."
    
    if len(authors) == 1:
        # Ein Autor: Nachname, Initialen
        return format_author_name_harvard(authors[0])
    
    elif len(authors) == 2:
        # Zwei Autoren: Autor1 & Autor2
        author1 = format_author_name_harvard(authors[0])
        author2 = format_author_name_harvard(authors[1])
        return f"{author1} & {author2}"
    
    elif len(authors) <= 4:
        # Bis zu vier Autoren: Autor1, Autor2, Autor3 & Autor4
        authors_text = [format_author_name_harvard(author) for author in authors[:-1]]
        last_author = format_author_name_harvard(authors[-1])
        return f"{', '.join(authors_text)} & {last_author}"
    
    else:
        # Mehr als vier Autoren: Erster Autor + "et al."
        first_author = format_author_name_harvard(authors[0])
        return f"{first_author} et al."


def format_author_name_harvard(author):
    """
    Formatiert einen einzelnen Autor im Harvard-Stil
    """
    name = author.get('name', '')
    
    if ',' in name:
        # Name ist bereits im Format "Nachname, Vorname"
        parts = name.split(',', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ""
        # Initialen erstellen
        initials = " ".join([f"{n[0]}." for n in first_name.split() if n])
        return f"{last_name}, {initials}"
    else:
        # Versuche, Vor- und Nachnamen zu trennen
        parts = name.split()
        if len(parts) > 1:
            last_name = parts[-1]
            first_names = parts[:-1]
            initials = " ".join([f"{n[0]}." for n in first_names if n])
            return f"{last_name}, {initials}"
        else:
            return name


def format_authors_fallback(authors):
    """
    Einfache Fallback-Formatierung für Autoren
    """
    if not authors or len(authors) == 0:
        return "Unbekannter Autor"
    
    author_names = []
    for author in authors:
        if isinstance(author, dict):
            author_names.append(author.get('name', ''))
        else:
            author_names.append(str(author))
    
    if len(author_names) == 1:
        return author_names[0]
    elif len(author_names) == 2:
        return f"{author_names[0]} & {author_names[1]}"
    elif len(author_names) > 2:
        return f"{author_names[0]} et al."
    else:
        return "Unbekannter Autor"