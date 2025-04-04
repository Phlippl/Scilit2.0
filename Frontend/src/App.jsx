// src/App.jsx
import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { CircularProgress, Box } from '@mui/material';

// Layout-Komponente
import Navbar from './components/common/Navbar';

// Pages
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import QueryPage from './pages/QueryPage';

// Contexts
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';

// PrivateRoute-Komponente für geschützte Routen
const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  // Zeige Ladebildschirm während Authentifizierungsprüfung
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Hauptkomponente App
function App() {
  const theme = createTheme({
    palette: {
      mode: 'light',
      primary: {
        main: '#1976d2',
      },
      secondary: {
        main: '#dc004e',
      },
    },
    typography: {
      fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    },
  });

  return (
    <AuthProvider>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Navbar />
          
          <Box component="main" sx={{ flexGrow: 1, py: 4, px: 2 }}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              
              <Route 
                path="/dashboard" 
                element={
                  <PrivateRoute>
                    <DashboardPage />
                  </PrivateRoute>
                } 
              />
              
              <Route 
                path="/upload" 
                element={
                  <PrivateRoute>
                    <UploadPage />
                  </PrivateRoute>
                } 
              />
              
              <Route 
                path="/query" 
                element={
                  <PrivateRoute>
                    <QueryPage />
                  </PrivateRoute>
                } 
              />
              
              {/* Fallback für ungültige Routen */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Box>
          
          <Box component="footer" sx={{ p: 2, mt: 'auto', backgroundColor: 'rgba(0, 0, 0, 0.05)' }}>
            <Typography variant="body2" color="text.secondary" align="center">
              © {new Date().getFullYear()} SciLit2.0 - Wissenschaftliche Literaturverwaltung
            </Typography>
          </Box>
        </Box>
      </ThemeProvider>
    </AuthProvider>
  );
}

export default App;