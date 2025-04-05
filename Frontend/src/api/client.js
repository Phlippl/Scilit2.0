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
  (error) => {
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
    
    // Automatic logout on 401 (Unauthorized)
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_data');
      
      // For React Router v6: Optionally trigger a global event for auth errors
      const authErrorEvent = new CustomEvent('auth:error', {
        detail: { status: 401, message: 'Session expired' }
      });
      window.dispatchEvent(authErrorEvent);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;