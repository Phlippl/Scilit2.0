import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Paper, 
  Box, 
  Typography, 
  TextField, 
  Button, 
  Link, 
  Alert, 
  CircularProgress 
} from '@mui/material';
import { AuthContext } from '../App';
import axios from 'axios';

const Register = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();
  const auth = useContext(AuthContext);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validate form
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    
    setLoading(true);
    
    try {
      // In a real app, you would connect this to your backend API
      // For demo purposes, we'll simulate a successful registration
      
      // Mock API call
      // const response = await axios.post('/api/auth/register', { name, email, password });
      
      // Simulating a successful response
      setTimeout(() => {
        const userData = {
          id: '1',
          name: name,
          email: email,
        };
        
        // Update auth context
        auth.handleLogin(userData);
        
        // Navigate to dashboard
        navigate('/dashboard');
        
        setLoading(false);
      }, 1000);
    } catch (error) {
      setError(error.response?.data?.message || 'Registration failed. Please try again.');
      setLoading(false);
    }
  };
  
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mt: 4 }}>
      <Paper elevation={3} sx={{ p: 4, maxWidth: 400, width: '100%' }}>
        <Typography variant="h5" component="h1" align="center" gutterBottom>
          Create Account
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
          <TextField
            margin="normal"
            required
            fullWidth
            id="name"
            label="Full Name"
            name="name"
            autoComplete="name"
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          
          <TextField
            margin="normal"
            required
            fullWidth
            id="email"
            label="Email Address"
            name="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          
          <TextField
            margin="normal"
            required
            fullWidth
            name="password"
            label="Password"
            type="password"
            id="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          
          <TextField
            margin="normal"
            required
            fullWidth
            name="confirmPassword"
            label="Confirm Password"
            type="password"
            id="confirmPassword"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2, py: 1.2 }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Sign Up'}
          </Button>
          
          <Box sx={{ textAlign: 'center', mt: 2 }}>
            <Link href="/login" variant="body2">
              {"Already have an account? Sign In"}
            </Link>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default Register;