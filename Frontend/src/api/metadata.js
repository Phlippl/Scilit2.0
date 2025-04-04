// src/api/metadata.js
import apiClient from './client';

const API_URL = '/metadata';

// Konfiguration für direkten CrossRef-Zugriff
const CROSSREF_API_BASE_URL = 'https://api.crossref.org';
const CROSSREF_EMAIL = import.meta.env.VITE_CROSSREF_EMAIL || 'your.email@example.com';

/**
 * Ruft Metadaten anhand einer DOI ab
 * 
 * @param {string} doi - Die Digital Object Identifier
 * @returns {Promise<Object>} - Promise mit Metadaten
 */
export const fetchDOIMetadata = async (doi) => {
  try {
    const response = await apiClient.get(`${API_URL}/doi/${encodeURIComponent(doi)}`);
    return response.data;
  } catch (error) {
    // Bei Backend-Fehler direkten CrossRef-Zugriff versuchen
    if (error.response?.status === 404 || error.response?.status === 500) {
      const crossrefData = await fetchDOIMetadataFromCrossRef(doi);
      if (crossrefData) {
        return formatCrossRefMetadata(crossrefData);
      }
    }
    
    throw error.response?.data || { message: 'DOI-Metadaten konnten nicht abgerufen werden' };
  }
};

/**
 * Ruft Metadaten anhand einer ISBN ab
 * 
 * @param {string} isbn - Die International Standard Book Number
 * @returns {Promise<Object>} - Promise mit Metadaten
 */
export const fetchISBNMetadata = async (isbn) => {
  try {
    const response = await apiClient.get(`${API_URL}/isbn/${encodeURIComponent(isbn)}`);
    return response.data;
  } catch (error) {
    // Bei Backend-Fehler direkten CrossRef-Zugriff versuchen
    if (error.response?.status === 404 || error.response?.status === 500) {
      const crossrefData = await searchByISBNFromCrossRef(isbn);
      if (crossrefData && crossrefData.length > 0) {
        return formatCrossRefMetadata(crossrefData[0]);
      }
    }
    
    throw error.response?.data || { message: 'ISBN-Metadaten konnten nicht abgerufen werden' };
  }
};

/**
 * Direkter Zugriff auf CrossRef für DOI-Metadaten (Fallback)
 * 
 * @param {string} doi - Die Digital Object Identifier
 * @returns {Promise<Object>} - Promise mit Metadaten
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
      throw new Error(`CrossRef API Fehler: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data && data.message) {
      return data.message;
    }
    return null;
  } catch (error) {
    console.error('Fehler beim Abrufen der DOI-Metadaten von CrossRef:', error);
    return null;
  }
};

/**
 * Direkter Zugriff auf CrossRef für ISBN-Suche (Fallback)
 * 
 * @param {string} isbn - Die International Standard Book Number
 * @returns {Promise<Array>} - Promise mit Suchergebnissen
 */
export const searchByISBNFromCrossRef = async (isbn) => {
  if (!isbn) return [];
  
  try {
    // Bindestriche und Leerzeichen aus ISBN entfernen
    const cleanISBN = isbn.replace(/[-\s]/g, '');
    const url = `${CROSSREF_API_BASE_URL}/works?query=${cleanISBN}&filter=type:book&rows=5`;
    
    const response = await fetch(url, {
      headers: {
        'User-Agent': `SciLit2.0/1.0 (${CROSSREF_EMAIL})`,
      }
    });
    
    if (!response.ok) {
      throw new Error(`CrossRef API Fehler: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data && data.message && data.message.items) {
      return data.message.items;
    }
    return [];
  } catch (error) {
    console.error('Fehler bei der ISBN-Suche über CrossRef:', error);
    return [];
  }
};

/**
 * Formatiert CrossRef-Metadaten in einheitliches Format
 * 
 * @param {Object} metadata - Rohe Metadaten von CrossRef
 * @returns {Object} - Formatierte Metadaten
 */
export const formatCrossRefMetadata = (metadata) => {
  if (!metadata) return null;
  
  try {
    // Grundlegende Informationen extrahieren
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
    
    // Autoren extrahieren
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
    
    // Publikationsdatum extrahieren
    if (metadata.published) {
      const date = metadata.published['date-parts'] ? 
        metadata.published['date-parts'][0] : [];
      
      if (date.length >= 1) {
        // Format als YYYY-MM-DD oder Teildatum
        result.publicationDate = date.join('-');
      }
    }
    
    // ISBN für Bücher extrahieren
    if (metadata.ISBN && Array.isArray(metadata.ISBN)) {
      result.isbn = metadata.ISBN[0];
    }
    
    // ISSN für Zeitschriften extrahieren
    if (metadata.ISSN && Array.isArray(metadata.ISSN)) {
      result.issn = metadata.ISSN[0];
    }
    
    return result;
  } catch (error) {
    console.error('Fehler beim Formatieren der Metadaten:', error);
    return null;
  }
};