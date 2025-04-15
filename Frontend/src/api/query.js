// src/api/query.js
import apiClient from './client';

const QUERY_ENDPOINT = '/api/query';

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
    // Basic validation
    if (!queryParams.query || typeof queryParams.query !== 'string' || !queryParams.query.trim()) {
      throw new Error('A valid query text is required');
    }
    
    // Ensure n_results is a number
    if (queryParams.n_results !== undefined) {
      queryParams.n_results = parseInt(queryParams.n_results, 10);
      if (isNaN(queryParams.n_results)) {
        delete queryParams.n_results;
      }
    }
    
    // Convert document_ids to array if it's not already
    if (queryParams.document_ids && !Array.isArray(queryParams.document_ids)) {
      if (typeof queryParams.document_ids === 'string') {
        queryParams.document_ids = [queryParams.document_ids];
      } else {
        delete queryParams.document_ids;
      }
    }
    
    const response = await apiClient.post(QUERY_ENDPOINT, queryParams);
    return response.data;
  } catch (error) {
    console.error('Query execution error:', error);
    
    // Construct a standardized error object
    const errorMessage = error.response?.data?.error || 
                         error.response?.data?.message || 
                         error.message || 
                         'Query failed';
                         
    const errorObject = {
      message: errorMessage,
      status: error.response?.status || 500,
      details: error.response?.data
    };
    
    throw errorObject;
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
    // Basic validation
    if (!savedQuery.query || typeof savedQuery.query !== 'string') {
      throw new Error('A valid query text is required');
    }
    
    if (!Array.isArray(savedQuery.results)) {
      savedQuery.results = [];
    }
    
    if (!Array.isArray(savedQuery.bibliography)) {
      savedQuery.bibliography = [];
    }
    
    // Add timestamp if not present
    if (!savedQuery.timestamp) {
      savedQuery.timestamp = new Date().toISOString();
    }
    
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

/**
 * Executes a streaming query that returns results gradually
 * 
 * @param {Object} queryParams - Query parameters (same as queryDocuments)
 * @param {Function} onChunk - Callback for each chunk of the response
 * @returns {Promise<void>}
 */
export const streamQueryResults = async (queryParams, onChunk) => {
  try {
    // Add streaming flag
    const streamParams = {
      ...queryParams,
      streaming: true
    };
    
    // Use fetch API for streaming
    const response = await fetch(`${apiClient.defaults.baseURL}${QUERY_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': apiClient.defaults.headers.Authorization
      },
      body: JSON.stringify(streamParams)
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Stream request failed: ${errorText}`);
    }
    
    // Process the stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        // Process any remaining buffer data
        if (buffer.trim()) {
          try {
            const chunk = JSON.parse(buffer);
            onChunk(chunk);
          } catch (e) {
            console.error('Error parsing final chunk:', e);
          }
        }
        break;
      }
      
      // Decode and add to buffer
      buffer += decoder.decode(value, { stream: true });
      
      // Process complete JSON objects in the buffer
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        
        if (line) {
          try {
            const chunk = JSON.parse(line);
            onChunk(chunk);
          } catch (e) {
            console.error('Error parsing chunk:', e);
          }
        }
      }
    }
  } catch (error) {
    console.error('Stream query error:', error);
    throw error;
  }
};