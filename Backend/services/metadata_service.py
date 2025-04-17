# metadata_service.py:

import logging
import requests
from crossref.restful import Works

# Import refactored utility modules
from utils.identifier_utils import extract_identifiers

# Configure logging
logger = logging.getLogger(__name__)

class MetadataService:
    """Service for extracting and fetching document metadata"""
    
    def __init__(self):
        # Initialize CrossRef client
        self.crossref = Works()
    
    def extract_identifiers(self, text):
        """
        Extract DOI and ISBN from text
        
        Args:
            text: Text to analyze
            
        Returns:
            dict: Dictionary containing DOI and ISBN
        """
        # Use the refactored central function instead of local implementation
        return extract_identifiers(text)
    
    def fetch_metadata(self, identifiers):
        """Fetch metadata from CrossRef and other sources"""
        # Initialize empty metadata
        metadata = {
            'title': '',
            'authors': '',
            'year': '',
            'journal': '',
            'volume': '',
            'issue': '',
            'pages': '',
            'publisher': '',
            'doi': identifiers.get('doi', ''),
            'isbn': identifiers.get('isbn', ''),
            'abstract': '',
            'keywords': '',
        }
        
        # Try to fetch from CrossRef if DOI is available
        if identifiers.get('doi'):
            crossref_metadata = self._fetch_from_crossref_by_doi(identifiers['doi'])
            if crossref_metadata:
                metadata.update(crossref_metadata)
        
        # If no metadata from DOI or metadata is incomplete, try ISBN
        if (not metadata['title'] or not metadata['authors']) and identifiers.get('isbn'):
            isbn_metadata = self._fetch_from_isbn(identifiers['isbn'])
            if isbn_metadata:
                metadata.update(isbn_metadata)