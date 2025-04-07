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
const ProcessingErrorDialog = ({ open, error, onClose, onRetry }) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle sx={{ bgcolor: 'error.light', color: 'error.contrastText' }}>
        Verarbeitungsfehler
      </DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <Typography variant="h6" gutterBottom>
            Bei der Verarbeitung Ihrer PDF-Datei ist ein Fehler aufgetreten
          </Typography>
          
          <Alert severity="error" sx={{ my: 2 }}>
            {error}
          </Alert>
          
          <Typography variant="body1" paragraph>
            Die Dokumentenverarbeitung wurde aufgrund eines Fehlers gestoppt. Dies könnte folgende Gründe haben:
          </Typography>
          
          <Box component="ul" sx={{ pl: 3 }}>
            <Typography component="li">Ungültige oder beschädigte PDF-Datei</Typography>
            <Typography component="li">PDF-Datei ist zu groß oder komplex</Typography>
            <Typography component="li">Probleme bei der OCR-Verarbeitung</Typography>
            <Typography component="li">Systembeschränkungen</Typography>
            <Typography component="li">Verbindungsprobleme mit externen Diensten</Typography>
          </Box>
          
          <Typography variant="body1" paragraph sx={{ mt: 2 }}>
            Sie können Folgendes versuchen:
          </Typography>
          
          <Box component="ul" sx={{ pl: 3 }}>
            <Typography component="li">Verwenden Sie eine kleinere oder einfachere PDF-Datei</Typography>
            <Typography component="li">Deaktivieren Sie OCR, falls es aktiviert war</Typography>
            <Typography component="li">Reduzieren Sie die maximale Seitenzahl für die Verarbeitung</Typography>
            <Typography component="li">Versuchen Sie es später erneut, wenn Systemressourcen verfügbar sind</Typography>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Schließen</Button>
        <Button onClick={onRetry} variant="contained">
          Mit anderen Einstellungen versuchen
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
        }, 3000); // Check every 3 seconds
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
      
      // Prepare document data with enhanced page tracking
      const documentData = {
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
  
      // Save document and file to the server
      const savedDoc = await documentsApi.saveDocument(documentData, file);
      
      console.log("Document saved with ID:", savedDoc.document_id);
      
      // Save the document ID for status checking
      setDocumentId(savedDoc.document_id || savedDoc.id);
      
      // Note: We do NOT immediately set saveSuccess here
      // Instead, we'll check the processing status before showing success
      setProcessingStage('Verarbeitungsfortschritt überprüfen...');
      setProcessingProgress(0);
      
      // Update UI to indicate we're waiting for background processing
      // saveSuccess will be set by the status polling when processing is actually complete
    } catch (error) {
      console.error('Error saving document:', error);
      setError(`Error saving document: ${error.message || 'Unknown error'}`);
      setSnackbarOpen(true);
      setProcessingFailed(true);
    } finally {
      setProcessing(false);
      setProcessingStage('');
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
                  disabled={processing}
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