// src/api/auth.js
import apiClient from './client';

const AUTH_ENDPOINT = '/api/auth';

/**
 * Logs in a user with the provided credentials
 * 
 * @param {Object} credentials - User credentials
 * @param {string} credentials.email - User email
 * @param {string} credentials.password - User password
 * @returns {Promise<Object>} User data and token
 */
export const login = async (credentials) => {
  try {
    const response = await apiClient.post(`${AUTH_ENDPOINT}/login`, credentials);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Login failed' };
  }
};

/**
 * Registers a new user
 * 
 * @param {Object} userData - User registration data
 * @param {string} userData.name - User full name
 * @param {string} userData.email - User email
 * @param {string} userData.password - User password
 * @returns {Promise<Object>} Registered user data
 */
export const register = async (userData) => {
  try {
    const response = await apiClient.post(`${AUTH_ENDPOINT}/register`, userData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Registration failed' };
  }
};

/**
 * Logs out the current user
 * 
 * @returns {Promise<boolean>} Success status
 */
export const logout = async () => {
  try {
    await apiClient.post(`${AUTH_ENDPOINT}/logout`);
    return true;
  } catch (error) {
    console.error('Logout error:', error);
    return false;
  }
};

/**
 * Gets the current user data
 * 
 * @returns {Promise<Object>} Current user data
 */
export const getCurrentUser = async () => {
  try {
    const response = await apiClient.get(`${AUTH_ENDPOINT}/me`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Failed to get user data' };
  }
};

/**
 * Refreshes an expired token
 * 
 * @returns {Promise<Object>} New token and user data
 */
export const refreshToken = async () => {
  try {
    const response = await apiClient.post(`${AUTH_ENDPOINT}/refresh`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { message: 'Token refresh failed' };
  }
};