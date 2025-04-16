// src/api/metadata.js
import apiClient from './client';

const API_URL = '/api/metadata';

// Configuration for direct CrossRef access
const CROSSREF_API_BASE_URL = 'https://api.crossref.org';
const CROSSREF_EMAIL = import.meta.env.VITE_CROSSREF_EMAIL || 'your.email@example.com';

/**
 * Fetches metadata using a DOI with improved error handling and logging
 * 
 * @param {string} doi - Digital Object Identifier
 * @returns {Promise<Object>} - Promise with metadata
 */
export const fetchDOIMetadata = async (doi) => {
  try {
    console.log(`[DEBUG] fetchDOIMetadata() called with DOI: ${doi}`);
    
    if (!doi) {
      console.warn("[DEBUG] No DOI provided to fetchDOIMetadata");
      return null;
    }
    
    // First try direct CrossRef access
    console.log("[DEBUG] Attempting direct CrossRef access");
    const crossrefData = await fetchDOIMetadataFromCrossRef(doi);
    
    if (crossrefData) {
      console.log("[DEBUG] Successfully retrieved data from CrossRef API directly");
      const formattedData = formatCrossRefMetadata(crossrefData);
      console.log("[DEBUG] Formatted CrossRef data:", formattedData);
      return formattedData;
    }
    
    // If direct access doesn't work, try via the backend
    console.log("[DEBUG] Direct CrossRef access failed, trying via backend");
    try {
      console.log(`[DEBUG] Making backend request to: ${API_URL}/doi/${encodeURIComponent(doi)}`);
      const response = await apiClient.get(`${API_URL}/doi/${encodeURIComponent(doi)}`);
      console.log("[DEBUG] Backend DOI response:", response.data);
      return response.data;
    } catch (error) {
      console.error('[ERROR] Error fetching DOI metadata from backend:', error);
      
      // If backend fails, try one more direct access with different options
      console.log("[DEBUG] Backend failed, trying alternative direct access");
      try {
        const alternateData = await fetch(`https://api.crossref.org/works/${encodeURIComponent(doi)}`, {
          headers: {
            'Accept': 'application/json',
            'User-Agent': `SciLit2.0/1.0 (${CROSSREF_EMAIL})`,
          }
        });
        
        if (alternateData.ok) {
          const jsonData = await alternateData.json();
          if (jsonData && jsonData.message) {
            console.log("[DEBUG] Successfully retrieved data via alternative method");
            const formattedData = formatCrossRefMetadata(jsonData.message);
            return formattedData;
          }
        }
      } catch (altError) {
        console.error('[ERROR] Alternative CrossRef access also failed:', altError);
      }
      
      // Throw a more informative error
      throw { 
        message: 'Could not retrieve DOI metadata',
        originalError: error,
        doi: doi 
      };
    }
  } catch (error) {
    console.error('[ERROR] Error in fetchDOIMetadata:', error);
    throw error.response?.data || { message: 'Could not retrieve DOI metadata' };
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
    console.log(`[DEBUG] Direct CrossRef request for DOI: ${doi}`);
    const encodedDOI = encodeURIComponent(doi);
    const url = `${CROSSREF_API_BASE_URL}/works/${encodedDOI}`;
    console.log(`[DEBUG] CrossRef URL: ${url}`);
    
    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': `SciLit2.0/1.0 (${CROSSREF_EMAIL})`,
      }
    });
    
    console.log(`[DEBUG] CrossRef response status: ${response.status}`);
    
    if (!response.ok) {
      console.warn(`[DEBUG] CrossRef API error: ${response.status}`);
      return null;
    }
    
    const data = await response.json();
    console.log("[DEBUG] CrossRef raw response:", data);
    
    if (data && data.message) {
      return data.message;
    }
    console.warn("[DEBUG] No message in CrossRef response");
    return null;
  } catch (error) {
    console.error('[ERROR] Error fetching DOI metadata from CrossRef:', error);
    return null;
  }
};

/**
 * Formats CrossRef metadata into a standardized format with improved processing
 * 
 * @param {Object} metadata - Raw metadata from CrossRef
 * @returns {Object} - Formatted metadata
 */
export const formatCrossRefMetadata = (metadata) => {
  if (!metadata) return null;
  
  try {
    console.log("[DEBUG] Formatting CrossRef metadata:", metadata);
    
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
      console.log(`[DEBUG] CrossRef document type: ${metadata.type}`);
      
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
      
      console.log(`[DEBUG] Mapped to application type: ${result.type}`);
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
          result.publicationDate = `${date[0]}`;
        }
      }
    }
    // Fallback: look for created or issued date
    else if (metadata.created && metadata.created['date-parts'] && metadata.created['date-parts'][0]) {
      const date = metadata.created['date-parts'][0];
      if (date.length >= 1) {
        result.publicationDate = `${date[0]}`;
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
    
    console.log("[DEBUG] Formatted document type:", result.type);
    console.log("[DEBUG] Final formatted metadata:", result);
    return result;
  } catch (error) {
    console.error('[ERROR] Error formatting CrossRef metadata:', error);
    return null;
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
    console.log(`[DEBUG] fetchISBNMetadata() called with ISBN: ${isbn}`);
    
    if (!isbn) {
      console.warn("[DEBUG] No ISBN provided to fetchISBNMetadata");
      return null;
    }
    
    // Remove hyphens and spaces for consistent format
    const cleanIsbn = isbn.replace(/[-\s]/g, '');
    console.log(`[DEBUG] Cleaned ISBN: ${cleanIsbn}`);
    
    // Try via backend
    console.log(`[DEBUG] Making backend request to: ${API_URL}/isbn/${cleanIsbn}`);
    const response = await apiClient.get(`${API_URL}/isbn/${cleanIsbn}`);
    console.log("[DEBUG] Backend ISBN response:", response.data);
    return response.data;
  } catch (error) {
    console.error('[ERROR] Error fetching ISBN metadata:', error);
    console.error('[ERROR] Response:', error.response?.data);
    
    // Try alternate sources like OpenLibrary
    try {
      console.log("[DEBUG] Trying alternate source (OpenLibrary) for ISBN");
      const openLibraryData = await fetchISBNFromOpenLibrary(isbn);
      if (openLibraryData) {
        return openLibraryData;
      }
    } catch (altError) {
      console.error('[ERROR] Alternate ISBN source also failed:', altError);
    }
    
    throw error.response?.data || { message: 'Could not retrieve ISBN metadata' };
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
    console.log(`[DEBUG] searchMetadata() called with query: ${query}`);
    
    if (!query || query.length < 3) {
      throw new Error('Search query must be at least 3 characters');
    }
    
    console.log(`[DEBUG] Making search request to: ${API_URL}/search?q=${encodeURIComponent(query)}`);
    const response = await apiClient.get(`${API_URL}/search`, {
      params: { q: query }
    });
    
    console.log("[DEBUG] Search response:", response.data);
    return response.data;
  } catch (error) {
    console.error('[ERROR] Error searching metadata:', error);
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
    console.log(`[DEBUG] getCitationStyles() called`);
    const response = await apiClient.get(`${API_URL}/citation-styles`);
    console.log("[DEBUG] Citation styles response:", response.data);
    return response.data;
  } catch (error) {
    console.error('[ERROR] Error fetching citation styles:', error);
    // Return default styles if API fails
    return [
      { id: 'apa', name: 'APA 7th Edition' },
      { id: 'chicago', name: 'Chicago 18th Edition' },
      { id: 'harvard', name: 'Harvard' }
    ];
  }
};