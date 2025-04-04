// src/pages/LoginPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Paper, Box, Typography } from '@mui/material';
import LoginForm from '../components/auth/LoginForm';
import { useAuth } from '../hooks/useAuth';

const LoginPage = () => {
  const { login, isAuthenticated, error: authError, loading } = useAuth();
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  
  // Weiterleitung, wenn der Benutzer bereits angemeldet ist
  useEffect(() => {
    if (isAuthenticated) {
      const redirectPath = location.state?.from || '/dashboard';
      navigate(redirectPath, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);
  
  // Bei AuthContext-Fehler
  useEffect(() => {
    if (authError) {
      setError(authError);
    }
  }, [authError]);
  
  const handleSubmit = async (credentials) => {
    try {
      setError('');
      await login(credentials);
      // Bei Erfolg erfolgt automatische Weiterleitung durch useEffect oben
    } catch (error) {
      setError(error.message || 'Anmeldung fehlgeschlagen. Bitte überprüfe deine Anmeldedaten.');
    }
  };
  
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 4 }}>
      <Paper elevation={3} sx={{ p: 4, maxWidth: 400, width: '100%' }}>
        <Typography variant="h5" component="h1" align="center" gutterBottom>
          Anmelden
        </Typography>
        
        <LoginForm 
          onSubmit={handleSubmit}
          loading={loading}
          error={error}
        />
      </Paper>
    </Box>
  );
};

export default LoginPage;