// src/pages/RegisterPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Container, 
  Box, 
  Paper, 
  Typography, 
  Avatar, 
  CircularProgress 
} from '@mui/material';
import PersonAddIcon from '@mui/icons-material/PersonAdd';

import RegisterForm from '../components/auth/RegisterForm';
import { useAuth } from '../hooks/useAuth';

const RegisterPage = () => {
  const { register, isAuthenticated, loading: authLoading, error: authError } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();
  const location = useLocation();
  
  // Redirect to intended destination if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      const from = location.state?.from || '/dashboard';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);
  
  // Handle registration form submission
  const handleRegister = async (userData) => {
    setLoading(true);
    setError('');
    
    try {
      await register(userData);
      // Redirect is handled by the above useEffect
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Container maxWidth="xs">
      <Box
        sx={{
          mt: 8,
          mb: 4,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Avatar sx={{ m: 1, bgcolor: 'secondary.main' }}>
          <PersonAddIcon />
        </Avatar>
        
        <Typography component="h1" variant="h5">
          Create an Account
        </Typography>
        
        <Paper 
          elevation={3} 
          sx={{ 
            p: 4, 
            mt: 3, 
            width: '100%' 
          }}
        >
          <RegisterForm 
            onSubmit={handleRegister} 
            loading={loading || authLoading} 
            error={error || authError} 
          />
        </Paper>
      </Box>
    </Container>
  );
};

export default RegisterPage;