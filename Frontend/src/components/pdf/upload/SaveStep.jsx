// src/components/pdf/upload/SaveStep.jsx
import React from 'react';
import { Box, Typography, Button, CircularProgress } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';

/**
 * Komponente für den Speicher-/Abschlussschritt beim PDF-Upload
 * 
 * @param {Object} props - Komponenten-Properties
 * @param {boolean} props.isCheckingStatus - Flag für Status-Überprüfung
 * @param {boolean} props.processingFailed - Flag für fehlgeschlagene Verarbeitung
 * @param {boolean} props.saveSuccess - Flag für erfolgreiche Speicherung
 * @param {boolean} props.processingComplete - Flag für abgeschlossene Verarbeitung
 * @param {string} props.error - Fehlermeldung bei Fehler
 * @param {string} props.processingStage - Aktuelle Verarbeitungsphase
 * @param {number} props.processingProgress - Aktueller Fortschritt (0-100)
 * @param {Function} props.onGoToDashboard - Callback für Navigation zum Dashboard
 * @param {Function} props.onRetry - Callback für Wiederholung
 */
const SaveStep = ({ 
  isCheckingStatus, 
  processingFailed, 
  saveSuccess, 
  processingComplete,
  error,
  processingStage,
  processingProgress,
  onGoToDashboard,
  onRetry
}) => {
  // Hilfsfunktion zum Anzeigen des Verarbeitungsstatus
  const renderProcessingStatus = () => (
    <Box sx={{ width: '100%', mt: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Typography variant="body2" color="textSecondary" sx={{ flexGrow: 1 }}>
          {processingStage}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {processingProgress}%
        </Typography>
      </Box>
      <Box 
        sx={{ 
          height: 8, 
          borderRadius: 4, 
          bgcolor: 'grey.300',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <Box 
          sx={{ 
            position: 'absolute',
            left: 0,
            top: 0,
            height: '100%',
            width: `${processingProgress}%`,
            bgcolor: 'primary.main',
            borderRadius: 4,
            transition: 'width 0.3s ease'
          }}
        />
      </Box>
    </Box>
  );
  
  if (isCheckingStatus) {
    // Waiting state while processing in background
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Box sx={{ animation: 'pulse 1.5s infinite', mb: 2 }}>
          <HourglassTopIcon sx={{ fontSize: 80, color: 'warning.main' }} />
        </Box>
        <Typography variant="h5" gutterBottom>
          Dokument wird im Hintergrund verarbeitet
        </Typography>
        <Typography variant="body1" paragraph>
          Die Verarbeitung kann je nach Dokumentgröße einige Minuten dauern.
        </Typography>
        {renderProcessingStatus()}
      </Box>
    );
  } 
  
  if (processingFailed) {
    // Error state
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <ErrorIcon sx={{ fontSize: 80, color: 'error.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Fehler bei der Verarbeitung
        </Typography>
        <Typography variant="body1" paragraph color="error">
          {error || 'Bei der Dokumentverarbeitung ist ein Fehler aufgetreten.'}
        </Typography>
        <Button
          variant="contained"
          onClick={onRetry}
          sx={{ mt: 2, mr: 2 }}
        >
          Erneut versuchen
        </Button>
        <Button
          variant="outlined"
          onClick={onGoToDashboard}
          sx={{ mt: 2 }}
        >
          Zum Dashboard
        </Button>
      </Box>
    );
  } 
  
  if (saveSuccess && processingComplete) {
    // Success state only when processing is actually complete
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <CheckCircleIcon sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          Dokument erfolgreich gespeichert
        </Typography>
        <Typography variant="body1" paragraph>
          Dein Dokument wurde verarbeitet und zu deiner Literaturdatenbank hinzugefügt.
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={onGoToDashboard}
          sx={{ mt: 2 }}
        >
          Zum Dashboard
        </Button>
      </Box>
    );
  }
  
  // Default saving state (should not appear for long)
  return (
    <Box sx={{ textAlign: 'center', py: 4 }}>
      <CircularProgress size={60} sx={{ mb: 2 }} />
      <Typography variant="h6">
        Speichere Dokument...
      </Typography>
    </Box>
  );
};

export default SaveStep;