// src/context/AuthContext.jsx
import React, { createContext, useState, useEffect } from 'react';
import * as authApi from '../api/auth';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check for existing session/token on app load
    const checkAuthStatus = async () => {
      try {
        // Get token from localStorage
        const token = localStorage.getItem('auth_token');
        
        if (token) {
          // Set axios default header
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          
          // Get user data
          const userData = JSON.parse(localStorage.getItem('user_data'));
          
          if (userData) {
            setUser(userData);
            setIsAuthenticated(true);
          }
        }
      } catch (err) {
        console.error('Auth check error:', err);
        // Clear potentially invalid auth data
        handleLogout();
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  const handleLogin = async (credentials) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authApi.login(credentials);
      
      // Store token and user data
      localStorage.setItem('auth_token', response.token);
      localStorage.setItem('user_data', JSON.stringify(response.user));
      
      // Set axios default header for subsequent requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.token}`;
      
      setUser(response.user);
      setIsAuthenticated(true);
      return response.user;
    } catch (err) {
      setError(err.message || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authApi.register(userData);
      
      // Automatically log in after successful registration
      await handleLogin({
        email: userData.email,
        password: userData.password
      });
      
      return response;
    } catch (err) {
      setError(err.message || 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Clean up regardless of API success
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
      delete axios.defaults.headers.common['Authorization'];
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        loading,
        error,
        login: handleLogin,
        register: handleRegister,
        logout: handleLogout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};