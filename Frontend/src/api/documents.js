// src/api/documents.js
import apiClient from './client';

const DOCUMENTS_ENDPOINT = '/api/documents'; // Corrected path with /api prefix

export const getDocuments = async () => {
  try {
    const response = await apiClient.get(DOCUMENTS_ENDPOINT);
    return response.data;
  } catch (error) {
    console.error('Error fetching documents:', error);
    throw error.response?.data || { message: 'Failed to retrieve documents' };
  }
};

export const getDocumentStatus = async (id) => {
  try {
    const response = await apiClient.get(`${DOCUMENTS_ENDPOINT}/status/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching document status for ID ${id}:`, error);
    const errorMessage = error.response?.data?.error || error.response?.data?.message || error.message || 'Unknown error';
    throw {
      status: "error",
      message: errorMessage,
      details: error.response?.data
    };
  }
};

export const getDocumentById = async (id) => {
  try {
    const response = await apiClient.get(`${DOCUMENTS_ENDPOINT}/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching document (ID: ${id}):`, error);
    throw error.response?.data || { message: 'Failed to retrieve document' };
  }
};

export const saveDocument = async (documentData, file = null) => {
  try {
    let data = documentData;
    let headers = {};

    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', documentData.title || '');
      formData.append('type', documentData.type || 'article');

      if (documentData.authors && documentData.authors.length > 0) {
        formData.append('authors', JSON.stringify(documentData.authors));
      }

      formData.append('data', JSON.stringify(documentData));
      data = formData;
      headers = { 'Content-Type': 'multipart/form-data' };
    }

    const response = await apiClient.post(DOCUMENTS_ENDPOINT, data, { headers });
    return response.data;
  } catch (error) {
    console.error('Error saving document:', error);
    throw error.response?.data || { message: 'Failed to save document' };
  }
};

export const updateDocument = async (id, documentData) => {
  try {
    const response = await apiClient.put(`${DOCUMENTS_ENDPOINT}/${id}`, documentData);
    return response.data;
  } catch (error) {
    console.error(`Error updating document (ID: ${id}):`, error);
    throw error.response?.data || { message: 'Failed to update document' };
  }
};

export const deleteDocument = async (id) => {
  try {
    await apiClient.delete(`${DOCUMENTS_ENDPOINT}/${id}`);
    return true;
  } catch (error) {
    console.error(`Error deleting document (ID: ${id}):`, error);
    throw error.response?.data || { message: 'Failed to delete document' };
  }
};

export const analyzeDocument = async (formData, progressCallback = null) => {
  try {
    // Use the same apiClient for consistency
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: progressCallback
        ? (progressEvent) => {
            const uploadProgress = Math.round((progressEvent.loaded * 30) / progressEvent.total);
            progressCallback('Uploading file...', uploadProgress);
          }
        : undefined
    };

    const response = await apiClient.post(`${DOCUMENTS_ENDPOINT}/analyze`, formData, config);

    if (response.data.jobId && progressCallback) {
      let completed = false;
      let attempt = 0;

      while (!completed && attempt < 30) {
        attempt++;
        await new Promise(resolve => setTimeout(resolve, Math.min(2000 + attempt * 500, 10000)));

        try {
          const statusResponse = await apiClient.get(`${DOCUMENTS_ENDPOINT}/analyze/${response.data.jobId}`);

          if (statusResponse.data.status === 'completed') {
            completed = true;
            return statusResponse.data.result;
          } else if (statusResponse.data.status === 'processing') {
            const processingProgress = 30 + Math.min(60, attempt * 2);
            progressCallback(statusResponse.data.message || 'Processing document...', processingProgress);
          } else if (statusResponse.data.status === 'error') {
            throw new Error(statusResponse.data.error || 'Analysis failed');
          }
        } catch (pollError) {
          console.error('Error polling analysis status:', pollError);
          if (pollError.message && pollError.message.includes('Network Error')) {
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
    console.error('Error analyzing document:', error);
    throw error.response?.data || { message: 'Failed to analyze document' };
  }
};