// src/api/documents.js
import apiClient from './client';

const ENDPOINT = '/documents';

/**
 * Holt alle Dokumente des angemeldeten Benutzers
 * @returns {Promise<Array>} - Liste der Dokumente
 */
export const getDocuments = async () => {
  try {
    const response = await apiClient.get(ENDPOINT);
    return response.data;
  } catch (error) {
    console.error('Fehler beim Abrufen der Dokumente:', error);
    throw error.response?.data || { 
      message: 'Dokumente konnten nicht abgerufen werden' 
    };
  }
};

/**
 * Holt ein bestimmtes Dokument nach ID
 * @param {string} id - Dokument-ID
 * @returns {Promise<Object>} - Dokument-Daten
 */
export const getDocumentById = async (id) => {
  try {
    const response = await apiClient.get(`${ENDPOINT}/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Fehler beim Abrufen des Dokuments (ID: ${id}):`, error);
    throw error.response?.data || { 
      message: 'Dokument konnte nicht abgerufen werden' 
    };
  }
};

/**
 * Speichert ein neues Dokument mit Metadaten und Dateiinhalt
 * 
 * @param {Object} documentData - Dokument-Daten mit Metadaten
 * @param {File} [file] - Optionale PDF-Datei (falls noch nicht im documentData enthalten)
 * @returns {Promise<Object>} - Gespeichertes Dokument mit ID
 */
export const saveDocument = async (documentData, file = null) => {
  try {
    let data = documentData;
    
    // Wenn eine separate Datei übergeben wurde, erstelle FormData
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      
      // Füge documentData als JSON-String hinzu
      formData.append('data', JSON.stringify(documentData));
      
      data = formData;
    }
    
    const response = await apiClient.post(ENDPOINT, data, {
      headers: file ? {
        'Content-Type': 'multipart/form-data'
      } : {}
    });
    
    return response.data;
  } catch (error) {
    console.error('Fehler beim Speichern des Dokuments:', error);
    throw error.response?.data || { 
      message: 'Dokument konnte nicht gespeichert werden' 
    };
  }
};

/**
 * Aktualisiert ein bestehendes Dokument
 * 
 * @param {string} id - Dokument-ID
 * @param {Object} documentData - Zu aktualisierende Daten
 * @returns {Promise<Object>} - Aktualisiertes Dokument
 */
export const updateDocument = async (id, documentData) => {
  try {
    const response = await apiClient.put(`${ENDPOINT}/${id}`, documentData);
    return response.data;
  } catch (error) {
    console.error(`Fehler beim Aktualisieren des Dokuments (ID: ${id}):`, error);
    throw error.response?.data || { 
      message: 'Dokument konnte nicht aktualisiert werden' 
    };
  }
};

/**
 * Löscht ein Dokument
 * 
 * @param {string} id - Dokument-ID
 * @returns {Promise<boolean>} - Erfolg
 */
export const deleteDocument = async (id) => {
  try {
    await apiClient.delete(`${ENDPOINT}/${id}`);
    return true;
  } catch (error) {
    console.error(`Fehler beim Löschen des Dokuments (ID: ${id}):`, error);
    throw error.response?.data || { 
      message: 'Dokument konnte nicht gelöscht werden' 
    };
  }
};