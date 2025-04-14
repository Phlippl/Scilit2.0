// src/components/pdf/FileUpload.jsx
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Box, Paper, Typography, Alert, Snackbar, Stepper, Step, StepLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

// Services
import * as documentsApi from '../../api/documents';
import * as metadataApi from '../../api/metadata';
import { formatToISODate } from '../../utils/dateFormatter';

// Subcomponents
import UploadArea from './upload/UploadArea';
import ProcessingStep from './upload/ProcessingStep';
import MetadataStep from './upload/MetadataStep';
import SaveStep from './upload/SaveStep';
import SettingsDialog from './upload/SettingsDialog';
import ProcessingErrorDialog from './upload/ProcessingErrorDialog';

// Container component for full-width view
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
  const statusCheckInterval = 5000; // 5 seconds between status checks
  const maxStatusChecks = 60; // Max 5 minutes of polling (60 * 5s = 300s)
  const statusCheckCount = useRef(0);
  const statusIntervalRef = useRef(null);
  
  // File state
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  
  // Processing state
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Document tracking state
  const [documentId, setDocumentId] = useState(null);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [processingFailed, setProcessingFailed] = useState(false);
  
  // Error handling
  const [processingError, setProcessingError] = useState(null);
  
  // Processing settings
  const [settings, setSettings] = useState({
    maxPages: 0,
    chunkSize: 1000,
    chunkOverlap: 200,
    performOCR: false
  });
  const [showSettings, setShowSettings] = useState(false);
  
  // Results
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
        statusIntervalRef.current = null;
      }
    };
  }, []);
  
  // Poll document status when documentId is set
  useEffect(() => {
    if (documentId && currentStep === 3 && !processingComplete && !processingFailed) {
      // Start polling status
      if (!statusIntervalRef.current) {
        setIsCheckingStatus(true);
        statusCheckCount.current = 0;
        checkDocumentStatus(documentId);
        
        statusIntervalRef.current = setInterval(() => {
          checkDocumentStatus(documentId);
        }, statusCheckInterval);
      }
    } else if (processingComplete || processingFailed) {
      // Stop polling when processing is complete or failed
      stopStatusPolling();
    }
    
    return () => stopStatusPolling();
  }, [documentId, currentStep, processingComplete, processingFailed]);
  
  // Set a safety timeout for long-running processes
  useEffect(() => {
    let processingTimer = null;
    
    if (processing) {
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
   * Stop status polling
   */
  const stopStatusPolling = () => {
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
      statusIntervalRef.current = null;
      setIsCheckingStatus(false);
    }
  };
  
  /**
   * Check document processing status
   */
  const checkDocumentStatus = async (id) => {
    try {
      // Increment the counter
      statusCheckCount.current++;
      
      // Stop polling after max attempts
      if (statusCheckCount.current > maxStatusChecks) {
        setProcessingError("Zeitüberschreitung bei der Dokumentverarbeitung.");
        stopStatusPolling();
        return;
      }
      
      const response = await documentsApi.getDocumentStatus(id);
      
      // Check status
      switch (response.status) {
        case 'completed':
          setProcessingProgress(100);
          setProcessingStage('Verarbeitung abgeschlossen');
          setProcessingComplete(true);
          setSaveSuccess(true);
          stopStatusPolling();
          break;
          
        case 'processing':
          setProcessingProgress(response.progress || 0);
          setProcessingStage(response.message || 'Verarbeitung läuft...');
          break;
          
        case 'error':
          setProcessingFailed(true);
          setError(response.message || 'Fehler bei der Verarbeitung');
          setSnackbarOpen(true);
          stopStatusPolling();
          break;
          
        default:
          // Handle unknown status
          console.warn(`Unknown processing status: ${response.status}`);
      }
    } catch (error) {
      console.error('Error checking document status:', error);
      // Don't stop polling on network errors - it might be temporary
    }
  };
  
  /**
   * Handle file selection
   */
  const handleFileChange = (selectedFile) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      resetUploadState();
    } else {
      setError('Bitte wähle eine gültige PDF-Datei aus');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Reset upload state
   */
  const resetUploadState = () => {
    setMetadata(null);
    setExtractedIdentifiers({ doi: null, isbn: null });
    setChunks([]);
    setError('');
    setCurrentStep(0);
    setSaveSuccess(false);
    setProcessingComplete(false);
    setProcessingFailed(false);
    setDocumentId(null);
    setProcessingError(null);
    stopStatusPolling();
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
    setProcessingError(null);
    
    try {
      // Client-side file size validation
      const maxFileSizeMB = 20;
      const fileSizeMB = file.size / (1024 * 1024);
      
      if (fileSizeMB > maxFileSizeMB) {
        throw new Error(`Die Datei ist zu groß (${fileSizeMB.toFixed(1)} MB). Maximale Größe ist ${maxFileSizeMB} MB.`);
      }
      
      // Create a form with just the file and processing settings for initial analysis
      const formData = new FormData();
      formData.append('file', file);
      formData.append('data', JSON.stringify({
        ...settings,
        analyzeOnly: true
      }));
      
      // Start analysis
      setProcessingStage('Extrahiere Text und Metadaten...');
      setProcessingProgress(10);
      
      // Upload the file for server-side processing
      const result = await documentsApi.analyzeDocument(formData, (stage, progress) => {
        setProcessingStage(stage);
        setProcessingProgress(progress);
      });
      
      // Store results
      setChunks(result.chunks || []);
      setExtractedIdentifiers({
        doi: result.metadata?.doi,
        isbn: result.metadata?.isbn
      });
      
      // Attempt to fetch metadata using identified DOI/ISBN
      setProcessingStage('Hole Metadaten...');
      setProcessingProgress(90);
      
      try {
        let fetchedMetadata = null;
        
        // Try DOI first
        if (result.metadata?.doi) {
          fetchedMetadata = await metadataApi.fetchDOIMetadata(result.metadata.doi);
        }
        
        // If DOI didn't work, try ISBN
        if (!fetchedMetadata && result.metadata?.isbn) {
          fetchedMetadata = await metadataApi.fetchISBNMetadata(result.metadata.isbn);
        }
        
        if (fetchedMetadata) {
          setMetadata({
            ...fetchedMetadata,
            type: fetchedMetadata.type || 'other'
          });
        } else {
          createEmptyMetadata(result.metadata);
        }
      } catch (metadataError) {
        console.error('Error fetching metadata:', metadataError);
        createEmptyMetadata(result.metadata);
      }
      
      setProcessingStage('Verarbeitung abgeschlossen');
      setProcessingProgress(100);
      setCurrentStep(2); // Move to metadata step
    } catch (error) {
      console.error('Error processing file:', error);
      setProcessingError(`Fehler bei der Dateiverarbeitung: ${error.message}`);
      setCurrentStep(0); // Back to upload step
    } finally {
      setProcessing(false);
    }
  }, [file, settings]);
  
  /**
   * Create empty metadata structure with any extracted identifiers
   */
  const createEmptyMetadata = (extractedData = {}) => {
    setMetadata({
      title: '',
      authors: [],
      publicationDate: '',
      publisher: '',
      journal: '',
      doi: extractedData?.doi || '',
      isbn: extractedData?.isbn || '',
      abstract: '',
      type: 'other'
    });
    
    if (!extractedData?.doi && !extractedData?.isbn) {
      setError('Keine DOI oder ISBN konnte aus dem Dokument extrahiert werden. Bitte geben Sie die Metadaten manuell ein.');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Handle metadata changes
   */
  const handleMetadataChange = (field, value) => {
    // Format date fields
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
      // Normalize chunks for consistent storage
      const chunksWithPages = normalizeChunks(chunks);
      
      // Create document data
      const documentData = {
        title: metadata.title.trim(),
        type: metadata.type || 'article',
        authors: metadata.authors || [],
        metadata: {
          ...metadata,
          publicationDate: formatToISODate(metadata.publicationDate) || new Date().toISOString().split('T')[0],
          date: metadata.date ? formatToISODate(metadata.date) : undefined,
          conferenceDate: metadata.conferenceDate ? formatToISODate(metadata.conferenceDate) : undefined,
          lastUpdated: metadata.lastUpdated ? formatToISODate(metadata.lastUpdated) : undefined,
          accessDate: metadata.accessDate ? formatToISODate(metadata.accessDate) : undefined
        },
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
  
      // Save document with file
      const savedDoc = await documentsApi.saveDocument(documentData, file);
      
      // Store document ID for status checking
      setDocumentId(savedDoc.document_id || savedDoc.id);
      setProcessingStage('Verarbeitungsfortschritt überprüfen...');
      setProcessingProgress(0);
      
    } catch (error) {
      console.error('Error saving document:', error);
      let errorMsg = "Error saving document: ";
      
      if (error.response?.data?.error) {
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
   * Normalize chunks to consistent format
   */
  const normalizeChunks = (chunks) => {
    return chunks.map(chunk => {
      // If chunk is already properly formatted
      if (typeof chunk === 'object' && chunk.hasOwnProperty('text') && chunk.hasOwnProperty('page_number')) {
        return chunk;
      }
      
      // Otherwise normalize the format
      return {
        text: typeof chunk === 'string' ? chunk : chunk.text || '',
        page_number: chunk.page_number || 1
      };
    }).filter(chunk => chunk.text.trim()); // Remove empty chunks
  };
  
  /**
   * Go to dashboard after successful save
   */
  const goToDashboard = () => {
    navigate('/dashboard');
  };
  
  /**
   * Render content based on current step
   */
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Upload step
        return (
          <UploadArea 
            file={file}
            fileName={fileName}
            onFileChange={handleFileChange}
            onProcess={processFile}
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
        
        {/* Dialogs */}
        <SettingsDialog
          open={showSettings}
          settings={settings}
          onClose={() => setShowSettings(false)}
          onChange={handleSettingsChange}
        />
        
        {processingError && (
          <ProcessingErrorDialog
            open={!!processingError}
            error={processingError}
            processingStage={processingStage}
            onClose={() => setProcessingError(null)}
            onRetry={() => {
              setProcessingError(null);
              processFile();
            }}
            onChangeSettings={() => {
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