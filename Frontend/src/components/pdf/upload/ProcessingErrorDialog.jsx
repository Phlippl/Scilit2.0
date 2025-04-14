// src/components/pdf/upload/ProcessingErrorDialog.jsx
import React from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Typography, 
  Box, 
  Button, 
  Alert 
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import RefreshIcon from '@mui/icons-material/Refresh';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import TimelapseIcon from '@mui/icons-material/Timelapse';

/**
 * Dialog component for displaying detailed PDF processing errors
 * 
 * @param {Object} props - Component props
 * @param {boolean} props.open - Dialog open state
 * @param {string} props.error - Error message
 * @param {string} props.processingStage - Stage where error occurred
 * @param {Function} props.onClose - Callback when dialog is closed
 * @param {Function} props.onRetry - Callback to retry processing
 * @param {Function} props.onChangeSettings - Callback to open settings dialog
 */
const ProcessingErrorDialog = ({ open, error, processingStage, onClose, onRetry, onChangeSettings }) => {
  // Error type analysis for better suggestions
  const errorType = 
    error?.includes('too large') ? 'size' :
    error?.includes('timeout') || error?.includes('zu lange gedauert') ? 'timeout' :
    error?.includes('network') || error?.includes('Network') ? 'network' :
    error?.includes('metadata') || error?.includes('Metadaten') ? 'metadata' :
    error?.includes('OCR') ? 'ocr' :
    error?.includes('memory') || error?.includes('Speicher') ? 'memory' :
    'unknown';
  
  const errorMessages = {
    size: {
      title: 'Datei zu groß',
      message: 'Die hochgeladene Datei überschreitet die maximal zulässige Größe.',
      action: 'Bitte verwenden Sie eine kleinere Datei (maximal 20MB).',
      icon: <ErrorOutlineIcon sx={{ fontSize: 60, color: 'error.main' }} />
    },
    timeout: {
      title: 'Zeitüberschreitung',
      message: 'Die Verarbeitung hat zu lange gedauert und wurde abgebrochen.',
      action: 'Versuchen Sie es mit einer kleineren Datei oder deaktivieren Sie die OCR-Verarbeitung.',
      icon: <TimelapseIcon sx={{ fontSize: 60, color: 'warning.main' }} />
    },
    network: {
      title: 'Netzwerkfehler',
      message: 'Verbindung zum Server unterbrochen während der Verarbeitung.',
      action: 'Bitte überprüfen Sie Ihre Internetverbindung und versuchen Sie es erneut.',
      icon: <ErrorOutlineIcon sx={{ fontSize: 60, color: 'error.main' }} />
    },
    metadata: {
      title: 'Metadatenfehler',
      message: 'Fehler bei der Extraktion oder Verarbeitung der Metadaten.',
      action: 'Bitte überprüfen Sie die Metadaten und korrigieren Sie etwaige Fehler.',
      icon: <ErrorOutlineIcon sx={{ fontSize: 60, color: 'warning.main' }} />
    },
    ocr: {
      title: 'OCR-Fehler',
      message: 'Fehler bei der Texterkennung (OCR).',
      action: 'Versuchen Sie es mit deaktivierter OCR-Verarbeitung.',
      icon: <ErrorOutlineIcon sx={{ fontSize: 60, color: 'warning.main' }} />
    },
    memory: {
      title: 'Speicherbegrenzung erreicht',
      message: 'Die Verarbeitung benötigt mehr Ressourcen als verfügbar.',
      action: 'Reduzieren Sie die Größe der Datei oder die Anzahl der zu verarbeitenden Seiten.',
      icon: <ErrorOutlineIcon sx={{ fontSize: 60, color: 'error.main' }} />
    },
    unknown: {
      title: 'Unbekannter Fehler',
      message: 'Bei der Verarbeitung ist ein unerwarteter Fehler aufgetreten.',
      action: 'Bitte versuchen Sie es erneut oder kontaktieren Sie den Support.',
      icon: <ErrorOutlineIcon sx={{ fontSize: 60, color: 'error.main' }} />
    }
  };
  
  const errorInfo = errorMessages[errorType];
  
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {errorInfo.icon}
        <Typography variant="h6" component="span" color="error">
          {errorInfo.title}
        </Typography>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6" gutterBottom>
            {errorInfo.message}
          </Typography>
          
          <Alert severity="info" sx={{ my: 2 }}>
            {errorInfo.action}
          </Alert>
          
          <Typography variant="body1" paragraph>
            Die Dokumentenverarbeitung wurde aufgrund eines Fehlers gestoppt. 
            Verarbeitungsschritt: <strong>{processingStage || 'Unbekannt'}</strong>
          </Typography>
          
          <Alert severity="error" sx={{ my: 2, overflowX: 'auto' }}>
            <Typography component="pre" sx={{ whiteSpace: 'pre-wrap', margin: 0 }}>
              {error}
            </Typography>
          </Alert>
          
          <Typography variant="body1" paragraph sx={{ mt: 2 }}>
            Sie können Folgendes versuchen:
          </Typography>
          
          <Box component="ul" sx={{ pl: 3 }}>
            {errorType === 'size' && <Typography component="li">Komprimieren Sie die PDF-Datei</Typography>}
            {(errorType === 'timeout' || errorType === 'memory') && (
              <>
                <Typography component="li">Reduzieren Sie die maximale Seitenzahl in den Einstellungen</Typography>
                <Typography component="li">Deaktivieren Sie OCR, falls es aktiviert ist</Typography>
              </>
            )}
            <Typography component="li">Verwenden Sie eine andere PDF-Datei</Typography>
            <Typography component="li">Versuchen Sie es später erneut</Typography>
          </Box>
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Schließen</Button>
        <Button 
          onClick={onChangeSettings} 
          startIcon={<SettingsIcon />}
        >
          Einstellungen ändern
        </Button>
        <Button 
          onClick={onRetry} 
          variant="contained" 
          startIcon={<RefreshIcon />}
        >
          Erneut versuchen
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProcessingErrorDialog;