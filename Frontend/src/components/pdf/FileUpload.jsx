// src/components/pdf/FileUpload.jsx
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { 
  Button, 
  CircularProgress, 
  Paper, 
  Typography, 
  Box, 
  TextField, 
  Alert, 
  Snackbar,
  LinearProgress,
  Step,
  Stepper,
  StepLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
} from '@mui/material';

// Icons
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ArticleIcon from '@mui/icons-material/Article';
import SettingsIcon from '@mui/icons-material/Settings';
import SaveIcon from '@mui/icons-material/Save';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';
import RefreshIcon from '@mui/icons-material/Refresh';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import TimelapseIcon from '@mui/icons-material/Timelapse';

// Services und Komponenten
import pdfService from '../../services/pdfService';
import * as metadataApi from '../../api/metadata';
import * as documentsApi from '../../api/documents';
import ProcessingSettings from './ProcessingSettings';
import MetadataForm, { detectDocumentType } from './MetadataForm';
import PDFViewer from './PDFViewer';
import { formatToISODate } from '../../utils/dateFormatter';

// Hooks
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

// Full viewport width container wrapper component
const FullWidthContainer = ({ children }) => (
  <Box
    sx={{
      position: 'relative',
      width: '90vw', // Slightly narrower than full viewport width
      left: '50%',
      right: '50%',
      marginLeft: '-45vw', // Half of the width
      marginRight: '-45vw', // Half of the width
      boxSizing: 'border-box',
      px: { xs: 6, sm: 8 }, // More horizontal padding
      py: 2,
    }}
  >
    {children}
  </Box>
);

// Dialog-Komponente für Verarbeitungsfehler
const ProcessingErrorDialog = ({ open, error, processingStage, onClose, onRetry, onChangeSettings }) => {
  // Erweiterte Fehleranalyse
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

const FileUpload = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // File-State
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  
  // Processing-State
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Document tracking state
  const [documentId, setDocumentId] = useState(null);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [processingFailed, setProcessingFailed] = useState(false);
  const statusIntervalRef = useRef(null);
  
  // Fehlerbehandlung
  const [processingError, setProcessingError] = useState(null);
  
  // Processing settings
  const [settings, setSettings] = useState({
    maxPages: 0, // 0 means all pages
    chunkSize: 1000,
    chunkOverlap: 200,
    performOCR: false
  });
  const [showSettings, setShowSettings] = useState(false);
  
  // Results
  const [extractedText, setExtractedText] = useState('');
  const [extractedIdentifiers, setExtractedIdentifiers] = useState({ doi: null, isbn: null });
  const [chunks, setChunks] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  // Errors
  const [error, setError] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Processing steps
  const steps = [
    'PDF hochladen', 
    'Dokument verarbeiten', 
    'Metadaten prüfen', 
    'In Datenbank speichern'
  ];

  // Authentication check
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/upload' } });
    }
  }, [isAuthenticated, navigate]);
  
  // Cleanup status polling on unmount
  useEffect(() => {
    return () => {
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
      }
    };
  }, []);
  
  // Poll document status when documentId is set
  useEffect(() => {
    if (documentId && currentStep === 3 && !processingComplete && !processingFailed) {
      // Start polling status
      if (!statusIntervalRef.current) {
        setIsCheckingStatus(true);
        checkDocumentStatus(documentId);
        
        statusIntervalRef.current = setInterval(() => {
          checkDocumentStatus(documentId);
        }, 5000); // Check every 5 seconds
      }
    } else if (processingComplete || processingFailed) {
      // Stop polling when processing is complete or failed
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
        setIsCheckingStatus(false);
      }
    }
    
    return () => {
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
      }
    };
  }, [documentId, currentStep, processingComplete, processingFailed]);
  
  // Add a monitoring function for long-running processes
  useEffect(() => {
    let processingTimer = null;
    
    if (processing) {
      // Set a safety timeout to prevent UI from being stuck in processing state
      processingTimer = setTimeout(() => {
        if (processing) {
          setProcessing(false);
          setProcessingError("Die Verarbeitung hat zu lange gedauert. Die Operation läuft möglicherweise noch im Hintergrund, aber die Benutzeroberfläche wurde entsperrt.");
        }
      }, 600000); // 10 minutes
    }
    
    return () => {
      if (processingTimer) {
        clearTimeout(processingTimer);
      }
    };
  }, [processing]);
  
  /**
   * Check processing status of the document
   */
  const checkDocumentStatus = async (id) => {
    try {
      // Zähler für Abfrageversuche
      if (!statusCheckCount.current) statusCheckCount.current = 0;
      statusCheckCount.current++;
      
      // Nach 20 Versuchen (ca. 1 Minute) automatisch abbrechen
      if (statusCheckCount.current > 20) {
        setProcessingError("Zeitüberschreitung bei der Dokumentverarbeitung.");
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
        return;
      }
      
      const response = await documentsApi.getDocumentStatus(id);
      
      // Check if processing is complete
      if (response.status === 'completed') {
        setProcessingProgress(100);
        setProcessingStage('Verarbeitung abgeschlossen');
        setProcessingComplete(true);
        setIsCheckingStatus(false);
        setSaveSuccess(true);
        
        // Stop polling
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
      } 
      // Check if processing is still ongoing
      else if (response.status === 'processing') {
        setProcessingProgress(response.progress || 0);
        setProcessingStage(response.message || 'Verarbeitung läuft...');
      }
      // Check if processing failed
      else if (response.status === 'error') {
        setProcessingFailed(true);
        setError(response.message || 'Fehler bei der Verarbeitung');
        setSnackbarOpen(true);
        setIsCheckingStatus(false);
        
        // Stop polling
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
      }
    } catch (error) {
      console.error('Error checking document status:', error);
      // Don't stop polling on network errors - it might be temporary
    }
  };
  
  /**
   * Handle file selection
   */
  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      // Reset state for new upload
      setMetadata(null);
      setExtractedIdentifiers({ doi: null, isbn: null });
      setExtractedText('');
      setChunks([]);
      setError('');
      setCurrentStep(0); // Back to first step
      setSaveSuccess(false);
      setProcessingComplete(false);
      setProcessingFailed(false);
      setDocumentId(null);
      setProcessingError(null);
      
      // Clear any existing status interval
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
      }
    } else {
      setError('Bitte wähle eine gültige PDF-Datei aus');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Update processing settings
   */
  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings);
  };
  
  /**
   * Process the uploaded PDF
   */
  const processFile = useCallback(async () => {
    if (!file) {
      setError('Bitte wähle zuerst eine Datei aus');
      setSnackbarOpen(true);
      return;
    }

    setProcessing(true);
    setCurrentStep(1); // Move to processing step
    
    // Reset any previous errors
    setProcessingError(null);
    
    try {
      // Check file size for client-side validation
      const maxFileSizeMB = 20; // 20 MB limit
      const fileSizeMB = file.size / (1024 * 1024);
      
      if (fileSizeMB > maxFileSizeMB) {
        throw new Error(`Die Datei ist zu groß (${fileSizeMB.toFixed(1)} MB). Maximale Größe ist ${maxFileSizeMB} MB.`);
      }
      
      // Process PDF file with progress reporting
      const result = await pdfService.processFile(file, {
        ...settings,
        progressCallback: (stage, percent) => {
          setProcessingStage(stage);
          setProcessingProgress(percent);
        }
      });
      
      // Store results
      setExtractedText(result.text);
      setChunks(result.chunks);
      setExtractedIdentifiers({
        doi: result.metadata.doi,
        isbn: result.metadata.isbn
      });
      
      // If DOI or ISBN was found, try to get metadata
      if (result.metadata.doi || result.metadata.isbn) {
        setProcessingStage('Hole Metadaten...');
        try {
          let fetchedMetadata = null;
          
          // Try DOI first
          if (result.metadata.doi) {
            fetchedMetadata = await metadataApi.fetchDOIMetadata(result.metadata.doi);
          }
          
          // If DOI didn't work, try ISBN
          if (!fetchedMetadata && result.metadata.isbn) {
            fetchedMetadata = await metadataApi.fetchISBNMetadata(result.metadata.isbn);
          }
          
          if (fetchedMetadata) {
            // Detect document type and set it
            const detectedType = detectDocumentType(fetchedMetadata);
            
            // Set metadata with document type
            setMetadata({
              ...fetchedMetadata,
              type: detectedType
            });
          } else {
            // Create empty metadata structure
            setMetadata({
              title: '',
              authors: [],
              publicationDate: '',
              publisher: '',
              journal: '',
              doi: result.metadata.doi || '',
              isbn: result.metadata.isbn || '',
              abstract: '',
              type: 'other' // Default document type
            });
          }
        } catch (metadataError) {
          console.error('Error fetching metadata:', metadataError);
          
          // Create empty metadata structure
          setMetadata({
            title: '',
            authors: [],
            publicationDate: '',
            publisher: '',
            journal: '',
            doi: result.metadata.doi || '',
            isbn: result.metadata.isbn || '',
            abstract: '',
            type: 'other' // Default document type
          });
        }
      } else {
        // If no identifiers were found
        setMetadata({
          title: '',
          authors: [],
          publicationDate: '',
          publisher: '',
          journal: '',
          doi: '',
          isbn: '',
          abstract: '',
          type: 'other' // Default document type
        });
        
        setError('Keine DOI oder ISBN konnte aus dem Dokument extrahiert werden. Bitte geben Sie die Metadaten manuell ein.');
        setSnackbarOpen(true);
      }
      
      setProcessingStage('Verarbeitung abgeschlossen');
      setProcessingProgress(100);
      
      // Move to next step
      setCurrentStep(2);
    } catch (error) {
      console.error('Error processing file:', error);
      setProcessingError(`Fehler bei der Dateiverarbeitung: ${error.message}`);
      setCurrentStep(0); // Back to upload step
    } finally {
      setProcessing(false);
    }
  }, [file, settings]);
  
  /**
   * Handle metadata updates
   */
  const handleMetadataChange = (field, value) => {
    // Convert date fields to ISO format
    let formattedValue = value;
    if (field === 'publicationDate' || field === 'date' || 
        field === 'conferenceDate' || field === 'lastUpdated' || 
        field === 'accessDate') {
      formattedValue = formatToISODate(value);
    }

    setMetadata(prev => ({
      ...prev,
      [field]: formattedValue,
    }));
  };
  
  /**
   * Save document to database
   */
  const saveToDatabase = async () => {
    if (!metadata || !metadata.title) {
      setError('Titel ist erforderlich');
      setSnackbarOpen(true);
      return;
    }
  
    setProcessing(true);
    setProcessingStage('Speichere in Datenbank...');
    setCurrentStep(3); // Move to saving step
    
    try {
      // Make sure all chunks have page numbers
      const chunksWithPages = chunks.map(chunk => {
        // If chunk is already properly formatted with page_number
        if (typeof chunk === 'object' && chunk.hasOwnProperty('text') && chunk.hasOwnProperty('page_number')) {
          return chunk;
        }
        
        // If it's just a text string, try to guess the page (fallback to page 1)
        return {
          text: typeof chunk === 'string' ? chunk : chunk.text || '',
          page_number: chunk.page_number || 1
        };
      });
      
      // Flache Datenstruktur für die wichtigsten Metadaten erstellen
      // Frontend-Fix: Stelle sicher, dass Metadaten direkt im Root-Objekt liegen
      const documentData = {
        // Wichtige Felder direkt im Root setzen
        title: metadata.title.trim(), // Stellen Sie sicher, dass der Titel getrimmt wird
        type: metadata.type || 'article',
        authors: metadata.authors || [],
        
        // Rest der Metadaten in metadata-Objekt
        metadata: {
          ...metadata,
          // Format dates properly
          publicationDate: formatToISODate(metadata.publicationDate) || new Date().toISOString().split('T')[0],
          date: metadata.date ? formatToISODate(metadata.date) : undefined,
          conferenceDate: metadata.conferenceDate ? formatToISODate(metadata.conferenceDate) : undefined,
          lastUpdated: metadata.lastUpdated ? formatToISODate(metadata.lastUpdated) : undefined,
          accessDate: metadata.accessDate ? formatToISODate(metadata.accessDate) : undefined
        },
        text: extractedText,
        chunks: chunksWithPages, // Enhanced chunks with page numbers
        fileName: fileName,
        fileSize: file.size,
        uploadDate: new Date().toISOString(),
        // Processing settings
        maxPages: settings.maxPages,
        performOCR: settings.performOCR,
        chunkSize: settings.chunkSize,
        chunkOverlap: settings.chunkOverlap
      };
  
      // Debug: Zeige Daten, die gesendet werden
      console.log("Sending document data:", JSON.stringify({
        title: documentData.title,
        type: documentData.type
      }));
  
      // Save document and file to the server
      const savedDoc = await documentsApi.saveDocument(documentData, file);
      
      console.log("Document saved with ID:", savedDoc.document_id);
      
      // Save the document ID for status checking
      setDocumentId(savedDoc.document_id || savedDoc.id);
      
      // Note: We do NOT immediately set saveSuccess here
      // Instead, we'll check the processing status before showing success
      setProcessingStage('Verarbeitungsfortschritt überprüfen...');
      setProcessingProgress(0);
      
    } catch (error) {
      console.error('Error saving document:', error);
      // Show more specific error message
      let errorMsg = "Error saving document: ";
      if (error.response && error.response.data && error.response.data.error) {
        errorMsg += error.response.data.error;
      } else if (error.message) {
        errorMsg += error.message;
      } else {
        errorMsg += "Unknown error";
      }
      setError(errorMsg);
      setSnackbarOpen(true);
      setProcessingFailed(true);
    }
  };
  
  /**
   * Go to dashboard after successful save
   */
  const goToDashboard = () => {
    navigate('/dashboard');
  };
  
  /**
   * Render the upload area
   */
  const renderUploadArea = () => (
    <Box 
      sx={{ 
        width: '100%', 
        height: 200, 
        border: '2px dashed #ccc',
        borderRadius: 2,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        mb: 3,
        p: 2,
        cursor: 'pointer',
        '&:hover': {
          borderColor: 'primary.main',
          bgcolor: 'rgba(0, 0, 0, 0.01)'
        }
      }}
      onClick={() => document.getElementById('pdf-upload').click()}
    >
      {fileName ? (
        <>
          <ArticleIcon sx={{ fontSize: 50, color: 'primary.main', mb: 1 }} />
          <Typography>{fileName}</Typography>
          <Typography variant="body2" color="textSecondary">
            Klicke, um Datei zu ändern
          </Typography>
        </>
      ) : (
        <>
          <CloudUploadIcon sx={{ fontSize: 50, color: 'primary.main', mb: 1 }} />
          <Typography>PDF-Datei hier ablegen oder klicken zum Durchsuchen</Typography>
          <Typography variant="body2" color="textSecondary">
            Unterstützt PDF-Dateien bis 20MB
          </Typography>
        </>
      )}
      <input
        id="pdf-upload"
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
    </Box>
  );
  
  /**
   * Render processing status
   */
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
      <LinearProgress 
        variant="determinate" 
        value={processingProgress} 
        sx={{ height: 8, borderRadius: 4 }}
      />
      
      {extractedIdentifiers.doi && (
        <Alert severity="success" sx={{ mt: 2 }}>
          DOI erkannt: {extractedIdentifiers.doi}
        </Alert>
      )}
      
      {extractedIdentifiers.isbn && (
        <Alert severity="success" sx={{ mt: 2 }}>
          ISBN erkannt: {extractedIdentifiers.isbn}
        </Alert>
      )}
      
      {chunks.length > 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Dokument in {chunks.length} Chunks für die Verarbeitung aufgeteilt
        </Alert>
      )}
    </Box>
  );
  
  /**
   * Render content based on current step
   */
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Upload step
        return (
          <>
            {renderUploadArea()}
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
              <Button
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => setShowSettings(true)}
              >
                Verarbeitungseinstellungen
              </Button>
              
              <Button
                variant="contained"
                color="primary"
                disabled={!file || processing}
                onClick={processFile}
              >
                PDF verarbeiten
              </Button>
            </Box>
          </>
        );
        
      case 1: // Processing step
        return (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <ArticleIcon sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
              <Typography variant="h6">{fileName}</Typography>
            </Box>
            
            {renderProcessingStatus()}
          </>
        );
        
      case 2: // Metadata step
        return (
          <Box sx={{ display: 'flex', gap: 4, flexDirection: { xs: 'column', md: 'row' } }}>
            {/* Metadata on left */}
            <Box sx={{ width: { xs: '100%', md: '55%' } }}>
              {metadata && (
                <MetadataForm
                  metadata={metadata}
                  onChange={handleMetadataChange}
                />
              )}
      
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<SaveIcon />}
                  onClick={saveToDatabase}
                  disabled={processing || !metadata?.title}
                >
                  In Datenbank speichern
                </Button>
              </Box>
            </Box>
      
            {/* PDF on right */}
            <Box sx={{ width: { xs: '100%', md: '45%' } }}>
              {file && <PDFViewer file={file} height="750px" />}
            </Box>
      
            {/* Optional: Loading indicator */}
            {processing && renderProcessingStatus()}
          </Box>
        );
      
      case 3: // Saving/success step
        return (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            {isCheckingStatus ? (
              // Show waiting state while processing in background
              <>
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
              </>
            ) : processingFailed ? (
              // Show error state
              <>
                <ErrorIcon sx={{ fontSize: 80, color: 'error.main', mb: 2 }} />
                <Typography variant="h5" gutterBottom>
                  Fehler bei der Verarbeitung
                </Typography>
                <Typography variant="body1" paragraph color="error">
                  {error || 'Bei der Dokumentverarbeitung ist ein Fehler aufgetreten.'}
                </Typography>
                <Button
                  variant="contained"
                  onClick={() => setCurrentStep(0)}
                  sx={{ mt: 2, mr: 2 }}
                >
                  Erneut versuchen
                </Button>
                <Button
                  variant="outlined"
                  onClick={goToDashboard}
                  sx={{ mt: 2 }}
                >
                  Zum Dashboard
                </Button>
              </>
            ) : saveSuccess && processingComplete ? (
              // Show success state only when processing is actually complete
              <>
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
                  onClick={goToDashboard}
                  sx={{ mt: 2 }}
                >
                  Zum Dashboard
                </Button>
              </>
            ) : (
              // Default saving state (should not appear for long)
              <Box sx={{ textAlign: 'center' }}>
                <CircularProgress size={60} sx={{ mb: 2 }} />
                <Typography variant="h6">
                  Speichere Dokument...
                </Typography>
              </Box>
            )}
          </Box>
        );
        
      default:
        return null;
    }
  };
  
  // Render settings dialog
  const renderSettingsDialog = () => (
    <Dialog
      open={showSettings}
      onClose={() => setShowSettings(false)}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Verarbeitungseinstellungen</DialogTitle>
      <DialogContent>
        <ProcessingSettings 
          settings={settings}
          onChange={handleSettingsChange}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShowSettings(false)}>Abbrechen</Button>
        <Button onClick={() => setShowSettings(false)} variant="contained">
          Einstellungen übernehmen
        </Button>
      </DialogActions>
    </Dialog>
  );
  
  // Use the full-width container for the entire component
  return (
    <FullWidthContainer>
      <Box sx={{ maxWidth: '100%', overflowX: 'hidden' }}>
        <Paper
          elevation={3}
          sx={{
            width: '100%',
            p: { xs: 3, md: 4 },
            mb: 4,
            mx: 'auto',
            maxWidth: 1500 // Set a maximum width for the paper component
          }}
        >
          {/* Main heading centered */}
          <Typography 
            variant="h5" 
            component="h2" 
            gutterBottom 
            align="center" 
            sx={{ mb: 3 }}
          >
            Wissenschaftliche Publikation hochladen
          </Typography>
          
          {/* Stepper */}
          <Stepper 
            activeStep={currentStep} 
            alternativeLabel 
            sx={{ width: '100%', mb: 4 }}
          >
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
          
          {/* Step content */}
          <Box sx={{ width: '100%' }}>
            {renderStepContent()}
          </Box>
        </Paper>
        
        {/* Settings dialog */}
        {renderSettingsDialog()}
        
        {/* Processing error dialog */}
        {processingError && (
          <ProcessingErrorDialog
            open={!!processingError}
            error={processingError}
            onClose={() => setProcessingError(null)}
            onRetry={() => {
              setProcessingError(null);
              setShowSettings(true);
            }}
          />
        )}
        
        {/* Error snackbar */}
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={6000}
          onClose={() => setSnackbarOpen(false)}
        >
          <Alert onClose={() => setSnackbarOpen(false)} severity="error">
            {error}
          </Alert>
        </Snackbar>
      </Box>
    </FullWidthContainer>
  );
};

