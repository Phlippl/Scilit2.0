// src/components/common/Footer.jsx
import React from 'react';
import { Box, Typography, Link, Container } from '@mui/material';

const Footer = () => {
  return (
    <Box 
      component="footer" 
      sx={{ 
        py: 3, 
        px: 2, 
        mt: 'auto',
        backgroundColor: theme => theme.palette.mode === 'light' 
          ? theme.palette.grey[200] 
          : theme.palette.grey[800]
      }}
    >
      <Container maxWidth="lg">
        <Typography variant="body2" color="text.secondary" align="center">
          © {new Date().getFullYear()} SciLit2.0 - Wissenschaftliche Literaturverwaltung
        </Typography>
        
        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
          Entwickelt für die wissenschaftliche Recherche und Verwaltung
        </Typography>
      </Container>
    </Box>
  );
};

export default Footer;