// Frontend/src/services/crossrefService.js
import axios from 'axios';

// Base URL for CrossRef API
const CROSSREF_API_BASE_URL = 'https://api.crossref.org';

// Add polite parameter with your email for better rate limits
// Replace with your actual email when deploying
const POLITE_POOL_EMAIL = 'your.email@example.com';

/**
 * CrossRef API service for fetching metadata by DOI or ISBN
 */
class CrossRefService {
  /**
   * Fetches metadata for a given DOI
   * @param {string} doi - The DOI to lookup (e.g., "10.1000/182")
   * @returns {Promise<Object>} - Promise resolving to the metadata object
   */
  async getMetadataByDOI(doi) {
    if (!doi) return null;
    
    try {
      // Encode the DOI to ensure it's URL-safe
      const encodedDOI = encodeURIComponent(doi);
      const url = `${CROSSREF_API_BASE_URL}/works/${encodedDOI}`;
      
      const response = await axios.get(url, {
        headers: {
          'User-Agent': `AcademicLiteratureAssistant/1.0 (${POLITE_POOL_EMAIL})`,
        },
        params: {
          mailto: POLITE_POOL_EMAIL,
        },
      });
      
      if (response.status === 200 && response.data && response.data.message) {
        return response.data.message;
      }
      return null;
    } catch (error) {
      console.error('Error fetching DOI metadata:', error);
      return null;
    }
  }
  
  /**
   * Searches for works using an ISBN
   * @param {string} isbn - The ISBN to search for
   * @returns {Promise<Array>} - Promise resolving to an array of matching works
   */
  async searchByISBN(isbn) {
    if (!isbn) return [];
    
    try {
      // Remove hyphens and spaces from ISBN
      const cleanISBN = isbn.replace(/[-\s]/g, '');
      const url = `${CROSSREF_API_BASE_URL}/works`;
      
      const response = await axios.get(url, {
        headers: {
          'User-Agent': `AcademicLiteratureAssistant/1.0 (${POLITE_POOL_EMAIL})`,
        },
        params: {
          query: cleanISBN,
          filter: 'type:book',
          rows: 5,  // Limit results
          mailto: POLITE_POOL_EMAIL,
        },
      });
      
      if (response.status === 200 && response.data && response.data.message && response.data.message.items) {
        return response.data.message.items;
      }
      return [];
    } catch (error) {
      console.error('Error searching by ISBN:', error);
      return [];
    }
  }
  
  /**
   * Formats metadata into a standardized structure
   * @param {Object} metadata - Raw metadata from CrossRef
   * @returns {Object} - Standardized metadata object
   */
  formatMetadata(metadata) {
    if (!metadata) return null;
    
    try {
      // Extract basic information
      const result = {
        title: metadata.title ? metadata.title[0] : '',
        doi: metadata.DOI || '',
        url: metadata.URL || '',
        type: metadata.type || '',
        publicationDate: '',
        authors: [],
        journal: metadata['container-title'] ? metadata['container-title'][0] : '',
        volume: metadata.volume || '',
        issue: metadata.issue || '',
        pages: metadata.page || '',
        publisher: metadata.publisher || '',
        abstract: metadata.abstract || '',
        isbn: '',
        issn: '',
      };
      
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
          result.publicationDate = date.join('-');
        }
      }
      
      // Extract ISBN for books
      if (metadata.ISBN && Array.isArray(metadata.ISBN)) {
        result.isbn = metadata.ISBN[0];
      }
      
      // Extract ISSN for journals
      if (metadata.ISSN && Array.isArray(metadata.ISSN)) {
        result.issn = metadata.ISSN[0];
      }
      
      return result;
    } catch (error) {
      console.error('Error formatting metadata:', error);
      return null;
    }
  }
}

export default new CrossRefService();