export default FileUpload;

/*
// src/components/pdf/FileUpload.jsx
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Box, Button, Paper, Typography, Alert, Snackbar, Stepper, Step, StepLabel, Grid } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

// Subkomponenten importieren
import UploadArea from './upload/UploadArea';
import ProcessingStep from './upload/ProcessingStep';
import MetadataStep from './upload/MetadataStep';
import SaveStep from './upload/SaveStep';
import SettingsDialog from './upload/SettingsDialog';
import ProcessingErrorDialog from './upload/ProcessingErrorDialog';

// Services
import * as documentsApi from '../../api/documents';
import { formatToISODate } from '../../utils/dateFormatter';

// Container-Komponente für Vollbild-Ansicht
const FullWidthContainer = ({ children }) => (
  <Box
    sx={{
      position: 'relative',
      width: '90vw',
      left: '50%',
      right: '50%',
      marginLeft: '-45vw',
      marginRight: '-45vw',
      boxSizing: 'border-box',
      px: { xs: 6, sm: 8 },
      py: 2,
    }}
  >
    {children}
  </Box>
);

const FileUpload = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const statusCheckCount = useRef(0);
  
  // Datei-Status
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  
  // Verarbeitungs-Status
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Dokument-Tracking-Status
  const [documentId, setDocumentId] = useState(null);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [processingFailed, setProcessingFailed] = useState(false);
  const statusIntervalRef = useRef(null);
  
  // Fehlerbehandlung
  const [processingError, setProcessingError] = useState(null);
  
  // Verarbeitungseinstellungen
  const [settings, setSettings] = useState({
    maxPages: 0,
    chunkSize: 1000,
    chunkOverlap: 200,
    performOCR: false
  });
  const [showSettings, setShowSettings] = useState(false);
  
  // Ergebnisse
  const [extractedText, setExtractedText] = useState('');
  const [extractedIdentifiers, setExtractedIdentifiers] = useState({ doi: null, isbn: null });
  const [chunks, setChunks] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  // Fehler
  const [error, setError] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Verarbeitungsschritte
  const steps = [
    'PDF hochladen', 
    'Dokument verarbeiten', 
    'Metadaten prüfen', 
    'In Datenbank speichern'
  ];

  // Authentifizierung prüfen
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/upload' } });
    }
  }, [isAuthenticated, navigate]);
  
  // Status-Polling beim Unmount aufräumen
  useEffect(() => {
    return () => {
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
      }
    };
  }, []);
  
  // Dokument-Status abfragen wenn documentId gesetzt ist
  useEffect(() => {
    if (documentId && currentStep === 3 && !processingComplete && !processingFailed) {
      // Start polling status
      if (!statusIntervalRef.current) {
        setIsCheckingStatus(true);
        checkDocumentStatus(documentId);
        
        statusIntervalRef.current = setInterval(() => {
          checkDocumentStatus(documentId);
        }, 5000); // Check every 5 seconds
      }
    } else if (processingComplete || processingFailed) {
      // Stop polling when processing is complete or failed
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
        setIsCheckingStatus(false);
      }
    }
    
    return () => {
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
      }
    };
  }, [documentId, currentStep, processingComplete, processingFailed]);
  
  // Überwachungsfunktion für lang laufende Prozesse hinzufügen
  useEffect(() => {
    let processingTimer = null;
    
    if (processing) {
      // Timeout setzen, um zu verhindern, dass die UI im Verarbeitungsstatus stecken bleibt
      processingTimer = setTimeout(() => {
        if (processing) {
          setProcessing(false);
          setProcessingError("Die Verarbeitung hat zu lange gedauert. Die Operation läuft möglicherweise noch im Hintergrund, aber die Benutzeroberfläche wurde entsperrt.");
        }
      }, 600000); // 10 minutes
    }
    
    return () => {
      if (processingTimer) {
        clearTimeout(processingTimer);
      }
    };
  }, [processing]);
  
  /**
   * Dokument-Verarbeitungsstatus prüfen
   */ /*
  const checkDocumentStatus = async (id) => {
    try {
      // Zähler für Abfrageversuche
      if (!statusCheckCount.current) statusCheckCount.current = 0;
      statusCheckCount.current++;
      
      // Nach 20 Versuchen (ca. 1 Minute) automatisch abbrechen
      if (statusCheckCount.current > 20) {
        setProcessingError("Zeitüberschreitung bei der Dokumentverarbeitung.");
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
        return;
      }
      
      const response = await documentsApi.getDocumentStatus(id);
      
      // Prüfen, ob Verarbeitung abgeschlossen
      if (response.status === 'completed') {
        setProcessingProgress(100);
        setProcessingStage('Verarbeitung abgeschlossen');
        setProcessingComplete(true);
        setIsCheckingStatus(false);
        setSaveSuccess(true);
        
        // Polling stoppen
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
      } 
      // Prüfen, ob Verarbeitung noch läuft
      else if (response.status === 'processing') {
        setProcessingProgress(response.progress || 0);
        setProcessingStage(response.message || 'Verarbeitung läuft...');
      }
      // Prüfen, ob Verarbeitung fehlgeschlagen
      else if (response.status === 'error') {
        setProcessingFailed(true);
        setError(response.message || 'Fehler bei der Verarbeitung');
        setSnackbarOpen(true);
        setIsCheckingStatus(false);
        
        // Polling stoppen
        if (statusIntervalRef.current) {
          clearInterval(statusIntervalRef.current);
          statusIntervalRef.current = null;
        }
      }
    } catch (error) {
      console.error('Error checking document status:', error);
      // Don't stop polling on network errors - it might be temporary
    }
  };
  
  /**
   * Dateiauswahl verarbeiten
   */ /*
  const handleFileChange = (selectedFile) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      // Status für neuen Upload zurücksetzen
      resetUploadState();
    } else {
      setError('Bitte wähle eine gültige PDF-Datei aus');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Upload-Status zurücksetzen
   */ /*
  const resetUploadState = () => {
    setMetadata(null);
    setExtractedIdentifiers({ doi: null, isbn: null });
    setExtractedText('');
    setChunks([]);
    setError('');
    setCurrentStep(0); // Zurück zum ersten Schritt
    setSaveSuccess(false);
    setProcessingComplete(false);
    setProcessingFailed(false);
    setDocumentId(null);
    setProcessingError(null);
    
    // Alle existierenden Status-Intervalle löschen
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
      statusIntervalRef.current = null;
    }
  };
  
  /**
   * Verarbeitungseinstellungen aktualisieren
   */ /*
  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings);
  };
  
  /**
   * Metadaten-Änderungen verarbeiten
   */ /*
  const handleMetadataChange = (field, value) => {
    // Datumsfelder in ISO-Format konvertieren
    let formattedValue = value;
    if (field === 'publicationDate' || field === 'date' || 
        field === 'conferenceDate' || field === 'lastUpdated' || 
        field === 'accessDate') {
      formattedValue = formatToISODate(value);
    }

    setMetadata(prev => ({
      ...prev,
      [field]: formattedValue,
    }));
  };
  
  /**
   * Nach erfolgreicher Speicherung zum Dashboard gehen
   */ /*
  const goToDashboard = () => {
    navigate('/dashboard');
  };
  
  /**
   * PDF-Datei verarbeiten
   */ /*
  const processFile = useCallback(async (uploadedFile) => {
    if (!uploadedFile) {
      setError('Bitte wähle zuerst eine Datei aus');
      setSnackbarOpen(true);
      return;
    }

    setProcessing(true);
    setCurrentStep(1); // Move to processing step
    
    // Alle vorherigen Fehler zurücksetzen
    setProcessingError(null);
    
    try {
      // Process PDF file and create metadata through backend services
      // This would be a call to the API, passing file and settings
      const formData = new FormData();
      formData.append('file', uploadedFile);
      
      // Add settings to the request
      const requestData = {
        maxPages: settings.maxPages,
        performOCR: settings.performOCR,
        chunkSize: settings.chunkSize,
        chunkOverlap: settings.chunkOverlap
      };
      
      formData.append('data', JSON.stringify(requestData));
      
      // Start PDF processing
      const response = await documentsApi.startProcessing(formData);
      
      // Store results
      setDocumentId(response.document_id);
      setExtractedText(response.text || '');
      setChunks(response.chunks || []);
      setExtractedIdentifiers({
        doi: response.metadata?.doi || null,
        isbn: response.metadata?.isbn || null
      });
      
      // If metadata was returned, use it
      if (response.metadata) {
        setMetadata(response.metadata);
      } else {
        // Create empty metadata structure
        setMetadata({
          title: '',
          authors: [],
          publicationDate: '',
          publisher: '',
          journal: '',
          doi: response.doi || '',
          isbn: response.isbn || '',
          abstract: '',
          type: 'other' // Default document type
        });
      }
      
      setProcessingStage('Verarbeitung abgeschlossen');
      setProcessingProgress(100);
      
      // Move to next step
      setCurrentStep(2);
    } catch (error) {
      console.error('Error processing file:', error);
      setProcessingError(`Fehler bei der Dateiverarbeitung: ${error.message}`);
      setCurrentStep(0); // Back to upload step
    } finally {
      setProcessing(false);
    }
  }, [settings]);
  
  /**
   * Dokument in Datenbank speichern
   */ /*
  const saveToDatabase = async () => {
    if (!metadata || !metadata.title) {
      setError('Titel ist erforderlich');
      setSnackbarOpen(true);
      return;
    }
  
    setProcessing(true);
    setProcessingStage('Speichere in Datenbank...');
    setCurrentStep(3); // Move to saving step
    
    try {
      // Make sure all chunks have page numbers
      const chunksWithPages = chunks.map(chunk => {
        // If chunk is already properly formatted with page_number
        if (typeof chunk === 'object' && chunk.hasOwnProperty('text') && chunk.hasOwnProperty('page_number')) {
          return chunk;
        }
        
        // If it's just a text string, try to guess the page (fallback to page 1)
        return {
          text: typeof chunk === 'string' ? chunk : chunk.text || '',
          page_number: chunk.page_number || 1
        };
      });
      
      // Flache Datenstruktur für die wichtigsten Metadaten erstellen
      const documentData = {
        // Wichtige Felder direkt im Root setzen
        title: metadata.title.trim(),
        type: metadata.type || 'article',
        authors: metadata.authors || [],
        
        // Rest der Metadaten im metadata-Objekt
        metadata: {
          ...metadata,
          // Dates properly format
          publicationDate: formatToISODate(metadata.publicationDate) || new Date().toISOString().split('T')[0],
          date: metadata.date ? formatToISODate(metadata.date) : undefined,
          conferenceDate: metadata.conferenceDate ? formatToISODate(metadata.conferenceDate) : undefined,
          lastUpdated: metadata.lastUpdated ? formatToISODate(metadata.lastUpdated) : undefined,
          accessDate: metadata.accessDate ? formatToISODate(metadata.accessDate) : undefined
        },
        text: extractedText,
        chunks: chunksWithPages,
        fileName: fileName,
        fileSize: file.size,
        uploadDate: new Date().toISOString(),
        // Processing settings
        maxPages: settings.maxPages,
        performOCR: settings.performOCR,
        chunkSize: settings.chunkSize,
        chunkOverlap: settings.chunkOverlap
      };
  
      // Save document and file to the server
      const savedDoc = await documentsApi.saveDocument(documentData, file);
      
      console.log("Document saved with ID:", savedDoc.document_id);
      
      // Save the document ID for status checking
      setDocumentId(savedDoc.document_id || savedDoc.id);
      
      // Note: We do NOT immediately set saveSuccess here
      // Instead, we'll check the processing status before showing success
      setProcessingStage('Verarbeitungsfortschritt überprüfen...');
      setProcessingProgress(0);
      
    } catch (error) {
      console.error('Error saving document:', error);
      let errorMsg = "Error saving document: ";
      if (error.response && error.response.data && error.response.data.error) {
        errorMsg += error.response.data.error;
      } else if (error.message) {
        errorMsg += error.message;
      } else {
        errorMsg += "Unknown error";
      }
      setError(errorMsg);
      setSnackbarOpen(true);
      setProcessingFailed(true);
    }
  };
  
  /**
   * Inhalt basierend auf aktuellem Schritt rendern
   */ /*
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Upload step
        return (
          <UploadArea 
            file={file}
            fileName={fileName}
            onFileChange={handleFileChange}
            onProcess={() => processFile(file)}
            onOpenSettings={() => setShowSettings(true)}
            processing={processing}
          />
        );
        
      case 1: // Processing step
        return (
          <ProcessingStep 
            fileName={fileName}
            processingStage={processingStage}
            processingProgress={processingProgress}
            extractedIdentifiers={extractedIdentifiers}
            chunks={chunks}
          />
        );
        
      case 2: // Metadata step
        return (
          <MetadataStep 
            metadata={metadata}
            file={file}
            onMetadataChange={handleMetadataChange}
            onSave={saveToDatabase}
            processing={processing}
          />
        );
      
      case 3: // Saving/success step
        return (
          <SaveStep 
            isCheckingStatus={isCheckingStatus}
            processingFailed={processingFailed}
            saveSuccess={saveSuccess}
            processingComplete={processingComplete}
            error={error}
            processingStage={processingStage}
            processingProgress={processingProgress}
            onGoToDashboard={goToDashboard}
            onRetry={() => setCurrentStep(0)}
          />
        );
        
      default:
        return null;
    }
  };
  
  // Render the complete component
  return (
    <FullWidthContainer>
      <Box sx={{ maxWidth: '100%', overflowX: 'hidden' }}>
        <Paper
          elevation={3}
          sx={{
            width: '100%',
            p: { xs: 3, md: 4 },
            mb: 4,
            mx: 'auto',
            maxWidth: 1500
          }}
        >
          {/* Main heading centered */ /*}
          <Typography 
            variant="h5" 
            component="h2" 
            gutterBottom 
            align="center" 
            sx={{ mb: 3 }}
          >
            Wissenschaftliche Publikation hochladen
          </Typography>
          
          {/* Stepper */ /*} 
          <Stepper 
            activeStep={currentStep} 
            alternativeLabel 
            sx={{ width: '100%', mb: 4 }}
          >
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
          
          {/* Step content *//*} /*
          <Box sx={{ width: '100%' }}>
            {renderStepContent()}
          </Box>
        </Paper>
        
        {/* Settings dialog *//*}   /*
        <SettingsDialog
          open={showSettings}
          settings={settings}
          onClose={() => setShowSettings(false)}
          onChange={handleSettingsChange}
        />
        
        {/* Processing error dialog *//*} /*
        {processingError && (
          <ProcessingErrorDialog
            open={!!processingError}
            error={processingError}
            processingStage={processingStage}
            onClose={() => setProcessingError(null)}
            onRetry={() => {
              setProcessingError(null);
              processFile(file);
            }}
            onChangeSettings={() => {
              setProcessingError(null);
              setShowSettings(true);
            }}
          />
        )}
        
        {/* Error snackbar *//*} /*
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={6000}
          onClose={() => setSnackbarOpen(false)}
        >
          <Alert onClose={() => setSnackbarOpen(false)} severity="error">
            {error}
          </Alert>
        </Snackbar>
      </Box>
    </FullWidthContainer>
  );
};

export default FileUpload; */