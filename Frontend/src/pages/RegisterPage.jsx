// src/pages/RegisterPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Paper, Box, Typography } from '@mui/material';
import RegisterForm from '../components/auth/RegisterForm';
import { useAuth } from '../hooks/useAuth';

const RegisterPage = () => {
  const { register, isAuthenticated, error: authError, loading } = useAuth();
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
  
  const handleSubmit = async (userData) => {
    try {
      setError('');
      await register(userData);
      // Bei Erfolg erfolgt automatische Weiterleitung durch useEffect oben
    } catch (error) {
      setError(error.message || 'Registrierung fehlgeschlagen. Bitte versuche es erneut.');
    }
  };
  
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 4 }}>
      <Paper elevation={3} sx={{ p: 4, maxWidth: 400, width: '100%' }}>
        <Typography variant="h5" component="h1" align="center" gutterBottom>
          Konto erstellen
        </Typography>
        
        <RegisterForm 
          onSubmit={handleSubmit}
          loading={loading}
          error={error}
        />
      </Paper>
    </Box>
  );
};

export default RegisterPage;