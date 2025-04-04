import { useState } from 'react';
import { Typography, Paper, Button, Box, TextField, Grid, MenuItem, Select, FormControl, InputLabel, CircularProgress, Alert, FormHelperText } from '@mui/material';
import { styled } from '@mui/material/styles';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SaveIcon from '@mui/icons-material/Save';
import FindInPageIcon from '@mui/icons-material/FindInPage';
// In a real app, we would use an actual PDF viewer
// For now, we'll just create a placeholder component
const PDFViewer = ({ file }) => {
  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
        border: '1px dashed #ccc',
        borderRadius: '4px',
        p: 2
      }}
    >
      {file ? (
        <>
          <Typography variant="body1" gutterBottom>
            PDF Preview: {file.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            (PDF viewer integration would be implemented here)
          </Typography>
        </>
      ) : (
        <Typography variant="body1" color="text.secondary">
          No PDF selected
        </Typography>
      )}
    </Box>
  );
};

// Styled component for the file input
const VisuallyHiddenInput = styled('input')({
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  height: 1,
  overflow: 'hidden',
  position: 'absolute',
  bottom: 0,
  left: 0,
  whiteSpace: 'nowrap',
  width: 1,
});

// Citation styles
const citationStyles = [
  { value: 'apa7', label: 'APA 7th Edition' },
  { value: 'chicago18', label: 'Chicago 18th Edition' },
  { value: 'harvard', label: 'Harvard' },
];

