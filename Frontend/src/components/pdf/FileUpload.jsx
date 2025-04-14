// src/components/pdf/FileUpload.jsx
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Box, Paper, Typography, Alert, Snackbar, Stepper, Step, StepLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

// Services
import pdfService from '../../services/pdfService';
import * as metadataApi from '../../api/metadata';
import * as documentsApi from '../../api/documents';
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
  
  // Monitoring function for long-running processes
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
   * Check document processing status
   */
  const checkDocumentStatus = async (id) => {
    try {
      // Counter for query attempts
      if (!statusCheckCount.current) statusCheckCount.current = 0;
      statusCheckCount.current++;
      
      // After 20 attempts (approx. 1 minute) automatically abort
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
  const handleFileChange = (selectedFile) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      // Reset state for new upload
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
            // Create metadata with document type
            setMetadata({
              ...fetchedMetadata,
              type: fetchedMetadata.type || 'other'
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
              type: 'other'
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
            type: 'other'
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
          type: 'other'
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
   * Handle metadata changes
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
      
      // Create flat data structure for important metadata
      const documentData = {
        // Set important fields directly in root
        title: metadata.title.trim(),
        type: metadata.type || 'article',
        authors: metadata.authors || [],
        
        // Rest of metadata in metadata object
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
        <SettingsDialog
          open={showSettings}
          settings={settings}
          onClose={() => setShowSettings(false)}
          onChange={handleSettingsChange}
        />
        
        {/* Processing error dialog */}
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