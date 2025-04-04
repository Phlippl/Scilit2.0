// src/components/auth/LoginForm.jsx
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
 * Anmeldeformularkomponente
 * 
 * @param {Object} props - Komponentenprops
 * @param {Function} props.onSubmit - Callback für Formularübermittlung
 * @param {boolean} [props.loading] - Ladezustand
 * @param {string} [props.error] - Fehlermeldung
 */
const LoginForm = ({ onSubmit, loading = false, error = '' }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ email, password });
  };
  
  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <TextField
        margin="normal"
        required
        fullWidth
        id="email"
        label="E-Mail-Adresse"
        name="email"
        autoComplete="email"
        autoFocus
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
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={loading}
      />
      
      <Button
        type="submit"
        fullWidth
        variant="contained"
        sx={{ mt: 3, mb: 2, py: 1.2 }}
        disabled={loading}
      >
        {loading ? <CircularProgress size={24} /> : 'Anmelden'}
      </Button>
      
      <Box sx={{ textAlign: 'center', mt: 2 }}>
        <RouterLink to="/register" style={{ textDecoration: 'none' }}>
          <Typography variant="body2" color="primary">
            Noch kein Konto? Registrieren
          </Typography>
        </RouterLink>
      </Box>
    </Box>
  );
};

export default LoginForm;