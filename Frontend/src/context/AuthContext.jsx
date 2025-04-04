// src/context/AuthContext.jsx
import React, { createContext, useState, useEffect, useCallback } from 'react';
import * as authApi from '../api/auth';
import apiClient from '../api/client';

// Create Auth Context
export const AuthContext = createContext();

/**
 * Auth Provider for authentication state and functions
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Check authentication status on first load
   */
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Get token from localStorage
        const token = localStorage.getItem('auth_token');
        
        if (token) {
          // Set Axios default header
          apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
          
          // Get user data
          const userData = JSON.parse(localStorage.getItem('user_data'));
          
          if (userData) {
            setUser(userData);
            setIsAuthenticated(true);
          } else {
            // If no user data but token exists, try /me API
            try {
              const response = await authApi.getCurrentUser();
              setUser(response.user);
              setIsAuthenticated(true);
              localStorage.setItem('user_data', JSON.stringify(response.user));
            } catch (userError) {
              // On error: Clear auth data
              handleLogout(false); // Silent = true, no API request
            }
          }
        }
      } catch (err) {
        console.error('Auth check error:', err);
        // Clear potentially invalid auth data
        handleLogout(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
    
    // Listener for auth errors (e.g., 401 from other API requests)
    const handleAuthError = (e) => {
      handleLogout(false);
    };
    
    window.addEventListener('auth:error', handleAuthError);
    
    return () => {
      window.removeEventListener('auth:error', handleAuthError);
    };
  }, []);

  /**
   * Handle login
   */
  const handleLogin = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authApi.login(credentials);
      
      // Store token and user data
      localStorage.setItem('auth_token', response.token);
      localStorage.setItem('user_data', JSON.stringify(response.user));
      
      // Set Axios default header for subsequent requests
      apiClient.defaults.headers.common.Authorization = `Bearer ${response.token}`;
      
      setUser(response.user);
      setIsAuthenticated(true);
      
      return response.user;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Login failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Handle registration
   */
  const handleRegister = useCallback(async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authApi.register(userData);
      
      // Auto login after successful registration
      await handleLogin({
        email: userData.email,
        password: userData.password
      });
      
      return response;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Registration failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [handleLogin]);

  /**
   * Handle logout
   * 
   * @param {boolean} callApi - Flag to call the logout API
   */
  const handleLogout = useCallback(async (callApi = true) => {
    if (callApi) {
      try {
        await authApi.logout();
      } catch (err) {
        console.error('Logout error:', err);
      }
    }
    
    // Clean up regardless of API success
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    delete apiClient.defaults.headers.common.Authorization;
    setUser(null);
    setIsAuthenticated(false);
  }, []);
  
  /**
   * Update user data
   */
  const updateUserData = useCallback((newUserData) => {
    setUser(prev => {
      const updatedUser = { ...prev, ...newUserData };
      localStorage.setItem('user_data', JSON.stringify(updatedUser));
      return updatedUser;
    });
  }, []);

  // Create context value
  const contextValue = {
    user,
    isAuthenticated,
    loading,
    error,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
    updateUserData
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};