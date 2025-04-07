// src/components/pdf/DocumentProcessingStatus.jsx
import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  LinearProgress, 
  Paper, 
  Alert, 
  AlertTitle, 
  Button,
  CircularProgress
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';

import { getDocumentStatus } from '../../api/documents';

/**
 * Component that displays document processing status with progress updates
 * 
 * @param {Object} props - Component props
 * @param {string} props.documentId - ID of the document being processed
 * @param {Function} props.onComplete - Function to call when processing is complete
 * @param {Function} props.onError - Function to call when processing fails
 */
const DocumentProcessingStatus = ({ documentId, onComplete, onError }) => {
  const [status, setStatus] = useState({
    status: 'pending',
    progress: 0,
    message: 'Starte Dokumentverarbeitung...'
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Poll for status updates
  useEffect(() => {
    let mounted = true;
    let timerId = null;
    
    const fetchStatus = async () => {
      if (!mounted) return;
      
      let retryCount = 0;
      const MAX_RETRIES = 5;
      
      const attemptFetch = async () => {
        try {
          setLoading(true);
          const statusData = await getDocumentStatus(documentId);
          setStatus(statusData);
          
          // Reset retry counter on success
          retryCount = 0;
    
          // Call completion callback if processing is done
          if (statusData.status === 'completed' && onComplete) {
            onComplete();
          }
          
          // Call error callback if processing failed
          if (statusData.status === 'error' && onError) {
            onError(statusData.message);
          }
          
          // Continue polling if still processing
          if (statusData.status === 'processing' || statusData.status === 'pending') {
            timerId = setTimeout(fetchStatus, 2000); // Poll every 2 seconds
          }
        } catch (err) {
          retryCount++;
          console.error(`Error fetching status (attempt ${retryCount}):`, err);
          
          if (retryCount >= MAX_RETRIES) {
            setError('Maximale Anzahl an Versuchen erreicht. Bitte Seite neu laden.');
            if (onError) onError(err.message);
            return; // Stop polling
          }
          
          // Exponential backoff
          const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
          
          // Continue polling with increased delay
          timerId = setTimeout(attemptFetch, delay);
        } finally {
          if (mounted) setLoading(false);
        }
      };
      
      await attemptFetch();
    };
    
    fetchStatus();
    
    // Clean up polling on unmount
    return () => {
      mounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [documentId, onComplete, onError]);
  
  // Status-specific icon
  const getStatusIcon = () => {
    switch (status.status) {
      case 'completed':
        return <CheckCircleIcon color="success" sx={{ fontSize: 40 }} />;
      case 'error':
        return <ErrorIcon color="error" sx={{ fontSize: 40 }} />;
      case 'processing':
        return <CircularProgress size={40} />;
      default:
        return <HourglassEmptyIcon sx={{ fontSize: 40 }} />;
    }
  };
  
  // Status-specific color
  const getStatusColor = () => {
    switch (status.status) {
      case 'completed':
        return 'success.main';
      case 'error':
        return 'error.main';
      case 'processing':
        return 'primary.main';
      default:
        return 'text.secondary';
    }
  };
  
  if (loading && !status) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', p: 4 }}>
        <CircularProgress size={40} />
        <Typography variant="body1" sx={{ ml: 2 }}>
          Lade Verarbeitungsstatus...
        </Typography>
      </Box>
    );
  }
  
  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        <AlertTitle>Fehler</AlertTitle>
        {error}
      </Alert>
    );
  }
  
  return (
    <Paper sx={{ p: 3, mt: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        {getStatusIcon()}
        <Box sx={{ ml: 2 }}>
          <Typography variant="h6" sx={{ color: getStatusColor() }}>
            {status.status === 'completed' ? 'Verarbeitung abgeschlossen' : 
             status.status === 'error' ? 'Verarbeitung fehlgeschlagen' :
             status.status === 'processing' ? 'Dokument wird verarbeitet' : 'Warten auf Verarbeitung'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {status.message}
          </Typography>
        </Box>
      </Box>
      
      {status.status === 'processing' && (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
              Fortschritt:
            </Typography>
            <Typography variant="body2" fontWeight="medium">
              {status.progress}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={status.progress} 
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>
      )}
      
      {status.status === 'error' && (
        <Button 
          variant="outlined" 
          color="primary" 
          sx={{ mt: 2 }}
          onClick={() => window.location.reload()}
        >
          Erneut versuchen
        </Button>
      )}
    </Paper>
  );
}