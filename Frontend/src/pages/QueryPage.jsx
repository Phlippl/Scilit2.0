// src/pages/QueryPage.jsx
import React, { useEffect } from 'react';
import { Box, Typography, Container } from '@mui/material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import QueryInterface from '../components/query/QueryInterface';

const QueryPage = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const documentId = searchParams.get('doc');
  
  // Authentifizierung prüfen
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/query${documentId ? `?doc=${documentId}` : ''}` } });
    }
  }, [isAuthenticated, navigate, documentId]);
  
  return (
    <Container>
      <Box sx={{ mt: 4, mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Literatur abfragen
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          Stelle präzise Fragen an deine Literatursammlung und erhalte Antworten mit 
          automatischen Zitierungen. Wähle zwischen verschiedenen Zitationsstilen und 
          filtere nach spezifischen Dokumenten.
        </Typography>
      </Box>
      
      <QueryInterface preselectedDocumentId={documentId} />
    </Container>
  );
};

export default QueryPage;