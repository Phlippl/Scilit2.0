// src/pages/DashboardPage.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, Grid, CircularProgress } from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import DocumentCard from '../components/dashboard/DocumentCard';
import NoDocuments from '../components/dashboard/NoDocuments';
import * as documentsApi from '../api/documents';

const DashboardPage = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  useEffect(() => {
    // Authentifizierung prüfen
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/dashboard' } });
      return;
    }
    
    // Dokumente laden
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const docs = await documentsApi.getDocuments();
        setDocuments(docs);
      } catch (error) {
        console.error('Fehler beim Laden der Dokumente:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchDocuments();
  }, [isAuthenticated, navigate]);
  
  // Dokument löschen
  const handleDeleteDocument = async (id) => {
    try {
      await documentsApi.deleteDocument(id);
      setDocuments(prevDocs => prevDocs.filter(doc => doc.id !== id));
    } catch (error) {
      console.error('Fehler beim Löschen des Dokuments:', error);
    }
  };
  
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Deine Literatur
      </Typography>
      
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button 
          variant="contained" 
          color="primary" 
          onClick={() => navigate('/upload')}
        >
          Neue Publikation hochladen
        </Button>
      </Box>
      
      {documents.length === 0 ? (
        <NoDocuments />
      ) : (
        <Grid container spacing={3}>
          {documents.map((document) => (
            <Grid item xs={12} sm={6} md={4} key={document.id}>
              <DocumentCard 
                document={document} 
                onDelete={() => handleDeleteDocument(document.id)}
                onView={() => navigate(`/query?doc=${document.id}`)}
              />
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default DashboardPage;