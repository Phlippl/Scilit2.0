// src/hooks/useDocuments.js
import { useState, useEffect, useCallback } from 'react';
import * as documentsApi from '../api/documents';

/**
 * Hook for managing documents with CRUD operations
 * 
 * @returns {Object} Document management functions and state
 */
export const useDocuments = () => {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);

  /**
   * Fetch all documents from the API
   */
  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const fetchedDocuments = await documentsApi.getDocuments();
      setDocuments(fetchedDocuments);
    } catch (err) {
      setError(err.message || 'Failed to fetch documents');
      console.error('Error fetching documents:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Fetch a specific document by ID
   * 
   * @param {string} id - Document ID to fetch
   */
  const fetchDocumentById = useCallback(async (id) => {
    if (!id) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const fetchedDocument = await documentsApi.getDocumentById(id);
      setSelectedDocument(fetchedDocument);
    } catch (err) {
      setError(err.message || `Failed to fetch document with ID: ${id}`);
      console.error(`Error fetching document with ID ${id}:`, err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Create a new document
   * 
   * @param {Object} documentData - New document data
   * @param {File} [file] - Optional PDF file
   * @returns {Promise<Object>} Created document
   */
  const createDocument = useCallback(async (documentData, file = null) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const newDocument = await documentsApi.saveDocument(documentData, file);
      
      // Update documents list with the new document
      setDocuments(prev => [...prev, newDocument]);
      
      return newDocument;
    } catch (err) {
      setError(err.message || 'Failed to create document');
      console.error('Error creating document:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Update an existing document
   * 
   * @param {string} id - Document ID to update
   * @param {Object} documentData - Updated document data
   * @returns {Promise<Object>} Updated document
   */
  const updateDocument = useCallback(async (id, documentData) => {
    if (!id) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const updatedDocument = await documentsApi.updateDocument(id, documentData);
      
      // Update documents list with the updated document
      setDocuments(prev => 
        prev.map(doc => doc.id === id ? updatedDocument : doc)
      );
      
      // Update selected document if it's the one being updated
      if (selectedDocument && selectedDocument.id === id) {
        setSelectedDocument(updatedDocument);
      }
      
      return updatedDocument;
    } catch (err) {
      setError(err.message || `Failed to update document with ID: ${id}`);
      console.error(`Error updating document with ID ${id}:`, err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [selectedDocument]);

  /**
   * Delete a document
   * 
   * @param {string} id - Document ID to delete
   * @returns {Promise<boolean>} Success status
   */
  const deleteDocument = useCallback(async (id) => {
    if (!id) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const success = await documentsApi.deleteDocument(id);
      
      if (success) {
        // Remove document from the list
        setDocuments(prev => prev.filter(doc => doc.id !== id));
        
        // Reset selected document if it's the one being deleted
        if (selectedDocument && selectedDocument.id === id) {
          setSelectedDocument(null);
        }
      }
      
      return success;
    } catch (err) {
      setError(err.message || `Failed to delete document with ID: ${id}`);
      console.error(`Error deleting document with ID ${id}:`, err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [selectedDocument]);
  
  // Load documents on first mount
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return {
    documents,
    selectedDocument,
    isLoading,
    error,
    fetchDocuments,
    fetchDocumentById,
    createDocument,
    updateDocument,
    deleteDocument,
    setSelectedDocument
  };
};

export default useDocuments;