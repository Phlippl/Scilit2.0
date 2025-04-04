// src/api/metadata.js
import axios from 'axios';

const API_URL = '/api/metadata';
const CROSSREF_EMAIL = 'your.email@example.com'; // Should be moved to environment variable

export const fetchDOIMetadata = async (doi) => {
  try {
    const response = await axios.get(`${API_URL}/doi/${encodeURIComponent(doi)}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Failed to fetch DOI metadata' };
  }
};

export const fetchISBNMetadata = async (isbn) => {
  try {
    const response = await axios.get(`${API_URL}/isbn/${encodeURIComponent(isbn)}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Failed to fetch ISBN metadata' };
  }
};

// Direct CrossRef calls (fallback if backend is unavailable)
export const fetchDOIMetadataFromCrossRef = async (doi) => {
  if (!doi) return null;
  
  try {
    const encodedDOI = encodeURIComponent(doi);
    const url = `https://api.crossref.org/works/${encodedDOI}`;
    
    const response = await axios.get(url, {
      headers: {
        'User-Agent': `AcademicLiteratureAssistant/1.0 (${CROSSREF_EMAIL})`,
      },
      params: {
        mailto: CROSSREF_EMAIL,
      },
    });
    
    if (response.status === 200 && response.data?.message) {
      return response.data.message;
    }
    return null;
  } catch (error) {
    console.error('Error fetching DOI metadata from CrossRef:', error);
    return null;
  }
};