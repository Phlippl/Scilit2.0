// src/api/query.js
import apiClient from './client';

const QUERY_ENDPOINT = '/query';

/**
 * Queries documents with the given parameters
 * 
 * @param {Object} queryParams - Query parameters
 * @param {string} queryParams.query - The query text
 * @param {string} [queryParams.citation_style] - Citation style to use (e.g., 'apa', 'chicago', 'harvard')
 * @param {Array<string>} [queryParams.document_ids] - Optional list of document IDs to limit the query to
 * @param {number} [queryParams.n_results] - Number of results to return
 * @param {boolean} [queryParams.use_direct_quotes] - Whether to use direct quotes in results
 * @param {boolean} [queryParams.include_page_numbers] - Whether to include page numbers in citations
 * @returns {Promise<Object>} Query results and bibliography
 */
export const queryDocuments = async (queryParams) => {
  try {
    const response = await apiClient.post(QUERY_ENDPOINT, queryParams);
    return response.data;
  } catch (error) {
    console.error('Query execution error:', error);
    throw error.response?.data || { message: 'Query failed' };
  }
};

/**
 * Gets a list of supported citation styles
 * 
 * @returns {Promise<Array>} List of citation styles
 */
export const getSupportedCitationStyles = async () => {
  try {
    const response = await apiClient.get(`${QUERY_ENDPOINT}/citation-styles`);
    return response.data;
  } catch (error) {
    console.error('Error fetching citation styles:', error);
    // Fallback to default styles if API fails
    return [
      { id: 'apa', name: 'APA 7th Edition' },
      { id: 'chicago', name: 'Chicago 18th Edition' },
      { id: 'harvard', name: 'Harvard' },
    ];
  }
};

/**
 * Saves a query and its results
 * 
 * @param {Object} savedQuery - Query and results to save
 * @param {string} savedQuery.query - The original query text
 * @param {Array} savedQuery.results - Query results
 * @param {Array} savedQuery.bibliography - Bibliography entries
 * @returns {Promise<Object>} Saved query with ID
 */
export const saveQuery = async (savedQuery) => {
  try {
    const response = await apiClient.post(`${QUERY_ENDPOINT}/save`, savedQuery);
    return response.data;
  } catch (error) {
    console.error('Error saving query:', error);
    throw error.response?.data || { message: 'Failed to save query' };
  }
};

/**
 * Gets saved queries for the current user
 * 
 * @returns {Promise<Array>} List of saved queries
 */
export const getSavedQueries = async () => {
  try {
    const response = await apiClient.get(`${QUERY_ENDPOINT}/saved`);
    return response.data;
  } catch (error) {
    console.error('Error fetching saved queries:', error);
    throw error.response?.data || { message: 'Failed to retrieve saved queries' };
  }
};