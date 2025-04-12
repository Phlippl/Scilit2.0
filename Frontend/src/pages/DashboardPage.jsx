// src/pages/DashboardPage.jsx
import React, { useState, useEffect } from 'react';
import { Box, Typography, Grid, CircularProgress, Container } from '@mui/material';
import { useNavigate } from 'react-router-dom';

// Components
import DocumentCard from '../components/dashboard/DocumentCard';
import ConfirmDialog from '../components/common/ConfirmDialog';
import NoDocuments from '../components/dashboard/NoDocuments';

// Hooks
import { useAuth } from '../hooks/useAuth';
import { useDocuments } from '../hooks/useDocuments';

const DashboardPage = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  const { 
    documents = [], // Hier wird ein Default-Wert (leeres Array) zugewiesen
    isLoading, 
    error, 
    fetchDocuments, 
    deleteDocument 
  } = useDocuments();
  
  const [documentToDelete, setDocumentToDelete] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  
  // Check authentication
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/dashboard' } });
    }
  }, [isAuthenticated, navigate]);
  
  // Open delete confirmation dialog
  const handleDeleteClick = (document) => {
    setDocumentToDelete(document);
    setDeleteDialogOpen(true);
  };
  
  // Close delete confirmation dialog
  const handleDeleteCancel = () => {
    setDocumentToDelete(null);
    setDeleteDialogOpen(false);
  };
  
  // Confirm document deletion
  const handleDeleteConfirm = async () => {
    if (documentToDelete) {
      try {
        await deleteDocument(documentToDelete.id);
        setDeleteDialogOpen(false);
        setDocumentToDelete(null);
      } catch (error) {
        console.error('Failed to delete document:', error);
      }
    }
  };
  
  // Navigate to query page with selected document
  const handleQueryDocument = (document) => {
    navigate(`/query?doc=${document.id}`);
  };
  
  // View document details
  const handleDocumentClick = (document) => {
    // This could open a document dialog or navigate to a document page
    console.log('Clicked document:', document);
  };
  
  return (
    <Container>
      <Box sx={{ mt: 4, mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          My Documents
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          Manage your uploaded scientific literature and papers
        </Typography>
      </Box>
      
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Typography color="error" align="center" sx={{ my: 4 }}>
          Error loading documents: {error}
        </Typography>
      ) : (!Array.isArray(documents) || documents.length === 0) ? (
        <NoDocuments />
      ) : (
        <Grid container spacing={3}>
          {Array.isArray(documents) && documents.map((document) => (
            <Grid item xs={12} sm={6} md={4} key={document.id || `doc-${index}`}>
              <DocumentCard 
                document={document}
                onDelete={() => handleDeleteClick(document)}
                onView={() => handleQueryDocument(document)}
                onClick={() => handleDocumentClick(document)}
              />
            </Grid>
          ))}
        </Grid>
      )}
      
      <ConfirmDialog
        open={deleteDialogOpen}
        title="Delete Document"
        content={`Are you sure you want to delete "${documentToDelete?.title}"? This action cannot be undone.`}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
      />
    </Container>
  );
};

export default DashboardPage;