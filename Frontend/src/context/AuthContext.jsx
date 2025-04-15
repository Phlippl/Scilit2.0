// src/context/AuthContext.jsx
import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
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
  const refreshTimerRef = useRef(null);

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
    
    // Clear refresh timer
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  /**
   * Set up a token refresh timer
   * Refreshes the token 30 minutes before it expires
   */
  const setupRefreshTimer = useCallback(() => {
    // Clear any existing timer
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    
    // Calculate time until refresh (token valid for 24h, refresh 30min before expiry)
    const timeUntilRefresh = 23.5 * 60 * 60 * 1000; // 23.5 hours in milliseconds
    
    // Set new timer
    refreshTimerRef.current = setTimeout(async () => {
      console.log('Token refresh timer triggered');
      try {
        await refreshToken();
        console.log('Token refreshed successfully');
      } catch (err) {
        console.error('Failed to refresh token:', err);
        // If refresh fails, log out the user
        handleLogout(false);
      }
    }, timeUntilRefresh);
    
    console.log('Token refresh timer set for 23.5 hours from now');
  }, [handleLogout]);

  /**
   * Check authentication status on first load
   */
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Get token from localStorage
        const token = localStorage.getItem('auth_token');
        
        if (token) {
          // Ensure we have default headers set properly
          apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
          
          // Get user data
          const userData = JSON.parse(localStorage.getItem('user_data') || 'null');
          
          if (userData) {
            setUser(userData);
            setIsAuthenticated(true);
            setLoading(false);
            // Set up token refresh timer whenever authenticated
            setupRefreshTimer();
          } else {
            // Clear potentially invalid auth data
            handleLogout(false);
            setLoading(false);
          }
        } else {
          setLoading(false);
        }
      } catch (err) {
        console.error('Auth check error:', err);
        handleLogout(false);
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
      // Clear refresh timer on unmount
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [handleLogout, setupRefreshTimer]);

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
      
      // Set up a new refresh timer
      setupRefreshTimer();
      
      return response.user;
    } catch (err) {
      console.error('Token refresh failed:', err);
      handleLogout(false); // Logout on refresh failure
      return null;
    } finally {
      setLoading(false);
    }
  }, [handleLogout, setupRefreshTimer]);

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
      
      // Set up refresh timer
      setupRefreshTimer();
      
      return response.user;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Login failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [setupRefreshTimer]);

  /**
   * Handle registration
   */
  const handleRegister = useCallback(async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
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
  }, [handleLogin]);

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