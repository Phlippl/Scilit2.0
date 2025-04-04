// src/pages/UploadPage.jsx
import React, { useEffect } from 'react';
import { Box, Typography, Container } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import FileUpload from '../components/pdf/FileUpload';

const UploadPage = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // Authentifizierung prüfen
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/upload' } });
    }
  }, [isAuthenticated, navigate]);
  
  return (
    <Container>
      <Box sx={{ mt: 4, mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Publikation hochladen
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          Lade wissenschaftliche Artikel oder Bücher als PDF hoch. Das System extrahiert automatisch 
          Metadaten wie DOI oder ISBN und bereitet das Dokument für intelligente Abfragen vor.
        </Typography>
      </Box>
      
      <FileUpload />
    </Container>
  );
};

export default UploadPage;