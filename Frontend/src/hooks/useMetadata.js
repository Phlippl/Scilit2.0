// src/hooks/useMetadata.js
import { useState, useCallback } from 'react';
import * as metadataApi from '../api/metadata';

/**
 * Hook for fetching and managing document metadata
 * 
 * @returns {Object} Metadata management functions and state
 */
export const useMetadata = () => {
  const [metadata, setMetadata] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Fetch metadata using DOI
   * 
   * @param {string} doi - Digital Object Identifier
   * @returns {Promise<Object>} Retrieved metadata
   */
  const fetchByDOI = useCallback(async (doi) => {
    if (!doi) {
      setError('DOI is required');
      return null;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const fetchedMetadata = await metadataApi.fetchDOIMetadata(doi);
      setMetadata(fetchedMetadata);
      return fetchedMetadata;
    } catch (err) {
      setError(err.message || 'Failed to fetch metadata by DOI');
      console.error('Error fetching metadata by DOI:', err);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Fetch metadata using ISBN
   * 
   * @param {string} isbn - International Standard Book Number
   * @returns {Promise<Object>} Retrieved metadata
   */
  const fetchByISBN = useCallback(async (isbn) => {
    if (!isbn) {
      setError('ISBN is required');
      return null;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const fetchedMetadata = await metadataApi.fetchISBNMetadata(isbn);
      setMetadata(fetchedMetadata);
      return fetchedMetadata;
    } catch (err) {
      setError(err.message || 'Failed to fetch metadata by ISBN');
      console.error('Error fetching metadata by ISBN:', err);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Create default metadata structure
   * 
   * @param {Object} partialMetadata - Partial metadata to include
   * @returns {Object} Default metadata structure
   */
  const createDefaultMetadata = useCallback((partialMetadata = {}) => {
    const defaultMetadata = {
      title: '',
      authors: [],
      publicationDate: '',
      publisher: '',
      journal: '',
      doi: '',
      isbn: '',
      abstract: '',
      ...partialMetadata
    };
    
    setMetadata(defaultMetadata);
    return defaultMetadata;
  }, []);

  /**
   * Update metadata fields
   * 
   * @param {Object} updatedFields - Fields to update
   */
  const updateMetadata = useCallback((updatedFields) => {
    setMetadata(prev => {
      if (!prev) return updatedFields;
      return { ...prev, ...updatedFields };
    });
  }, []);

  /**
   * Reset metadata state
   */
  const resetMetadata = useCallback(() => {
    setMetadata(null);
    setError(null);
  }, []);

  return {
    metadata,
    isLoading,
    error,
    fetchByDOI,
    fetchByISBN,
    createDefaultMetadata,
    updateMetadata,
    resetMetadata
  };
};

export default useMetadata;