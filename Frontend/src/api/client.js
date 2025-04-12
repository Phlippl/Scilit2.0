// src/api/client.js
import axios from 'axios';

// Test user config from environment variables
const testUserEnabled = import.meta.env.VITE_TEST_USER_ENABLED === 'true';

// Base API client with configuration
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api', // From environment variables or default
  timeout: 30000, // 30 seconds timeout for long operations like PDF processing
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token-Refresh-Mechanismus
let isRefreshing = false;
let refreshSubscribers = [];

// Funktion zum erneuten Ausführen fehlgeschlagener Anfragen nach Token-Refresh
const subscribeToTokenRefresh = (callback) => {
  refreshSubscribers.push(callback);
};

// Funktion zum Benachrichtigen aller Subscriber nach erfolgreichem Token-Refresh
const onTokenRefreshed = (token) => {
  refreshSubscribers.forEach(callback => callback(token));
  refreshSubscribers = [];
};

// Funktion zum Abbrechen aller ausstehenden Anfragen bei Refresh-Fehler
const onRefreshError = (error) => {
  refreshSubscribers = [];
  isRefreshing = false;
  
  // Benachrichtigung für Abmeldung auslösen
  const authErrorEvent = new CustomEvent('auth:error', {
    detail: { status: 401, message: 'Sitzung abgelaufen' }
  });
  window.dispatchEvent(authErrorEvent);
};

// Request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Debugging: Log outgoing requests
    console.log(`Request: ${config.method.toUpperCase()} ${config.url}`);
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for unified error handling
apiClient.interceptors.response.use(
  (response) => {
    // Debugging: Log successful responses
    console.log(`Response: ${response.status} ${response.config.url}`);
    return response;
  },
  async (error) => {
    // Handle test user mode when API is not available
    if (testUserEnabled && (!error.response || error.code === 'ERR_NETWORK')) {
      console.warn('API not available, using test mode fallbacks');
      
      // Return with flag for test mode
      return Promise.reject({
        ...error,
        isTestMode: true
      });
    }
    
    // Log detailed error information
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    
    // Token-Refresh-Logik für 401 (Unauthorized)
    if (error.response && error.response.status === 401) {
      const originalRequest = error.config;
      
      // Verhindere unendliche Loops (wenn Refresh-Anfrage selbst 401 zurückgibt)
      if (originalRequest.url.includes('/api/auth/refresh')) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        onRefreshError(error);
        return Promise.reject(error);
      }
      
      // Prüfe, ob wir bereits einen Refresh durchführen
      if (!isRefreshing) {
        isRefreshing = true;
        
        // Token-Refresh versuchen
        try {
          const token = localStorage.getItem('auth_token');
          
          if (!token) {
            throw new Error("Kein Token vorhanden");
          }
          
          // Anfrage zum Token-Refresh
          const response = await axios.post('/api/auth/refresh', {}, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          });
          
          // Speichere neuen Token
          const newToken = response.data.token;
          localStorage.setItem('auth_token', newToken);
          
          // Aktualisiere auch Benutzerdaten wenn vorhanden
          if (response.data.user) {
            localStorage.setItem('user_data', JSON.stringify(response.data.user));
          }
          
          // Setze neuen Token für alle weiteren Anfragen
          apiClient.defaults.headers.Authorization = `Bearer ${newToken}`;
          
          // Benachrichtige alle wartenden Anfragen
          onTokenRefreshed(newToken);
          isRefreshing = false;
          
          // Wiederhole die Originalanfrage mit dem neuen Token
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          console.error('Token-Refresh fehlgeschlagen:', refreshError);
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_data');
          onRefreshError(refreshError);
          return Promise.reject(refreshError);
        }
      } else {
        // Anfrage zu den Subscribers hinzufügen, wenn bereits ein Refresh läuft
        return new Promise(resolve => {
          subscribeToTokenRefresh(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(originalRequest));
          });
        });
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;