// src/api/documents.js
import axios from 'axios';

const API_URL = '/api/documents';

export const getDocuments = async () => {
  try {
    const response = await axios.get(API_URL);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Failed to fetch documents' };
  }
};

export const getDocumentById = async (id) => {
  try {
    const response = await axios.get(`${API_URL}/${id}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Failed to fetch document' };
  }
};

export const saveDocument = async (documentData) => {
  try {
    const response = await axios.post(API_URL, documentData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Failed to save document' };
  }
};

export const deleteDocument = async (id) => {
  try {
    await axios.delete(`${API_URL}/${id}`);
    return true;
  } catch (error) {
    throw error.response?.data || { message: 'Failed to delete document' };
  }
};