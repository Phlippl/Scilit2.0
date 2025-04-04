// src/api/client.js - Basis-API-Client mit Konfiguration
import axios from 'axios';

// Basis-API-Client mit Konfiguration
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api', // Aus Umgebungsvariablen oder Standard
  timeout: 30000, // 30 Sekunden Timeout für lange Operationen wie PDF-Verarbeitung
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request-Interceptor für Authentifizierung
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response-Interceptor für einheitliche Fehlerbehandlung
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Automatisches Logout bei 401 (Unauthorized)
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;