function Upload() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [metadataFound, setMetadataFound] = useState(false);
  
  // Metadata state
  const [metadata, setMetadata] = useState({
    title: '',
    authors: '',
    year: '',
    doi: '',
    isbn: '',
    publisher: '',
    journal: '',
    volume: '',
    issue: '',
    pages: '',
    abstract: '',
    keywords: '',
    citationStyle: 'apa7',
    chunkSize: 1000,
    chunkOverlap: 200,
  });

  // Handle file selection
  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError('');
      // In a real app, you would start the OCR and metadata extraction here
      simulateProcessing();
    } else {
      setFile(null);
      setError('Please select a valid PDF file');
    }
  };

  // Simulate the processing of the PDF
  const simulateProcessing = () => {
    setLoading(true);
    setMetadataFound(false);
    
    // Simulate an API call with a timeout
    setTimeout(() => {
      // Mock metadata that would be returned from actual OCR and CrossRef
      const mockMetadata = {
        title: 'Understanding Vector Databases in Scientific Research',
        authors: 'Smith, John; Johnson, Emily; Lee, Robert',
        year: '2023',
        doi: '10.1234/scilit.2023.0001',
        isbn: '',
        publisher: 'Scientific Publishing Co.',
        journal: 'Journal of Data Science',
        volume: '15',
        issue: '4',
        pages: '425-442',
        abstract: 'This paper explores the applications of vector databases in scientific research, focusing on their ability to enhance literature review processes through semantic search capabilities.',
        keywords: 'vector database, literature review, semantic search, NLP',
        citationStyle: 'apa7',
        chunkSize: 1000,
        chunkOverlap: 200,
      };
      
      setMetadata(mockMetadata);
      setLoading(false);
      setMetadataFound(true);
    }, 2000);
  };

  // Handle metadata input changes
  const handleMetadataChange = (event) => {
    const { name, value } = event.target;
    setMetadata((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // Handle save to database
  const handleSave = () => {
    setLoading(true);
    
    // Simulate saving to database
    setTimeout(() => {
      setLoading(false);
      setSuccess(true);
      
      // Reset success message after a few seconds
      setTimeout(() => {
        setSuccess(false);
      }, 5000);
    }, 2000);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" className="page-title">
        Upload Scientific Literature
      </Typography>
      
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>Document successfully stored in the database!</Alert>}
      
      {/* File Upload Section */}
      <Paper elevation={3} className="paper-container">
        <Typography variant="h6" gutterBottom>
          Step 1: Upload PDF Document
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Upload a scientific paper or book in PDF format. The system will automatically extract text via OCR and attempt to identify metadata.
        </Typography>
        
        <Button
          component="label"
          variant="contained"
          startIcon={<CloudUploadIcon />}
          disabled={loading}
        >
          Select PDF File
          <VisuallyHiddenInput type="file" accept=".pdf" onChange={handleFileChange} />
        </Button>
        {file && (
          <Typography variant="body2" sx={{ mt: 1 }}>
            Selected file: {file.name}
          </Typography>
        )}
      </Paper>
      
      {/* Main Upload Layout with Metadata and PDF Preview */}
      {(file || metadataFound) && (
        <Box className="upload-layout" sx={{ mt: 3 }}>
          {/* Left side - Metadata Section */}
          <Box>
            <Paper elevation={3} className="paper-container">
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Step 2: Review Metadata
                </Typography>
                
                {loading && (
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <CircularProgress size={24} sx={{ mr: 1 }} />
                    <Typography variant="body2">Processing...</Typography>
                  </Box>
                )}
                
                {metadataFound && !loading && (
                  <Button 
                    variant="outlined" 
                    size="small"
                    startIcon={<FindInPageIcon />}
                    onClick={simulateProcessing}
                  >
                    Re-Extract
                  </Button>
                )}
              </Box>
              
              <Typography variant="body2" color="text.secondary" paragraph>
                Review and edit the extracted metadata below. Fields marked with * are required.
              </Typography>
              
              <form className="metadata-section">
                <TextField
                  label="Title *"
                  name="title"
                  value={metadata.title}
                  onChange={handleMetadataChange}
                  fullWidth
                  required
                  variant="outlined"
                />
                
                <TextField
                  label="Authors *"
                  name="authors"
                  value={metadata.authors}
                  onChange={handleMetadataChange}
                  fullWidth
                  required
                  variant="outlined"
                  helperText="Separate multiple authors with semicolons (e.g., 'Smith, John; Johnson, Emily')"
                />
                
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      label="Publication Year *"
                      name="year"
                      value={metadata.year}
                      onChange={handleMetadataChange}
                      fullWidth
                      required
                      variant="outlined"
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      label="DOI"
                      name="doi"
                      value={metadata.doi}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                    />
                  </Grid>
                </Grid>
                
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      label="ISBN"
                      name="isbn"
                      value={metadata.isbn}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      label="Publisher"
                      name="publisher"
                      value={metadata.publisher}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                    />
                  </Grid>
                </Grid>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Journal/Book Title"
                      name="journal"
                      value={metadata.journal}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                    />
                  </Grid>
                  <Grid item xs={4} sm={2}>
                    <TextField
                      label="Volume"
                      name="volume"
                      value={metadata.volume}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                    />
                  </Grid>
                  <Grid item xs={4} sm={2}>
                    <TextField
                      label="Issue"
                      name="issue"
                      value={metadata.issue}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                    />
                  </Grid>
                  <Grid item xs={4} sm={2}>
                    <TextField
                      label="Pages"
                      name="pages"
                      value={metadata.pages}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                    />
                  </Grid>
                </Grid>
                
                <TextField
                  label="Abstract"
                  name="abstract"
                  value={metadata.abstract}
                  onChange={handleMetadataChange}
                  fullWidth
                  multiline
                  rows={4}
                  variant="outlined"
                />
                
                <TextField
                  label="Keywords"
                  name="keywords"
                  value={metadata.keywords}
                  onChange={handleMetadataChange}
                  fullWidth
                  variant="outlined"
                  helperText="Separate keywords with commas"
                />
                
                <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
                  Processing Settings
                </Typography>
                
                <FormControl fullWidth variant="outlined">
                  <InputLabel>Citation Style</InputLabel>
                  <Select
                    name="citationStyle"
                    value={metadata.citationStyle}
                    onChange={handleMetadataChange}
                    label="Citation Style"
                  >
                    {citationStyles.map((style) => (
                      <MenuItem key={style.value} value={style.value}>
                        {style.label}
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>
                    Citation style for references and in-text citations
                  </FormHelperText>
                </FormControl>
                
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <TextField
                      label="Chunk Size (chars)"
                      name="chunkSize"
                      type="number"
                      value={metadata.chunkSize}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                      helperText="Size of each text chunk for processing"
                      InputProps={{ inputProps: { min: 100, max: 10000 } }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      label="Chunk Overlap (chars)"
                      name="chunkOverlap"
                      type="number"
                      value={metadata.chunkOverlap}
                      onChange={handleMetadataChange}
                      fullWidth
                      variant="outlined"
                      helperText="Overlap between consecutive chunks"
                      InputProps={{ inputProps: { min: 0, max: 5000 } }}
                    />
                  </Grid>
                </Grid>
                
                <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
                  <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    startIcon={<SaveIcon />}
                    onClick={handleSave}
                    disabled={loading || !metadata.title || !metadata.authors || !metadata.year}
                  >
                    Store in Database
                  </Button>
                </Box>
              </form>
            </Paper>
          </Box>
          
          {/* Right side - PDF Preview */}
          <Box>
            <Paper elevation={3} className="paper-container" sx={{ height: '100%' }}>
              <Typography variant="h6" gutterBottom>
                PDF Preview
              </Typography>
              <Box className="pdf-preview">
                <PDFViewer file={file} />
              </Box>
            </Paper>
          </Box>
        </Box>
      )}
    </Box>
  );
}

export default Upload;
