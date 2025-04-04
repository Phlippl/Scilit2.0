// Frontend/src/components/PDFUploader.jsx
import React, { useState, useCallback } from 'react';
import { Button, CircularProgress, Paper, Typography, Box, TextField, Alert, Snackbar } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ArticleIcon from '@mui/icons-material/Article';
import pdfExtractor from '../utils/pdfExtractor';
import crossrefService from '../services/crossrefService';

const PDFUploader = () => {
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [loading, setLoading] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [extractedIdentifiers, setExtractedIdentifiers] = useState({ doi: null, isbn: null });
  const [metadata, setMetadata] = useState(null);
  const [error, setError] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);

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
      setError('');
    } else {
      setError('Please select a valid PDF file');
      setSnackbarOpen(true);
    }
  };

  /**
   * Fetch metadata from CrossRef using DOI or ISBN
   */
  const fetchMetadata = useCallback(async (doi, isbn) => {
    try {
      let fetchedMetadata = null;
      
      // Try DOI first if available
      if (doi) {
        setProcessingStage('Fetching metadata using DOI...');
        const doiMetadata = await crossrefService.getMetadataByDOI(doi);
        if (doiMetadata) {
          fetchedMetadata = crossrefService.formatMetadata(doiMetadata);
        }
      }
      
      // If DOI didn't yield results or wasn't available, try ISBN
      if (!fetchedMetadata && isbn) {
        setProcessingStage('Fetching metadata using ISBN...');
        const isbnResults = await crossrefService.searchByISBN(isbn);
        if (isbnResults && isbnResults.length > 0) {
          // Use the first match
          fetchedMetadata = crossrefService.formatMetadata(isbnResults[0]);
        }
      }
      
      return fetchedMetadata;
    } catch (error) {
      console.error('Error fetching metadata:', error);
      throw error;
    }
  }, []);

  /**
   * Process the uploaded PDF
   */
  const processFile = useCallback(async () => {
    if (!file) {
      setError('Please select a file first');
      setSnackbarOpen(true);
      return;
    }

    setLoading(true);
    setProcessingStage('Extracting text from PDF...');
    
    try {
      // Extract DOI/ISBN from the PDF
      const result = await pdfExtractor.processFile(file);
      setExtractedIdentifiers({
        doi: result.doi,
        isbn: result.isbn,
      });
      
      if (!result.doi && !result.isbn) {
        setProcessingStage('');
        setError('No DOI or ISBN could be extracted from the document. Please enter manually.');
        setSnackbarOpen(true);
        setLoading(false);
        return;
      }
      
      // Fetch metadata using the extracted identifiers
      const fetchedMetadata = await fetchMetadata(result.doi, result.isbn);
      
      if (!fetchedMetadata) {
        setProcessingStage('');
        setError('Could not find metadata for this document. Please enter manually.');
        setSnackbarOpen(true);
        setLoading(false);
        return;
      }
      
      setMetadata(fetchedMetadata);
      setProcessingStage('');
      setLoading(false);
    } catch (error) {
      console.error('Error processing file:', error);
      setError(`Error processing file: ${error.message}`);
      setSnackbarOpen(true);
      setProcessingStage('');
      setLoading(false);
    }
  }, [file, fetchMetadata]);

  /**
   * Manually update DOI/ISBN and fetch metadata
   */
  const handleManualIdentifierUpdate = async (type, value) => {
    const updatedIdentifiers = {
      ...extractedIdentifiers,
      [type]: value,
    };
    
    setExtractedIdentifiers(updatedIdentifiers);
  };

  /**
   * Fetch metadata using manually entered identifiers
   */
  const handleManualFetch = async () => {
    setLoading(true);
    try {
      const fetchedMetadata = await fetchMetadata(
        extractedIdentifiers.doi, 
        extractedIdentifiers.isbn
      );
      
      if (!fetchedMetadata) {
        setError('Could not find metadata for the provided identifiers');
        setSnackbarOpen(true);
      } else {
        setMetadata(fetchedMetadata);
      }
    } catch (error) {
      setError(`Error fetching metadata: ${error.message}`);
      setSnackbarOpen(true);
    }
    setLoading(false);
  };

  /**
   * Handle metadata field updates
   */
  const handleMetadataChange = (field, value) => {
    setMetadata(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  /**
   * Render metadata editor
   */
  const renderMetadataEditor = () => {
    if (!metadata) return null;
    
    return (
      <Box sx={{ mt: 3, p: 2, border: '1px solid #ccc', borderRadius: 1 }}>
        <Typography variant="h6" gutterBottom>
          Metadata
        </Typography>
        
        <TextField
          fullWidth
          label="Title"
          value={metadata.title || ''}
          onChange={(e) => handleMetadataChange('title', e.target.value)}
          margin="normal"
          variant="outlined"
        />
        
        <TextField
          fullWidth
          label="DOI"
          value={metadata.doi || ''}
          onChange={(e) => handleMetadataChange('doi', e.target.value)}
          margin="normal"
          variant="outlined"
        />
        
        <TextField
          fullWidth
          label="Publication Date"
          value={metadata.publicationDate || ''}
          onChange={(e) => handleMetadataChange('publicationDate', e.target.value)}
          margin="normal"
          variant="outlined"
          placeholder="YYYY-MM-DD"
        />
        
        <TextField
          fullWidth
          label="Authors (comma-separated)"
          value={metadata.authors.map(a => a.name).join(', ') || ''}
          onChange={(e) => {
            const authorNames = e.target.value.split(',').map(name => name.trim());
            const authors = authorNames.map(name => ({ name }));
            handleMetadataChange('authors', authors);
          }}
          margin="normal"
          variant="outlined"
        />
        
        <TextField
          fullWidth
          label="Journal/Publisher"
          value={metadata.journal || metadata.publisher || ''}
          onChange={(e) => {
            handleMetadataChange('journal', e.target.value);
            handleMetadataChange('publisher', e.target.value);
          }}
          margin="normal"
          variant="outlined"
        />
        
        <Button 
          variant="contained" 
          color="primary" 
          sx={{ mt: 2 }}
          onClick={() => console.log('Save metadata and process for database', metadata)}
        >
          Save to Database
        </Button>
      </Box>
    );
  };

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 3, 
        mt: 3, 
        maxWidth: 800, 
        mx: 'auto',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}
    >
      <Typography variant="h5" component="h2" gutterBottom>
        Upload Academic Paper or Book
      </Typography>
      
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
      
      {/* Processing button */}
      <Button
        variant="contained"
        color="primary"
        startIcon={loading ? <CircularProgress size={20} color="inherit" /> : null}
        onClick={processFile}
        disabled={!file || loading}
        sx={{ mb: 2 }}
      >
        {loading ? 'Processing...' : 'Process PDF'}
      </Button>
      
      {/* Processing status */}
      {processingStage && (
        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
          {processingStage}
        </Typography>
      )}
      
      {/* Manual identifier input */}
      {file && (
        <Box sx={{ width: '100%', mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant="h6">Document Identifiers</Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <TextField
              label="DOI"
              value={extractedIdentifiers.doi || ''}
              onChange={(e) => handleManualIdentifierUpdate('doi', e.target.value)}
              placeholder="10.XXXX/XXXXX"
              fullWidth
            />
            
            <TextField
              label="ISBN"
              value={extractedIdentifiers.isbn || ''}
              onChange={(e) => handleManualIdentifierUpdate('isbn', e.target.value)}
              placeholder="XXXXXXXXXX"
              fullWidth
            />
            
            <Button 
              variant="outlined" 
              onClick={handleManualFetch}
              disabled={loading || (!extractedIdentifiers.doi && !extractedIdentifiers.isbn)}
            >
              Fetch Metadata
            </Button>
          </Box>
        </Box>
      )}
      
      {/* Metadata editor */}
      {renderMetadataEditor()}
      
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