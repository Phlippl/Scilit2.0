// src/api/query.js
import axios from 'axios';

const API_URL = '/api/query';

export const queryDocuments = async (queryParams) => {
  try {
    const response = await axios.post(API_URL, queryParams);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Query failed' };
  }
};

export const getSupportedCitationStyles = async () => {
  try {
    const response = await axios.get(`${API_URL}/citation-styles`);
    return response.data;
  } catch (error) {
    // Fallback to default styles if API fails
    return [
      { id: 'apa', name: 'APA 7th Edition' },
      { id: 'chicago', name: 'Chicago 18th Edition' },
      { id: 'harvard', name: 'Harvard' },
    ];
  }
};