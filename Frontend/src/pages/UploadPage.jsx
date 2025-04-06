// src/pages/UploadPage.jsx
import React, { useEffect } from 'react';
import { Box, Typography, Container } from '@mui/material';
import { useNavigate } from 'react-router-dom';

import FileUpload from '../components/pdf/FileUpload';
import { useAuth } from '../hooks/useAuth';

const UploadPage = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // Check authentication
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/upload' } });
    }
  }, [isAuthenticated, navigate]);
  
  return (
    <Container maxWidth="xl">
      <Box sx={{ mt: 4, mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Upload Document
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          Upload scientific papers or books as PDF files. The system will extract metadata,
          analyze content, and make documents searchable through the query interface.
        </Typography>
      </Box>
      
      <FileUpload />
    </Container>
  );
};

export default UploadPage;