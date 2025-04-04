// src/context/AuthContext.jsx
import React, { createContext, useState, useEffect, useCallback } from 'react';
import * as authApi from '../api/auth';
import apiClient from '../api/client';

// Auth-Context erstellen
export const AuthContext = createContext();

/**
 * Auth-Provider für Authentifizierungszustand und -funktionen
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Beim ersten Laden den Auth-Status prüfen
   */
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Token aus localStorage holen
        const token = localStorage.getItem('auth_token');
        
        if (token) {
          // Axios-Default-Header setzen
          apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
          
          // Benutzerdaten holen
          const userData = JSON.parse(localStorage.getItem('user_data'));
          
          if (userData) {
            setUser(userData);
            setIsAuthenticated(true);
          } else {
            // Wenn keine Benutzerdaten, aber Token vorhanden, versuche /me API
            try {
              const response = await authApi.getCurrentUser();
              setUser(response.user);
              setIsAuthenticated(true);
              localStorage.setItem('user_data', JSON.stringify(response.user));
            } catch (userError) {
              // Bei Fehler: Auth-Daten löschen
              handleLogout(false); // Silent = true, keine API-Anfrage
            }
          }
        }
      } catch (err) {
        console.error('Auth-Check-Fehler:', err);
        // Potenziell ungültige Auth-Daten löschen
        handleLogout(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
    
    // Listener für Auth-Fehler (z.B. 401 von anderen API-Anfragen)
    const handleAuthError = (e) => {
      handleLogout(false);
    };
    
    window.addEventListener('auth:error', handleAuthError);
    
    return () => {
      window.removeEventListener('auth:error', handleAuthError);
    };
  }, []);

  /**
   * Anmeldung behandeln
   */
  const handleLogin = useCallback(async (credentials) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authApi.login(credentials);
      
      // Token und Benutzerdaten speichern
      localStorage.setItem('auth_token', response.token);
      localStorage.setItem('user_data', JSON.stringify(response.user));
      
      // Axios-Default-Header für nachfolgende Anfragen setzen
      apiClient.defaults.headers.common.Authorization = `Bearer ${response.token}`;
      
      setUser(response.user);
      setIsAuthenticated(true);
      
      return response.user;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Anmeldung fehlgeschlagen';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Registrierung behandeln
   */
  const handleRegister = useCallback(async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authApi.register(userData);
      
      // Nach erfolgreicher Registrierung automatisch anmelden
      await handleLogin({
        email: userData.email,
        password: userData.password
      });
      
      return response;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Registrierung fehlgeschlagen';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [handleLogin]);

  /**
   * Abmeldung behandeln
   * 
   * @param {boolean} callApi - Flag, ob die Logout-API aufgerufen werden soll
   */
  const handleLogout = useCallback(async (callApi = true) => {
    if (callApi) {
      try {
        await authApi.logout();
      } catch (err) {
        console.error('Logout-Fehler:', err);
      }
    }
    
    // Aufräumen unabhängig vom API-Erfolg
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    delete apiClient.defaults.headers.common.Authorization;
    setUser(null);
    setIsAuthenticated(false);
  }, []);
  
  /**
   * Benutzerdaten aktualisieren
   */
  const updateUserData = useCallback((newUserData) => {
    setUser(prev => {
      const updatedUser = { ...prev, ...newUserData };
      localStorage.setItem('user_data', JSON.stringify(updatedUser));
      return updatedUser;
    });
  }, []);

  // Context-Wert erstellen
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