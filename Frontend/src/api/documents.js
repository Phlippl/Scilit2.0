// src/api/documents.js
import apiClient from './client';
import mockService from '../utils/mockService';

const DOCUMENTS_ENDPOINT = '/documents';

// Prüfen, ob der Testmodus aktiviert ist
const testUserEnabled = import.meta.env.VITE_TEST_USER_ENABLED === 'true';

/**
 * Gets all documents for the current user
 * @returns {Promise<Array>} List of documents
 */
export const getDocuments = async () => {
  try {
    const response = await apiClient.get(DOCUMENTS_ENDPOINT);
    return response.data;
  } catch (error) {
    // Im Testmodus Mock-Daten zurückgeben
    if (testUserEnabled && (error.isTestMode || error.code === 'ERR_NETWORK')) {
      console.log('Using mock documents data');
      return mockService.documents;
    }
    
    console.error('Error fetching documents:', error);
    throw error.response?.data || { 
      message: 'Failed to retrieve documents' 
    };
  }
};

/**
 * Ruft den Verarbeitungsstatus eines Dokuments ab
 * 
 * @param {string} id - Dokument-ID
 * @returns {Promise<Object>} Verarbeitungsstatus-Informationen
 */
export const getDocumentStatus = async (id) => {
  try {
    const response = await apiClient.get(`${DOCUMENTS_ENDPOINT}/status/${id}`);
    return response.data;
  } catch (error) {
    // Im Testmodus Mock-Status basierend auf Zeit zurückgeben
    if (testUserEnabled && (error.isTestMode || error.code === 'ERR_NETWORK')) {
      console.log('Nutze Mock-Dokumentstatus');
      
      // Erstelle einen zeitbasierten Status, der langsam abgeschlossen wird (für UI-Tests)
      const startTime = parseInt(localStorage.getItem(`doc_start_${id}`) || Date.now());
      const currentTime = Date.now();
      const elapsedSeconds = (currentTime - startTime) / 1000;
      
      // Startzeit speichern, falls nicht vorhanden
      if (!localStorage.getItem(`doc_start_${id}`)) {
        localStorage.setItem(`doc_start_${id}`, startTime);
      }
      
      // Nach 20 Sekunden abschließen
      if (elapsedSeconds > 20) {
        localStorage.removeItem(`doc_start_${id}`); // Aufräumen
        return {
          status: 'completed',
          progress: 100,
          message: 'Verarbeitung abgeschlossen'
        };
      }
      
      // Fortschritt simulieren
      const progress = Math.min(Math.floor(elapsedSeconds * 5), 95); // Max 95% bis zur Fertigstellung
      
      // Statusmeldung basierend auf Fortschritt erstellen
      let message = 'Starte Dokumentverarbeitung...';
      if (progress > 10) message = 'Extrahiere Text...';
      if (progress > 30) message = 'Erstelle Dokument-Chunks...';
      if (progress > 50) message = 'Generiere Einbettungen...';
      if (progress > 70) message = 'Speichere in Vektordatenbank...';
      if (progress > 90) message = 'Finalisiere Dokumentverarbeitung...';
      
      return {
        status: 'processing',
        progress,
        message
      };
    }
    
    console.error(`Fehler beim Abrufen des Dokumentstatus für ID ${id}:`, error);
    throw error.response?.data || {
      message: 'Dokumentstatus konnte nicht abgerufen werden'
    };
  }
};

/**
 * Gets a specific document by ID
 * @param {string} id - Document ID
 * @returns {Promise<Object>} Document data
 */
export const getDocumentById = async (id) => {
  try {
    const response = await apiClient.get(`${DOCUMENTS_ENDPOINT}/${id}`);
    return response.data;
  } catch (error) {
    // Im Testmodus Mock-Daten zurückgeben
    if (testUserEnabled && (error.isTestMode || error.code === 'ERR_NETWORK')) {
      console.log('Using mock document data for ID:', id);
      const doc = mockService.documents.find(d => d.id === id);
      if (doc) return doc;
      throw { message: 'Document not found' };
    }
    
    console.error(`Error fetching document (ID: ${id}):`, error);
    throw error.response?.data || { 
      message: 'Failed to retrieve document' 
    };
  }
};


/**
 * Saves a new document with metadata and file content
 * 
 * @param {Object} documentData - Document data with metadata
 * @param {File} [file] - Optional PDF file (if not already included in documentData)
 * @returns {Promise<Object>} Saved document with ID
 */
export const saveDocument = async (documentData, file = null) => {
  try {
    let data = documentData;
    let headers = {};
    
    // If a separate file was passed, create FormData
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      
      // Stelle sicher, dass wichtige Metadatenfelder direkt im FormData liegen
      formData.append('title', documentData.title || '');
      formData.append('type', documentData.type || 'article');
      
      // Füge Authors als JSON-String hinzu wenn vorhanden
      if (documentData.authors && documentData.authors.length > 0) {
        formData.append('authors', JSON.stringify(documentData.authors));
      }
      
      // Add documentData as JSON string
      formData.append('data', JSON.stringify(documentData));
      
      data = formData;
      // Let axios set the content type with boundary
      headers = {
        'Content-Type': 'multipart/form-data'
      };
    }
    
    // Debug-Log
    console.log('Saving document with title:', documentData.title);
    console.log('File included:', !!file);
    
    const response = await apiClient.post(DOCUMENTS_ENDPOINT, data, { headers });
    
    return response.data;
  } catch (error) {
    // Im Testmodus Mock-Daten zurückgeben
    if (testUserEnabled && (error.isTestMode || error.code === 'ERR_NETWORK')) {
      console.log('Using mock document save');
      return mockService.saveDocument(documentData, file);
    }
    
    console.error('Error saving document:', error);
    throw error.response?.data || { 
      message: 'Failed to save document' 
    };
  }
};

