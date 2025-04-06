import re
import logging
import requests
from crossref.restful import Works

# Configure logging
logger = logging.getLogger(__name__)

class MetadataService:
    """Service for extracting and fetching document metadata"""
    
    def __init__(self):
        # Initialize CrossRef client
        self.crossref = Works()
    
    def extract_identifiers(self, text):
        """Extract DOI and ISBN from text"""
        identifiers = {
            'doi': None,
            'isbn': None
        }
        
        # Extract DOI
        doi_pattern = r'(?:doi:|https?://doi\.org/|DOI:?\s*)(10\.\d{4,}(?:\.\d+)*\/(?:(?![\"&\'<>])\S)+)'
        doi_match = re.search(doi_pattern, text, re.IGNORECASE)
        if doi_match:
            identifiers['doi'] = doi_match.group(1)
        
        # Extract ISBN-10 or ISBN-13
        isbn_pattern = r'(?:ISBN(?:-1[03])?:?\s*)((?:97[89][- ]?)?(?:[0-9][- ]?){9}[0-9Xx])'
        isbn_match = re.search(isbn_pattern, text, re.IGNORECASE)
        if isbn_match:
            # Clean the ISBN by removing hyphens and spaces
            isbn = isbn_match.group(1).replace('-', '').replace(' ', '')
            identifiers['isbn'] = isbn
        
        return identifiers
    
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
