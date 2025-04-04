// src/api/auth.js
import axios from 'axios';

const API_URL = '/api/auth';

export const login = async (credentials) => {
  try {
    const response = await axios.post(`${API_URL}/login`, credentials);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Login failed' };
  }
};

export const register = async (userData) => {
  try {
    const response = await axios.post(`${API_URL}/register`, userData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Registration failed' };
  }
};

export const logout = async () => {
  try {
    await axios.post(`${API_URL}/logout`);
    return true;
  } catch (error) {
    console.error('Logout error:', error);
    return false;
  }
};