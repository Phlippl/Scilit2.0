// src/components/pdf/PDFUploader.jsx
import React, { useState, useCallback, useEffect } from 'react';
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
  Card,
  CardContent,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';

// Icons
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ArticleIcon from '@mui/icons-material/Article';
import InfoIcon from '@mui/icons-material/Info';
import HelpIcon from '@mui/icons-material/Help';
import SettingsIcon from '@mui/icons-material/Settings';
import SaveIcon from '@mui/icons-material/Save';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

// Services and APIs
import pdfProcessingService from '../../services/pdfProcessing';
import * as metadataApi from '../../api/metadata';
import * as documentsApi from '../../api/documents';

// Components
import ProcessingSettings from './ProcessingSettings';
import MetadataForm from './MetadataForm';
import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

const PDFUploader = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // File state
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  
  // Processing state
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Processing settings
  const [settings, setSettings] = useState({
    maxPages: 0, // 0 means all pages
    chunkSize: 1000,
    chunkOverlap: 200
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
    'Upload PDF', 
    'Process Document', 
    'Review Metadata', 
    'Save to Database'
  ];
  
  // Effects
  useEffect(() => {
    // Check authentication
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/upload' } });
    }
  }, [isAuthenticated, navigate]);
  
  // If we have identifiers, try to fetch metadata
  useEffect(() => {
    const fetchMetadata = async () => {
      if (!extractedIdentifiers.doi && !extractedIdentifiers.isbn) return;
      
      try {
        setProcessingStage('Fetching metadata...');
        
        let fetchedMetadata = null;
        
        // Try DOI first
        if (extractedIdentifiers.doi) {
          fetchedMetadata = await metadataApi.fetchDOIMetadata(extractedIdentifiers.doi);
        }
        
        // If DOI didn't work, try ISBN
        if (!fetchedMetadata && extractedIdentifiers.isbn) {
          fetchedMetadata = await metadataApi.fetchISBNMetadata(extractedIdentifiers.isbn);
        }
        
        // If backend API fails, try direct CrossRef call
        if (!fetchedMetadata && extractedIdentifiers.doi) {
          const crossrefData = await metadataApi.fetchDOIMetadataFromCrossRef(extractedIdentifiers.doi);
          // Format the CrossRef data if needed
          if (crossrefData) {
            fetchedMetadata = formatCrossRefMetadata(crossrefData);
          }
        }
        
        if (fetchedMetadata) {
          setMetadata(fetchedMetadata);
          setCurrentStep(2); // Move to metadata review step
        } else {
          // Create empty metadata structure for user to fill
          setMetadata({
            title: '',
            authors: [],
            publicationDate: '',
            publisher: '',
            journal: '',
            doi: extractedIdentifiers.doi || '',
            isbn: extractedIdentifiers.isbn || '',
            abstract: ''
          });
          setError('Could not find metadata for this document. Please enter manually.');
          setSnackbarOpen(true);
          setCurrentStep(2); // Still move to metadata review step
        }
        
        setProcessingStage('');
      } catch (err) {
        console.error('Error fetching metadata:', err);
        setError(`Error fetching metadata: ${err.message}`);
        setSnackbarOpen(true);
        // Still move to metadata review with empty form
        setMetadata({
          title: '',
          authors: [],
          publicationDate: '',
          publisher: '',
          journal: '',
          doi: extractedIdentifiers.doi || '',
          isbn: extractedIdentifiers.isbn || '',
          abstract: ''
        });
        setCurrentStep(2);
      }
    };
    
    if (currentStep === 1 && !processing) {
      fetchMetadata();
    }
  }, [extractedIdentifiers, currentStep, processing]);
  
  /**
   * Format CrossRef metadata into application format
   */
  const formatCrossRefMetadata = (data) => {
    if (!data) return null;
    
    // Extract basic information
    const result = {
      title: data.title ? data.title[0] : '',
      doi: data.DOI || '',
      url: data.URL || '',
      type: data.type || '',
      publicationDate: '',
      authors: [],
      journal: data['container-title'] ? data['container-title'][0] : '',
      volume: data.volume || '',
      issue: data.issue || '',
      pages: data.page || '',
      publisher: data.publisher || '',
      abstract: data.abstract || '',
      isbn: '',
    };
    
    // Extract authors
    if (data.author && Array.isArray(data.author)) {
      result.authors = data.author.map(author => ({
        given: author.given || '',
        family: author.family || '',
        name: (author.given && author.family) ? 
          `${author.family}, ${author.given}` : 
          author.name || '',
        orcid: author.ORCID || '',
      }));
    }
    
    // Extract publication date
    if (data.published) {
      const date = data.published['date-parts'] ? 
        data.published['date-parts'][0] : [];
      
      if (date.length >= 1) {
        // Format as YYYY-MM-DD or partial date
        result.publicationDate = date.join('-');
      }
    }
    
    // Extract ISBN for books
    if (data.ISBN && Array.isArray(data.ISBN)) {
      result.isbn = data.ISBN[0];
    }
    
    return result;
  };
  
  /**
   * Handle file selection
   */
  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      // Reset states for new upload
      setMetadata(null);
      setExtractedIdentifiers({ doi: null, isbn: null });
      setExtractedText('');
      setChunks([]);
      setError('');
      setCurrentStep(0); // Reset to first step
      setSaveSuccess(false);
    } else {
      setError('Please select a valid PDF file');
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
      setError('Please select a file first');
      setSnackbarOpen(true);
      return;
    }

    setProcessing(true);
    setCurrentStep(1); // Move to processing step
    
    try {
      // Process the PDF file with progress reporting
      const result = await pdfProcessingService.processFile(file, {
        ...settings,
        progressCallback: (stage, percent) => {
          setProcessingStage(
            stage === 'text_extraction' ? 'Extracting text...' :
            stage === 'metadata_extraction' ? 'Extracting identifiers...' :
            stage === 'ocr_processing' ? 'Performing OCR...' :
            stage === 'chunking' ? 'Chunking document...' : 
            'Processing...'
          );
  
  // Main component render
  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 3, 
        mt: 3, 
        maxWidth: 900, 
        mx: 'auto',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}
    >
      <Typography variant="h5" component="h2" gutterBottom>
        Upload Academic Paper or Book
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
      
      {/* Settings Dialog */}
      {renderSettingsDialog()}
      
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
    </Paper>
  );
};

export default PDFUploader;
          setProcessingProgress(percent);
        }
      });
      
      // Store the results
      setExtractedText(result.text);
      setChunks(result.chunks);
      setExtractedIdentifiers({
        doi: result.metadata.doi,
        isbn: result.metadata.isbn
      });
      
      setProcessingStage('Processing complete');
      setProcessingProgress(100);
      
      // If no identifiers were found
      if (!result.metadata.doi && !result.metadata.isbn) {
        setError('No DOI or ISBN could be extracted from the document. Please enter manually if available.');
        setSnackbarOpen(true);
      }
    } catch (error) {
      console.error('Error processing file:', error);
      setError(`Error processing file: ${error.message}`);
      setSnackbarOpen(true);
      setCurrentStep(0); // Return to upload step
    } finally {
      setProcessing(false);
    }
  }, [file, settings]);
  
  /**
   * Handle metadata updates
   */
  const handleMetadataChange = (field, value) => {
    setMetadata(prev => ({
      ...prev,
      [field]: value,
    }));
  };
  
  /**
   * Save document to database
   */
  const saveToDatabase = async () => {
    if (!metadata || !metadata.title) {
      setError('Title is required');
      setSnackbarOpen(true);
      return;
    }

    setProcessing(true);
    setProcessingStage('Saving to database...');
    
    try {
      // Prepare document data for saving
      const documentData = {
        metadata: {
          ...metadata,
          // Ensure date format is correct
          publicationDate: metadata.publicationDate || new Date().toISOString().split('T')[0]
        },
        text: extractedText,
        chunks: chunks,
        fileName: fileName,
        fileSize: file.size,
        uploadDate: new Date().toISOString(),
        chunkSettings: {
          chunkSize: settings.chunkSize,
          chunkOverlap: settings.chunkOverlap
        }
      };
      
      // Convert file to base64 if needed by the API
      // This might be better handled by a form upload endpoint
      // const fileBase64 = await convertFileToBase64(file);
      // documentData.fileContent = fileBase64;
      
      // Save to database via API
      await documentsApi.saveDocument(documentData);
      
      setSaveSuccess(true);
      setCurrentStep(3); // Move to final step
    } catch (error) {
      console.error('Error saving document:', error);
      setError(`Error saving document: ${error.message}`);
      setSnackbarOpen(true);
    } finally {
      setProcessing(false);
      setProcessingStage('');
    }
  };
  
  /**
   * Convert a file to base64 string
   */
  const convertFileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.onerror = error => reject(error);
    });
  };
  
  /**
   * Move to dashboard after successful save
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
            Click to change file
          </Typography>
        </>
      ) : (
        <>
          <CloudUploadIcon sx={{ fontSize: 50, color: 'primary.main', mb: 1 }} />
          <Typography>Drop your PDF file here or click to browse</Typography>
          <Typography variant="body2" color="textSecondary">
            Supports PDF files up to 20MB
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
          DOI detected: {extractedIdentifiers.doi}
        </Alert>
      )}
      
      {extractedIdentifiers.isbn && (
        <Alert severity="success" sx={{ mt: 2 }}>
          ISBN detected: {extractedIdentifiers.isbn}
        </Alert>
      )}
      
      {chunks.length > 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Document split into {chunks.length} chunks for processing
        </Alert>
      )}
    </Box>
  );
  
  /**
   * Render content based on current step
   */
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Upload Step
        return (
          <>
            {renderUploadArea()}
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
              <Button
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => setShowSettings(true)}
              >
                Processing Settings
              </Button>
              
              <Button
                variant="contained"
                color="primary"
                disabled={!file || processing}
                onClick={processFile}
              >
                Process PDF
              </Button>
            </Box>
          </>
        );
        
      case 1: // Processing Step
        return (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <ArticleIcon sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
              <Typography variant="h6">{fileName}</Typography>
            </Box>
            
            {renderProcessingStatus()}
          </>
        );
        
      case 2: // Metadata Review
        return (
          <>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6">Document Metadata</Typography>
              <Tooltip title="These fields will be used for citation generation">
                <IconButton>
                  <InfoIcon />
                </IconButton>
              </Tooltip>
            </Box>
            
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
                Save to Database
              </Button>
            </Box>
            
            {processing && renderProcessingStatus()}
          </>
        );
        
      case 3: // Success Step
        return (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CheckCircleIcon sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              Document Saved Successfully
            </Typography>
            <Typography variant="body1" paragraph>
              Your document has been processed and added to your literature database.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={goToDashboard}
              sx={{ mt: 2 }}
            >
              Go to Dashboard
            </Button>
          </Box>
        );
        
      default:
        return null;
    }
  };
  
  // Render the settings dialog
  const renderSettingsDialog = () => (
    <Dialog
      open={showSettings}
      onClose={() => setShowSettings(false)}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Processing Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ py: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            These settings control how your document is processed and chunked for optimal retrieval.
          </Typography>
          
          <TextField
            fullWidth
            margin="normal"
            label="Maximum Pages to Process (0 = all)"
            type="number"
            value={settings.maxPages}
            onChange={(e) => handleSettingsChange({
              ...settings,
              maxPages: parseInt(e.target.value) || 0
            })}
            InputProps={{ inputProps: { min: 0 } }}
            helperText="Limit processing to first N pages. Use 0 for all pages."
          />
          
          <TextField
            fullWidth
            margin="normal"
            label="Chunk Size (characters)"
            type="number"
            value={settings.chunkSize}
            onChange={(e) => handleSettingsChange({
              ...settings,
              chunkSize: parseInt(e.target.value) || 1000
            })}
            InputProps={{ inputProps: { min: 100, max: 10000 } }}
            helperText="Smaller chunks improve granularity but may lose context. Larger chunks preserve context but may be less precise."
          />
          
          <TextField
            fullWidth
            margin="normal"
            label="Chunk Overlap (characters)"
            type="number"
            value={settings.chunkOverlap}
            onChange={(e) => handleSettingsChange({
              ...settings,
              chunkOverlap: parseInt(e.target.value) || 200
            })}
            InputProps={{ inputProps: { min: 0, max: settings.chunkSize / 2 } }}
            helperText="Overlap between chunks helps maintain context across chunk boundaries."
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShowSettings(false)}>Cancel</Button>
        <Button onClick={() => setShowSettings(false)} variant="contained">
          Apply Settings
        </Button>
      </DialogActions>
    </Dialog>
  );