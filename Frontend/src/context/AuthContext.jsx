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

  // Test user config from environment variables
  const testUserEnabled = import.meta.env.VITE_TEST_USER_ENABLED === 'true';
  const testUserEmail = import.meta.env.VITE_TEST_USER_EMAIL || '';
  const testUserPassword = import.meta.env.VITE_TEST_USER_PASSWORD || '';
  const testUserName = import.meta.env.VITE_TEST_USER_NAME || 'Test User';

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
   * Refresh token method - attempts to get a new token using the existing one
   */
  const refreshToken = useCallback(async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) return null;
    
    try {
      setLoading(true);
      const response = await authApi.refreshToken();
      
      // Update token and user data
      localStorage.setItem('auth_token', response.token);
      localStorage.setItem('user_data', JSON.stringify(response.user));
      
      // Update axios header for subsequent requests
      apiClient.defaults.headers.common.Authorization = `Bearer ${response.token}`;
      
      setUser(response.user);
      setIsAuthenticated(true);
      
      return response.user;
    } catch (err) {
      console.error('Token refresh failed:', err);
      handleLogout(false); // Logout on refresh failure
      return null;
    } finally {
      setLoading(false);
    }
  }, [handleLogout]);

  /**
   * Check authentication status on first load and set up listeners
   */
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Get token from localStorage
        const token = localStorage.getItem('auth_token');
        
        if (token) {
          // Ensure we have default headers set properly
          apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
          
          // Get user data or try to refresh token if needed
          try {
            const userData = JSON.parse(localStorage.getItem('user_data') || 'null');
            
            if (userData) {
              setUser(userData);
              setIsAuthenticated(true);
            } else {
              // Try to refresh token if we have token but no user data
              const refreshedUser = await refreshToken();
              if (!refreshedUser) {
                handleLogout(false);
              }
            }
          } catch (e) {
            console.error('Error parsing user data:', e);
            // Try to refresh token if we had an error
            const refreshedUser = await refreshToken();
            if (!refreshedUser) {
              handleLogout(false);
            }
          }
        } else {
          // No token, ensure logged out state
          handleLogout(false);
        }
      } catch (err) {
        console.error('Auth check error:', err);
        handleLogout(false);
      } finally {
        setLoading(false);
      }
    };
  
    checkAuthStatus();
    
    // Listener for auth errors (e.g., 401 from other API requests)
    const handleAuthError = (e) => {
      console.log('Auth error event received', e);
      handleLogout(false);
    };
    
    window.addEventListener('auth:error', handleAuthError);
    
    return () => {
      window.removeEventListener('auth:error', handleAuthError);
    };
  }, [handleLogout, refreshToken]);

  /**
   * Handle login
   */
  const handleLogin = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    
    try {
      // Check if test user is enabled and credentials match
      if (testUserEnabled && 
          credentials.email === testUserEmail && 
          credentials.password === testUserPassword) {
        
        console.log('Using test user login');
        
        // Create mock user and token
        const mockUser = {
          id: 'test-user-id',
          email: testUserEmail,
          name: testUserName,
          role: 'admin'
        };
        
        const mockToken = 'test-user-token';
        
        // Store token and user data
        localStorage.setItem('auth_token', mockToken);
        localStorage.setItem('user_data', JSON.stringify(mockUser));
        
        // Set axios header for subsequent requests
        apiClient.defaults.headers.common.Authorization = `Bearer ${mockToken}`;
        
        setUser(mockUser);
        setIsAuthenticated(true);
        
        return mockUser;
      }
      
      // Regular login if not using test user
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
  }, [testUserEnabled, testUserEmail, testUserPassword, testUserName]);

  /**
   * Handle registration
   */
  const handleRegister = useCallback(async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      // For test user, simulate successful registration and auto-login
      if (testUserEnabled && userData.email === testUserEmail) {
        console.log('Using test user registration');
        
        // Auto login after successful registration
        await handleLogin({
          email: userData.email,
          password: userData.password
        });
        
        return { success: true, user: { ...userData, id: 'test-user-id' } };
      }
      
      // Regular registration flow
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
  }, [handleLogin, testUserEnabled, testUserEmail]);

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
    refreshToken,
    updateUserData
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};