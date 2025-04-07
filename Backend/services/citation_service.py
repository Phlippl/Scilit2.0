# Backend/services/citation_service.py
import logging
import json
from datetime import datetime
import re
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

class CitationService:
    """Service for generating properly formatted citations"""
    
    @staticmethod
    def format_citation(document: Dict[str, Any], style: str = 'apa') -> Optional[str]:
        """
        Format a citation in the specified style
        
        Args:
            document: Document metadata
            style: Citation style ('apa', 'chicago', 'harvard')
        
        Returns:
            str: Formatted citation or None if insufficient data
        """
        try:
            if not document:
                return None
            
            # Check for minimal required data
            if not document.get('title'):
                return None
            
            # Prepare authors
            authors = CitationService.prepare_authors(document.get('authors', []))
            
            # Extract year
            year = CitationService.extract_year(document.get('publicationDate', ''))
            
            # Determine document type
            document_type = document.get('type', '').lower()
            if not document_type:
                # Infer type from available metadata
                if document.get('journal'):
                    document_type = 'article'
                elif document.get('isbn'):
                    document_type = 'book'
                else:
                    document_type = 'other'
            
            # Format according to style
            if style.lower() == 'apa':
                return CitationService.format_apa_citation(document, authors, year, document_type)
            elif style.lower() == 'chicago':
                return CitationService.format_chicago_citation(document, authors, year, document_type)
            elif style.lower() == 'harvard':
                return CitationService.format_harvard_citation(document, authors, year, document_type)
            else:
                # Default to APA
                return CitationService.format_apa_citation(document, authors, year, document_type)
        
        except Exception as e:
            logger.error(f"Error formatting citation: {e}")
            return None
    
    @staticmethod
    def prepare_authors(authors_data: Union[List[Dict[str, str]], List[str], str]) -> List[Dict[str, str]]:
        """
        Prepare authors in a standardized format
        
        Args:
            authors_data: Author data in various formats
            
        Returns:
            list: Standardized author list
        """
        authors = []
        
        try:
            # Handle string JSON
            if isinstance(authors_data, str):
                try:
                    authors_data = json.loads(authors_data)
                except json.JSONDecodeError:
                    # Simple string, treat as single author
                    return [{"name": authors_data}]
            
            # Handle list of dictionaries
            if isinstance(authors_data, list):
                for author in authors_data:
                    if isinstance(author, dict):
                        if 'name' in author:
                            authors.append({"name": author['name']})
                        elif 'given' in author and 'family' in author:
                            # Handle CrossRef format
                            authors.append({
                                "name": f"{author['family']}, {author['given']}"
                            })
                    elif isinstance(author, str):
                        authors.append({"name": author})
            
            return authors
        except Exception as e:
            logger.error(f"Error preparing authors: {e}")
            return []
    
    @staticmethod
    def extract_year(date_str: str) -> str:
        """Extract year from date string"""
        if not date_str:
            return "n.d."  # no date
        
        try:
            # YYYY-MM-DD format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                return date_str[:4]
            # Year only
            elif re.match(r'^\d{4}$', date_str):
                return date_str
            # Extract year from any string containing a year
            else:
                year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
                if year_match:
                    return year_match.group(0)
                else:
                    return "n.d."
        except Exception:
            return "n.d."
    
    @staticmethod
    def format_apa_citation(document: Dict[str, Any], authors: List[Dict[str, str]], year: str, doc_type: str) -> str:
        """
        Format citation in APA style (7th edition)
        """
        try:
            title = document.get('title', '')
            
            # Format author list
            author_text = CitationService.format_authors_apa(authors)
            
            if doc_type == 'article':
                # Journal article
                journal = document.get('journal', '')
                volume = document.get('volume', '')
                issue = document.get('issue', '')
                pages = document.get('pages', '')
                doi = document.get('doi', '')
                
                # Journal, volume and issue
                journal_info = journal
                if volume:
                    journal_info += f", {volume}"
                    if issue:
                        journal_info += f"({issue})"
                
                # Page range
                if pages:
                    journal_info += f", {pages}"
                
                # DOI
                doi_text = f" https://doi.org/{doi}" if doi else ""
                
                return f"{author_text} ({year}). {title}. {journal_info}.{doi_text}"
            
            elif doc_type in ['book', 'edited_book']:
                # Book
                publisher = document.get('publisher', '')
                publisher_location = document.get('publisherLocation', '')
                
                # Publisher info
                publisher_info = ''
                if publisher_location and publisher:
                    publisher_info = f"{publisher_location}: {publisher}"
                elif publisher:
                    publisher_info = publisher
                
                return f"{author_text} ({year}). {title}. {publisher_info}."
            
            elif doc_type == 'conference':
                # Conference paper
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
                # Thesis
                university = document.get('university', '')
                thesis_type = document.get('thesisType', 'Dissertation')
                
                return f"{author_text} ({year}). {title} [{thesis_type}]. {university}."
            
            else:
                # Generic citation for other document types
                publisher = document.get('publisher', '')
                return f"{author_text} ({year}). {title}. {publisher}."
        
        except Exception as e:
            logger.error(f"Error formatting APA citation: {e}")
            return f"{CitationService.format_authors_fallback(authors)} ({year}). {document.get('title', '')}."
    
    @staticmethod
    def format_chicago_citation(document: Dict[str, Any], authors: List[Dict[str, str]], year: str, doc_type: str) -> str:
        """
        Format citation in Chicago style (18th edition)
        """
        try:
            title = document.get('title', '')
            
            # Format author list
            author_text = CitationService.format_authors_chicago(authors)
            
            if doc_type == 'article':
                # Journal article
                journal = document.get('journal', '')
                volume = document.get('volume', '')
                issue = document.get('issue', '')
                pages = document.get('pages', '')
                
                # Journal, volume and issue
                journal_info = f'"{title}." {journal}'
                if volume:
                    journal_info += f" {volume}"
                    if issue:
                        journal_info += f", no. {issue}"
                
                # Page range
                if pages:
                    journal_info += f" ({year}): {pages}"
                else:
                    journal_info += f" ({year})"
                
                return f"{author_text}. {journal_info}."
            
            elif doc_type in ['book', 'edited_book']:
                # Book
                publisher = document.get('publisher', '')
                publisher_location = document.get('publisherLocation', '')
                
                # Publisher info
                publisher_info = ''
                if publisher_location and publisher:
                    publisher_info = f"{publisher_location}: {publisher}, {year}"
                elif publisher:
                    publisher_info = f"{publisher}, {year}"
                else:
                    publisher_info = year
                
                return f"{author_text}. {title}. {publisher_info}."
            
            elif doc_type == 'conference':
                # Conference paper
                conference = document.get('conference', '')
                publisher = document.get('publisher', '')
                
                return f"{author_text}. \"{title}.\" Paper presented at {conference}, {year}."
            
            elif doc_type == 'thesis':
                # Thesis
                university = document.get('university', '')
                thesis_type = document.get('thesisType', 'PhD diss.')
                
                return f"{author_text}. \"{title}.\" {thesis_type}, {university}, {year}."
            
            else:
                # Generic citation for other document types
                publisher = document.get('publisher', '')
                return f"{author_text}. {title}. {publisher}, {year}."
        
        except Exception as e:
            logger.error(f"Error formatting Chicago citation: {e}")
            return f"{CitationService.format_authors_fallback(authors)}. \"{document.get('title', '')}.\" {year}."
    
    @staticmethod
    def format_harvard_citation(document: Dict[str, Any], authors: List[Dict[str, str]], year: str, doc_type: str) -> str:
        """
        Format citation in Harvard style
        """
        try:
            title = document.get('title', '')
            
            # Format author list
            author_text = CitationService.format_authors_harvard(authors)
            
            if doc_type == 'article':
                # Journal article
                journal = document.get('journal', '')
                volume = document.get('volume', '')
                issue = document.get('issue', '')
                pages = document.get('pages', '')
                
                # Journal, volume and issue
                journal_info = journal
                if volume:
                    journal_info += f", {volume}"
                    if issue:
                        journal_info += f"({issue})"
                
                # Page range
                if pages:
                    journal_info += f", pp. {pages}"
                
                return f"{author_text} {year}, '{title}', {journal_info}."
            
            elif doc_type in ['book', 'edited_book']:
                # Book
                publisher = document.get('publisher', '')
                publisher_location = document.get('publisherLocation', '')
                
                # Publisher info
                publisher_info = ''
                if publisher_location and publisher:
                    publisher_info = f"{publisher}, {publisher_location}"
                elif publisher:
                    publisher_info = publisher
                
                return f"{author_text} {year}, {title}, {publisher_info}."
            
            elif doc_type == 'conference':
                # Conference paper
                conference = document.get('conference', '')
                publisher = document.get('publisher', '')
                
                return f"{author_text} {year}, '{title}', {conference}, {publisher}."
            
            elif doc_type == 'thesis':
                # Thesis
                university = document.get('university', '')
                thesis_type = document.get('thesisType', 'PhD thesis')
                
                return f"{author_text} {year}, '{title}', {thesis_type}, {university}."
            
            else:
                # Generic citation for other document types
                publisher = document.get('publisher', '')
                return f"{author_text} {year}, {title}, {publisher}."
        
        except Exception as e:
            logger.error(f"Error formatting Harvard citation: {e}")
            return f"{CitationService.format_authors_fallback(authors)} {year}, '{document.get('title', '')}'."
    
    @staticmethod
    def format_authors_apa(authors: List[Dict[str, str]]) -> str:
        """Format authors in APA style"""
        if not authors or len(authors) == 0:
            return "Unknown Author"
        
        if len(authors) == 1:
            # Single author: Last Name, Initials
            return CitationService.format_author_name_apa(authors[0])
        
        elif len(authors) == 2:
            # Two authors: Author1 & Author2
            author1 = CitationService.format_author_name_apa(authors[0])
            author2 = CitationService.format_author_name_apa(authors[1])
            return f"{author1} & {author2}"
        
        elif len(authors) <= 7:
            # Up to 7 authors: Author1, Author2, Author3, ..., & LastAuthor
            authors_text = [CitationService.format_author_name_apa(author) for author in authors[:-1]]
            last_author = CitationService.format_author_name_apa(authors[-1])
            return f"{', '.join(authors_text)}, & {last_author}"
        
        else:
            # More than 7 authors: First 6 authors, ..., LastAuthor
            authors_text = [CitationService.format_author_name_apa(author) for author in authors[:6]]
            last_author = CitationService.format_author_name_apa(authors[-1])
            return f"{', '.join(authors_text)}, ... & {last_author}"
    
    @staticmethod
    def format_author_name_apa(author: Dict[str, str]) -> str:
        """Format a single author in APA style"""
        name = author.get('name', '')
        
        if ',' in name:
            # Name is already in "Last Name, First Name" format
            parts = name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
            # Create initials
            initials = "".join([f"{n[0]}." for n in first_name.split() if n])
            return f"{last_name}, {initials}"
        else:
            # Try to split into first and last name
            parts = name.split()
            if len(parts) > 1:
                last_name = parts[-1]
                first_names = parts[:-1]
                initials = "".join([f"{n[0]}." for n in first_names if n])
                return f"{last_name}, {initials}"
            else:
                return name
    
    @staticmethod
    def format_authors_chicago(authors: List[Dict[str, str]]) -> str:
        """Format authors in Chicago style"""
        if not authors or len(authors) == 0:
            return "Unknown Author"
        
        if len(authors) == 1:
            # Single author: Last Name, First Name
            return CitationService.format_author_name_chicago(authors[0])
        
        elif len(authors) <= 3:
            # Up to three authors: full names, in order of appearance
            authors_text = [CitationService.format_author_name_chicago(author) for author in authors]
            return ", ".join(authors_text)
        
        else:
            # More than three authors: First author + "et al."
            first_author = CitationService.format_author_name_chicago(authors[0])
            return f"{first_author} et al."
    
    @staticmethod
    def format_author_name_chicago(author: Dict[str, str]) -> str:
        """Format a single author in Chicago style"""
        name = author.get('name', '')
        
        if ',' in name:
            # Name is already in "Last Name, First Name" format
            return name
        else:
            # Try to split into first and last name
            parts = name.split()
            if len(parts) > 1:
                last_name = parts[-1]
                first_names = " ".join(parts[:-1])
                return f"{last_name}, {first_names}"
            else:
                return name
    
    @staticmethod
    def format_authors_harvard(authors: List[Dict[str, str]]) -> str:
        """Format authors in Harvard style"""
        if not authors or len(authors) == 0:
            return "Anon."
        
        if len(authors) == 1:
            # Single author: Last Name, Initials
            return CitationService.format_author_name_harvard(authors[0])
        
        elif len(authors) == 2:
            # Two authors: Author1 & Author2
            author1 = CitationService.format_author_name_harvard(authors[0])
            author2 = CitationService.format_author_name_harvard(authors[1])
            return f"{author1} & {author2}"
        
        elif len(authors) <= 4:
            # Up to four authors: Author1, Author2, Author3 & Author4
            authors_text = [CitationService.format_author_name_harvard(author) for author in authors[:-1]]
            last_author = CitationService.format_author_name_harvard(authors[-1])
            return f"{', '.join(authors_text)} & {last_author}"
        
        else:
            # More than four authors: First author + "et al."
            first_author = CitationService.format_author_name_harvard(authors[0])
            return f"{first_author} et al."
    
    @staticmethod
    def format_author_name_harvard(author: Dict[str, str]) -> str:
        """Format a single author in Harvard style"""
        name = author.get('name', '')
        
        if ',' in name:
            # Name is already in "Last Name, First Name" format
            parts = name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
            # Create initials
            initials = " ".join([f"{n[0]}." for n in first_name.split() if n])
            return f"{last_name}, {initials}"
        else:
            # Try to split into first and last name
            parts = name.split()
            if len(parts) > 1:
                last_name = parts[-1]
                first_names = parts[:-1]
                initials = " ".join([f"{n[0]}." for n in first_names if n])
                return f"{last_name}, {initials}"
            else:
                return name
    
    @staticmethod
    def format_authors_fallback(authors: List[Dict[str, str]]) -> str:
        """Simple fallback formatting for authors"""
        if not authors or len(authors) == 0:
            return "Unknown Author"
        
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
            return "Unknown Author"


# Function-based version for backwards compatibility
def format_citation(document, style='apa'):
    """Legacy function interface for backwards compatibility"""
    return CitationService.format_citation(document, style)