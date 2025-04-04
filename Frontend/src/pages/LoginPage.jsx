// src/pages/LoginPage.jsx
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
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';

import LoginForm from '../components/auth/LoginForm';
import { useAuth } from '../hooks/useAuth';

const LoginPage = () => {
  const { login, isAuthenticated, loading: authLoading, error: authError } = useAuth();
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
  
  // Handle login form submission
  const handleLogin = async (credentials) => {
    setLoading(true);
    setError('');
    
    try {
      await login(credentials);
      // Redirect is handled by the above useEffect
    } catch (err) {
      setError(err.message || 'Login failed');
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
          <LockOutlinedIcon />
        </Avatar>
        
        <Typography component="h1" variant="h5">
          Log in to SciLit2.0
        </Typography>
        
        <Paper 
          elevation={3} 
          sx={{ 
            p: 4, 
            mt: 3, 
            width: '100%' 
          }}
        >
          <LoginForm 
            onSubmit={handleLogin} 
            loading={loading || authLoading} 
            error={error || authError} 
          />
        </Paper>
      </Box>
    </Container>
  );
};

export default LoginPage;