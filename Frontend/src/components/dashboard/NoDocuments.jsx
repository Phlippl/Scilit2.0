// src/components/dashboard/NoDocuments.jsx
import React from 'react';
import { Paper, Typography, Button, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import UploadFileIcon from '@mui/icons-material/UploadFile';

/**
 * Komponente zur Anzeige, wenn keine Dokumente vorhanden sind
 */
const NoDocuments = () => {
  const navigate = useNavigate();
  
  return (
    <Paper sx={{ p: 4, textAlign: 'center' }}>
      <UploadFileIcon sx={{ fontSize: 60, color: 'action.disabled', mb: 2 }} />
      
      <Typography variant="h6" gutterBottom>
        Noch keine Dokumente vorhanden
      </Typography>
      
      <Typography variant="body1" paragraph>
        Lade deine erste wissenschaftliche Publikation hoch, um loszulegen
      </Typography>
      
      <Button 
        variant="contained" 
        color="primary" 
        onClick={() => navigate('/upload')}
        startIcon={<UploadFileIcon />}
      >
        Publikation hochladen
      </Button>
    </Paper>
  );
};

export default NoDocuments;