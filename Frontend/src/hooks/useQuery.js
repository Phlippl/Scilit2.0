// src/hooks/useQuery.js
import { useState, useCallback } from 'react';
import * as queryApi from '../api/query';

/**
 * Hook for querying documents and managing query state
 * 
 * @returns {Object} Query management functions and state
 */
const useQuery = () => {
  const [queryResults, setQueryResults] = useState([]);
  const [bibliography, setBibliography] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [queryTime, setQueryTime] = useState(null);
  const [citationStyles, setCitationStyles] = useState([
    { id: 'apa', name: 'APA 7th Edition' },
    { id: 'chicago', name: 'Chicago 18th Edition' },
    { id: 'harvard', name: 'Harvard' }
  ]);

  /**
   * Execute a query against document collection
   * 
   * @param {Object} queryParams - Query parameters
   * @param {string} queryParams.query - The actual query text
   * @param {string} [queryParams.citation_style] - Citation style to use
   * @param {Array} [queryParams.document_ids] - Optional list of document IDs to query
   * @param {number} [queryParams.n_results] - Number of results to return
   * @param {boolean} [queryParams.use_direct_quotes] - Whether to use direct quotes
   * @returns {Promise<Object>} Query results with bibliography
   */
  const executeQuery = useCallback(async (queryParams) => {
    if (!queryParams.query) {
      setError('Query text is required');
      return null;
    }

    setIsLoading(true);
    setError(null);
    
    const startTime = performance.now();
    
    try {
      const response = await queryApi.queryDocuments(queryParams);
      
      const endTime = performance.now();
      setQueryTime((endTime - startTime) / 1000); // Convert to seconds
      
      setQueryResults(response.results || []);
      setBibliography(response.bibliography || []);
      
      return response;
    } catch (err) {
      setError(err.message || 'Query execution failed');
      console.error('Error executing query:', err);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Fetch available citation styles
   */
  const fetchCitationStyles = useCallback(async () => {
    try {
      const styles = await queryApi.getSupportedCitationStyles();
      if (styles && styles.length > 0) {
        setCitationStyles(styles);
      }
    } catch (err) {
      console.error('Error fetching citation styles:', err);
      // Keep default styles if fetch fails
    }
  }, []);

  /**
   * Clear query results
   */
  const clearResults = useCallback(() => {
    setQueryResults([]);
    setBibliography([]);
    setQueryTime(null);
  }, []);

  return {
    queryResults,
    bibliography,
    isLoading,
    error,
    queryTime,
    citationStyles,
    executeQuery,
    fetchCitationStyles,
    clearResults
  };
};

export default useQuery;