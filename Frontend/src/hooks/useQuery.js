// src/hooks/useQuery.js
import { useState, useCallback, useRef } from 'react';
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
  const [savedQueries, setSavedQueries] = useState([]);
  
  // Ref for active stream
  const activeStreamRef = useRef(null);

  /**
   * Execute a query against document collection
   * 
   * @param {Object} queryParams - Query parameters
   * @param {string} queryParams.query - The actual query text
   * @param {string} [queryParams.citation_style] - Citation style to use
   * @param {Array} [queryParams.document_ids] - Optional list of document IDs to query
   * @param {number} [queryParams.n_results] - Number of results to return
   * @param {boolean} [queryParams.use_direct_quotes] - Whether to use direct quotes
   * @param {boolean} [queryParams.include_page_numbers] - Whether to include page numbers
   * @returns {Promise<Object>} Query results with bibliography
   */
  const executeQuery = useCallback(async (queryParams) => {
    if (!queryParams.query || !queryParams.query.trim()) {
      setError('Query text is required');
      return null;
    }

    // Cancel any active streams first
    if (activeStreamRef.current) {
      activeStreamRef.current.abort();
      activeStreamRef.current = null;
    }

    setIsLoading(true);
    setError(null);
    clearResults(); // Clear previous results for a new query
    
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
   * Execute a streaming query for progressive results
   * 
   * @param {Object} queryParams - Query parameters (same as executeQuery)
   * @param {Function} onProgress - Callback for progress updates
   * @returns {Promise<Object>} Final query result
   */
  const executeStreamingQuery = useCallback(async (queryParams, onProgress) => {
    if (!queryParams.query || !queryParams.query.trim()) {
      setError('Query text is required');
      return null;
    }

    // Cancel any active streams first
    if (activeStreamRef.current) {
      activeStreamRef.current.abort();
    }

    // Create new AbortController for this stream
    const controller = new AbortController();
    activeStreamRef.current = controller;

    setIsLoading(true);
    setError(null);
    clearResults(); // Clear previous results
    
    const startTime = performance.now();
    
    try {
      // Initialize results arrays
      const results = [];
      let bibliographyItems = [];
      
      // Define chunk handler
      const handleChunk = (chunk) => {
        if (chunk.type === 'search_results') {
          // Search results info
          if (onProgress) {
            onProgress('search_results', chunk.data);
          }
        } 
        else if (chunk.type === 'llm_chunk') {
          // LLM response chunk
          if (!chunk.data.complete) {
            results.push(chunk.data);
            setQueryResults([...results]);
          }
          
          if (onProgress) {
            onProgress('llm_chunk', chunk.data);
          }
        } 
        else if (chunk.type === 'bibliography') {
          // Bibliography
          bibliographyItems = chunk.data;
          setBibliography(bibliographyItems);
          
          if (onProgress) {
            onProgress('bibliography', bibliographyItems);
          }
        }
      };
      
      // Execute the streaming query
      await queryApi.streamQueryResults(queryParams, handleChunk);
      
      // Calculate query time
      const endTime = performance.now();
      const queryDuration = (endTime - startTime) / 1000;
      setQueryTime(queryDuration);
      
      // Return complete result
      return {
        results,
        bibliography: bibliographyItems,
        query: queryParams.query,
        search_time: queryDuration
      };
    } catch (err) {
      // Only set error if this request wasn't intentionally aborted
      if (!controller.signal.aborted) {
        setError(err.message || 'Query execution failed');
        console.error('Error executing streaming query:', err);
      }
      return null;
    } finally {
      setIsLoading(false);
      
      // Clear the abort controller reference if it's still this one
      if (activeStreamRef.current === controller) {
        activeStreamRef.current = null;
      }
    }
  }, []);

  /**
   * Cancel any active streaming query
   */
  const cancelStreamingQuery = useCallback(() => {
    if (activeStreamRef.current) {
      activeStreamRef.current.abort();
      activeStreamRef.current = null;
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
    setError(null);
  }, []);

  /**
   * Save current query and results to history
   * 
   * @param {Object} queryData - Query data to save
   * @returns {Promise<Object>} Saved query data
   */
  const saveQueryToHistory = useCallback(async (queryData) => {
    try {
      if (!queryData.query || (queryData.results && queryData.results.length === 0)) {
        throw new Error('Cannot save empty query or results');
      }
      
      // Save via API
      const savedQuery = await queryApi.saveQuery(queryData);
      
      // Update local state
      setSavedQueries(prev => [savedQuery, ...prev]);
      
      return savedQuery;
    } catch (err) {
      console.error('Error saving query:', err);
      
      // Still update local state even if API call fails
      const localSavedQuery = {
        ...queryData,
        id: `local_${Date.now()}`,
        timestamp: new Date().toISOString()
      };
      
      setSavedQueries(prev => [localSavedQuery, ...prev]);
      
      return localSavedQuery;
    }
  }, []);

  /**
   * Load saved queries from the server
   */
  const loadSavedQueries = useCallback(async () => {
    try {
      const queries = await queryApi.getSavedQueries();
      setSavedQueries(queries);
      return queries;
    } catch (err) {
      console.error('Error loading saved queries:', err);
      return [];
    }
  }, []);

  return {
    queryResults,
    bibliography,
    isLoading,
    error,
    queryTime,
    citationStyles,
    savedQueries,
    executeQuery,
    executeStreamingQuery,
    cancelStreamingQuery,
    fetchCitationStyles,
    clearResults,
    saveQueryToHistory,
    loadSavedQueries
  };
};

export default useQuery;