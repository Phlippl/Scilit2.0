// src/components/auth/RegisterForm.jsx
import React, { useState } from 'react';
import { 
  Box, 
  TextField, 
  Button, 
  Typography, 
  Link, 
  Alert, 
  CircularProgress 
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

/**
 * Registrierungsformularkomponente
 * 
 * @param {Object} props - Komponentenprops
 * @param {Function} props.onSubmit - Callback für Formularübermittlung
 * @param {boolean} [props.loading] - Ladezustand
 * @param {string} [props.error] - Fehlermeldung
 */
const RegisterForm = ({ onSubmit, loading = false, error = '' }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Formularvalidierung
    if (password !== confirmPassword) {
      setValidationError('Passwörter stimmen nicht überein');
      return;
    }
    
    setValidationError('');
    onSubmit({ name, email, password });
  };
  
  const displayError = validationError || error;
  
  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
      {displayError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {displayError}
        </Alert>
      )}
      
      <TextField
        margin="normal"
        required
        fullWidth
        id="name"
        label="Vollständiger Name"
        name="name"
        autoComplete="name"
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={loading}
      />
      
      <TextField
        margin="normal"
        required
        fullWidth
        id="email"
        label="E-Mail-Adresse"
        name="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={loading}
      />
      
      <TextField
        margin="normal"
        required
        fullWidth
        name="password"
        label="Passwort"
        type="password"
        id="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={loading}
      />
      
      <TextField
        margin="normal"
        required
        fullWidth
        name="confirmPassword"
        label="Passwort bestätigen"
        type="password"
        id="confirmPassword"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        disabled={loading}
      />
      
      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2, py: 1.2 }}
        disabled={loading}
      >
        {loading ? <CircularProgress size={24} /> : 'Registrieren'}
      </Button>
      
      <Box sx={{ textAlign: 'center', mt: 2 }}>
        <RouterLink to="/login" style={{ textDecoration: 'none' }}>
          <Typography variant="body2" color="primary">
            Bereits ein Konto? Anmelden
          </Typography>
        </RouterLink>
      </Box>
    </Box>
  );
};

export default RegisterForm;