/**
 * Updates an existing document
 * 
 * @param {string} id - Document ID to update
 * @param {Object} documentData - Updated document data
 * @returns {Promise<Object>} Updated document
 */
export const updateDocument = async (id, documentData) => {
  try {
    const response = await apiClient.put(`${DOCUMENTS_ENDPOINT}/${id}`, documentData);
    return response.data;
  } catch (error) {
    // Im Testmodus Mock-Daten zurückgeben
    if (testUserEnabled && (error.isTestMode || error.code === 'ERR_NETWORK')) {
      console.log('Using mock document update for ID:', id);
      // Einfache Simulation eines Updates
      return { id, ...documentData, updatedAt: new Date().toISOString() };
    }
    
    console.error(`Error updating document (ID: ${id}):`, error);
    throw error.response?.data || { 
      message: 'Failed to update document' 
    };
  }
};

/**
 * Deletes a document
 * 
 * @param {string} id - Document ID to delete
 * @returns {Promise<boolean>} Success status
 */
export const deleteDocument = async (id) => {
  try {
    await apiClient.delete(`${DOCUMENTS_ENDPOINT}/${id}`);
    return true;
  } catch (error) {
    // Im Testmodus Mock-Daten zurückgeben
    if (testUserEnabled && (error.isTestMode || error.code === 'ERR_NETWORK')) {
      console.log('Using mock document delete for ID:', id);
      return true;
    }
    
    console.error(`Error deleting document (ID: ${id}):`, error);
    throw error.response?.data || { 
      message: 'Failed to delete document' 
    };
  }
};

/**
 * Analyzes a document without saving it to get metadata and chunks
 * 
 * @param {FormData} formData - Form data with file and settings
 * @param {Function} progressCallback - Optional callback for progress updates
 * @returns {Promise<Object>} Analysis results with metadata and chunks
 */
export const analyzeDocument = async (formData, progressCallback = null) => {
  try {
    // Create a custom axios instance for this request to handle progress
    const axiosInstance = axios.create({
      baseURL: apiClient.defaults.baseURL,
      headers: {
        ...apiClient.defaults.headers,
        'Content-Type': 'multipart/form-data'
      }
    });

    // Add the authorization header if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      axiosInstance.defaults.headers.Authorization = `Bearer ${token}`;
    }

    // Add progress tracking if a callback is provided
    if (progressCallback) {
      axiosInstance.defaults.onUploadProgress = (progressEvent) => {
        const uploadProgress = Math.round((progressEvent.loaded * 30) / progressEvent.total);
        progressCallback('Uploading file...', uploadProgress);
      };
    }

    const response = await axiosInstance.post(`${DOCUMENTS_ENDPOINT}/analyze`, formData);
    
    // Track progress for processing phase
    if (response.data.jobId && progressCallback) {
      // Start polling for analysis status
      let completed = false;
      let attempt = 0;
      
      while (!completed && attempt < 30) { // Max 30 attempts (5 minutes with 10s interval)
        attempt++;
        
        // Wait 10 seconds between polls
        await new Promise(resolve => setTimeout(resolve, 10000));
        
        try {
          const statusResponse = await apiClient.get(`${DOCUMENTS_ENDPOINT}/analyze/${response.data.jobId}`);
          
          if (statusResponse.data.status === 'completed') {
            completed = true;
            return statusResponse.data.result;
          } else if (statusResponse.data.status === 'processing') {
            // Update progress (30-90%)
            const processingProgress = 30 + Math.min(60, attempt * 2);
            progressCallback(statusResponse.data.message || 'Processing document...', processingProgress);
          } else if (statusResponse.data.status === 'error') {
            throw new Error(statusResponse.data.error || 'Analysis failed');
          }
        } catch (pollError) {
          console.error('Error polling analysis status:', pollError);
          // On network errors, continue polling
          if (pollError.message.includes('Network Error')) {
            continue;
          }
          throw pollError;
        }
      }
      
      if (!completed) {
        throw new Error('Analysis timed out');
      }
    }
    
    return response.data;
  } catch (error) {
    // In test mode, return mock data
    if (testUserEnabled && (error.isTestMode || error.code === 'ERR_NETWORK')) {
      console.log('Using mock document analysis');
      
      // Simulate progress updates
      if (progressCallback) {
        progressCallback('Starting analysis...', 10);
        await new Promise(resolve => setTimeout(resolve, 500));
        progressCallback('Extracting text...', 30);
        await new Promise(resolve => setTimeout(resolve, 500));
        progressCallback('Analyzing document...', 50);
        await new Promise(resolve => setTimeout(resolve, 500));
        progressCallback('Extracting metadata...', 70);
        await new Promise(resolve => setTimeout(resolve, 500));
        progressCallback('Creating chunks...', 90);
        await new Promise(resolve => setTimeout(resolve, 500));
        progressCallback('Analysis complete', 100);
      }
      
      // Generate mock analysis result
      return {
        metadata: {
          doi: '10.1234/example.2023.0001',
          isbn: null
        },
        chunks: Array(15).fill().map((_, i) => ({
          text: `This is sample chunk ${i+1} with some academic content for demonstration purposes.`,
          page_number: Math.floor(i/3) + 1
        }))
      };
    }
    
    console.error('Error analyzing document:', error);
    throw error.response?.data || { message: 'Failed to analyze document' };
  }
};