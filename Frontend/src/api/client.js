// src/api/client.js
import axios from 'axios';

// Base API client with configuration
const apiClient = axios.create({
  // Use the correct base URL format - ensure it doesn't add double /api
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  timeout: 30000,
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
    detail: { status: 401, message: 'Session expired' }
  });
  window.dispatchEvent(authErrorEvent);
};

// Standardisierte Fehlerobjekt-Erstellung
const createErrorObject = (error) => {
  return {
    url: error.config?.url,
    method: error.config?.method,
    status: error.response?.status,
    statusText: error.response?.statusText,
    data: error.response?.data,
    message: error.response?.data?.message || error.response?.data?.error || error.message,
    timestamp: new Date().toISOString()
  };
};

// Request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add request timestamp for timing metrics
    config.metadata = { startTime: new Date().getTime() };
    
    return config;
  },
  (error) => {
    console.error('Request error:', createErrorObject(error));
    return Promise.reject(error);
  }
);

// Response interceptor for unified error handling
apiClient.interceptors.response.use(
  (response) => {
    // Calculate request duration for performance monitoring
    const requestDuration = response.config.metadata 
      ? new Date().getTime() - response.config.metadata.startTime 
      : undefined;
    
    // Log slow requests
    if (requestDuration && requestDuration > 5000) {
      console.warn(`Slow request detected: ${response.config.url} took ${requestDuration}ms`);
    }
    
    return response;
  },
  async (error) => {
    // Create standardized error object for logging and handling
    const errorObj = createErrorObject(error);
    
    // Log detailed error information
    console.error('API Error:', errorObj);
    
    // Token-Refresh-Logik für 401 (Unauthorized)
    if (error.response && error.response.status === 401) {
      const originalRequest = error.config;
      
      // Prevent infinite loops (if the refresh request itself returns 401)
      if (originalRequest.url.includes('/api/auth/refresh')) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        onRefreshError(error);
        return Promise.reject(error);
      }
      
      // Check if we're already refreshing
      if (!isRefreshing) {
        isRefreshing = true;
        
        try {
          const token = localStorage.getItem('auth_token');
          
          if (!token) {
            throw new Error("No token available");
          }
          
          // Request to refresh token - use the complete path
          const response = await axios.post(`${apiClient.defaults.baseURL}/api/auth/refresh`, {}, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          });
          
          // Store new token
          const newToken = response.data.token;
          localStorage.setItem('auth_token', newToken);
          
          // Update user data if available
          if (response.data.user) {
            localStorage.setItem('user_data', JSON.stringify(response.data.user));
          }
          
          // Set new token for all future requests
          apiClient.defaults.headers.Authorization = `Bearer ${newToken}`;
          
          // Notify all waiting requests
          onTokenRefreshed(newToken);
          isRefreshing = false;
          
          // Retry the original request with the new token
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_data');
          onRefreshError(refreshError);
          return Promise.reject(refreshError);
        }
      } else {
        // Add request to subscribers if refresh is already in progress
        return new Promise(resolve => {
          subscribeToTokenRefresh(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(originalRequest));
          });
        });
      }
    }
    
    // Handle specific error types
    if (error.response) {
      // Server responded with error status (4xx, 5xx)
      switch (error.response.status) {
        case 403:
          // Forbidden - User doesn't have permission
          window.dispatchEvent(new CustomEvent('api:permission-denied', {
            detail: errorObj
          }));
          break;
        case 404:
          // Not found
          window.dispatchEvent(new CustomEvent('api:not-found', {
            detail: errorObj
          }));
          break;
        case 408:
        case 504:
          // Timeout
          window.dispatchEvent(new CustomEvent('api:timeout', {
            detail: errorObj
          }));
          break;
        case 500:
        case 502:
        case 503:
          // Server error
          window.dispatchEvent(new CustomEvent('api:server-error', {
            detail: errorObj
          }));
          break;
      }
    } else if (error.request) {
      // Request made but no response received (network error)
      window.dispatchEvent(new CustomEvent('api:network-error', {
        detail: errorObj
      }));
    }
    
    // Add standardized error object to the error
    error.errorData = errorObj;
    
    return Promise.reject(error);
  }
);

export default apiClient;