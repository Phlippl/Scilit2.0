// src/api/metadata.js
import apiClient from './client';

const API_URL = '/api/metadata';

// Configuration for direct CrossRef access
const CROSSREF_API_BASE_URL = 'https://api.crossref.org';
const CROSSREF_EMAIL = import.meta.env.VITE_CROSSREF_EMAIL || 'your.email@example.com';

/**
 * Fetches metadata using a DOI
 * 
 * @param {string} doi - Digital Object Identifier
 * @returns {Promise<Object>} - Promise with metadata
 */
export const fetchDOIMetadata = async (doi) => {
  try {
    console.log(`Fetching DOI metadata for: ${doi}`);
    
    // Try direct CrossRef access without backend
    const crossrefData = await fetchDOIMetadataFromCrossRef(doi);
    if (crossrefData) {
      return formatCrossRefMetadata(crossrefData);
    }
    
    // If direct access doesn't work, try via the backend
    try {
      const response = await apiClient.get(`${API_URL}/doi/${encodeURIComponent(doi)}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching DOI metadata from backend:', error);
      // Pass through error from direct access if both fail
      throw { message: 'Could not retrieve DOI metadata' };
    }
  } catch (error) {
    console.error('Error fetching DOI metadata:', error);
    throw error.response?.data || { message: 'Could not retrieve DOI metadata' };
  }
};

/**
 * Fetches metadata using an ISBN
 * 
 * @param {string} isbn - International Standard Book Number
 * @returns {Promise<Object>} - Promise with metadata
 */
export const fetchISBNMetadata = async (isbn) => {
  try {
    console.log(`Fetching ISBN metadata for: ${isbn}`);
    
    // Remove hyphens and spaces for consistent format
    const cleanIsbn = isbn.replace(/[-\s]/g, '');
    
    // Try via backend
    const response = await apiClient.get(`${API_URL}/isbn/${cleanIsbn}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching ISBN metadata:', error);
    throw error.response?.data || { message: 'Could not retrieve ISBN metadata' };
  }
};

/**
 * Direct access to CrossRef for DOI metadata (fallback)
 * 
 * @param {string} doi - Digital Object Identifier
 * @returns {Promise<Object>} - Promise with metadata
 */
export const fetchDOIMetadataFromCrossRef = async (doi) => {
  if (!doi) return null;
  
  try {
    const encodedDOI = encodeURIComponent(doi);
    const url = `${CROSSREF_API_BASE_URL}/works/${encodedDOI}`;
    
    const response = await fetch(url, {
      headers: {
        'User-Agent': `SciLit2.0/1.0 (${CROSSREF_EMAIL})`,
      }
    });
    
    if (!response.ok) {
      console.warn(`CrossRef API error: ${response.status}`);
      return null;
    }
    
    const data = await response.json();
    
    if (data && data.message) {
      return data.message;
    }
    return null;
  } catch (error) {
    console.error('Error fetching DOI metadata from CrossRef:', error);
    return null;
  }
};

/**
 * Formats CrossRef metadata into a standardized format
 * 
 * @param {Object} metadata - Raw metadata from CrossRef
 * @returns {Object} - Formatted metadata
 */
export const formatCrossRefMetadata = (metadata) => {
  if (!metadata) return null;
  
  try {
    // Extract basic information
    const result = {
      title: '',
      doi: metadata.DOI || '',
      url: metadata.URL || '',
      type: 'article', // Default to article
      publicationDate: '',
      authors: [],
      journal: '',
      volume: metadata.volume || '',
      issue: metadata.issue || '',
      pages: metadata.page || '',
      publisher: metadata.publisher || '',
      abstract: metadata.abstract || '',
      isbn: '',
      issn: '',
    };
    
    // Extract title
    if (metadata.title) {
      if (Array.isArray(metadata.title) && metadata.title.length > 0) {
        result.title = metadata.title[0];
      } else {
        result.title = metadata.title;
      }
    }
    
    // Map CrossRef type to our application's types
    if (metadata.type) {
      // Map CrossRef types to our application types
      const typeMapping = {
        'journal-article': 'article',
        'book': 'book',
        'book-chapter': 'book',
        'monograph': 'book',
        'edited-book': 'edited_book',
        'proceedings-article': 'conference',
        'proceedings': 'conference',
        'conference-paper': 'conference',
        'dissertation': 'thesis',
        'report': 'report',
        'report-component': 'report',
        'journal': 'article',
        'newspaper-article': 'newspaper',
        'website': 'website',
        'peer-review': 'article',
        'standard': 'report',
        'dataset': 'other',
        'posted-content': 'other',
        'reference-entry': 'other'
      };
      
      // Use mapping if available, otherwise use default 'article' or 'other'
      result.type = typeMapping[metadata.type] || 
                   (metadata.type.includes('book') ? 'book' : 
                   (metadata.type.includes('journal') ? 'article' : 'other'));
    }
    
    // Extract journal/container title
    if (metadata['container-title']) {
      if (Array.isArray(metadata['container-title']) && metadata['container-title'].length > 0) {
        result.journal = metadata['container-title'][0];
      } else {
        result.journal = metadata['container-title'];
      }
    }
    
    // Extract authors
    if (metadata.author && Array.isArray(metadata.author)) {
      result.authors = metadata.author.map(author => ({
        given: author.given || '',
        family: author.family || '',
        name: (author.given && author.family) ? 
          `${author.family}, ${author.given}` : 
          author.name || '',
        orcid: author.ORCID || '',
      }));
    }
    
    // Extract publication date
    if (metadata.published) {
      const date = metadata.published['date-parts'] ? 
        metadata.published['date-parts'][0] : [];
      
      if (date.length >= 1) {
        // Format as YYYY-MM-DD or partial date
        if (date.length >= 3) {
          result.publicationDate = `${date[0]}-${date[1].toString().padStart(2, '0')}-${date[2].toString().padStart(2, '0')}`;
        } else if (date.length === 2) {
          result.publicationDate = `${date[0]}-${date[1].toString().padStart(2, '0')}-01`;
        } else {
          result.publicationDate = `${date[0]}-01-01`;
        }
      }
    }
    
    // Extract ISBN for books
    if (metadata.ISBN) {
      if (Array.isArray(metadata.ISBN) && metadata.ISBN.length > 0) {
        result.isbn = metadata.ISBN[0].replace(/-/g, '');
      } else {
        result.isbn = metadata.ISBN.replace(/-/g, '');
      }
    }
    
    // Extract ISSN for journals
    if (metadata.ISSN) {
      if (Array.isArray(metadata.ISSN) && metadata.ISSN.length > 0) {
        result.issn = metadata.ISSN[0];
      } else {
        result.issn = metadata.ISSN;
      }
    }
    
    console.log("Formatted metadata type:", result.type);
    return result;
  } catch (error) {
    console.error('Error formatting CrossRef metadata:', error);
    return null;
  }
};


/**
 * Search for metadata using a free text query
 * 
 * @param {string} query - Search query
 * @returns {Promise<Object>} - Search results
 */
export const searchMetadata = async (query) => {
  try {
    if (!query || query.length < 3) {
      throw new Error('Search query must be at least 3 characters');
    }
    
    const response = await apiClient.get(`${API_URL}/search`, {
      params: { q: query }
    });
    
    return response.data;
  } catch (error) {
    console.error('Error searching metadata:', error);
    throw error.response?.data || { message: 'Search failed' };
  }
};

/**
 * Gets available citation styles
 * 
 * @returns {Promise<Array>} - List of citation styles
 */
export const getCitationStyles = async () => {
  try {
    const response = await apiClient.get(`${API_URL}/citation-styles`);
    return response.data;
  } catch (error) {
    console.error('Error fetching citation styles:', error);
    // Return default styles if API fails
    return [
      { id: 'apa', name: 'APA 7th Edition' },
      { id: 'chicago', name: 'Chicago 18th Edition' },
      { id: 'harvard', name: 'Harvard' }
    ];
  }
};