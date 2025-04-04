import React, { useState, useEffect, useContext } from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  Card, 
  CardContent, 
  CardActions, 
  Button, 
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Avatar,
  Divider,
  Paper,
  CircularProgress,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { 
  Description as DescriptionIcon,
  DeleteOutline as DeleteIcon,
  Search as SearchIcon,
  CloudDownload as DownloadIcon
} from '@mui/icons-material';
import { AuthContext } from '../App';

const Dashboard = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const auth = useContext(AuthContext);
  
  useEffect(() => {
    // In a real app, fetch documents from backend
    // For demo purposes, we'll use mock data
    
    const fetchDocuments = async () => {
      try {
        // Mock API call
        // const response = await axios.get('/api/documents');
        
        // Mock data
        const mockDocuments = [
          {
            id: '1',
            title: 'Understanding Climate Change Impact on Global Agriculture',
            authors: ['Smith, J.', 'Garcia, M.', 'Chen, W.'],
            publicationDate: '2023-01-15',
            doi: '10.1234/climate.2023.001',
            publisher: 'Journal of Climate Research',
            uploadDate: '2024-12-15',
            fileSize: '1.2 MB',
            type: 'article'
          },
          {
            id: '2',
            title: 'Machine Learning Approaches in Medical Diagnosis',
            authors: ['Johnson, R.', 'Williams, P.'],
            publicationDate: '2023-05-22',
            doi: '10.5678/medtech.2023.045',
            publisher: 'Medical Technology Review',
            uploadDate: '2024-12-10',
            fileSize: '3.4 MB',
            type: 'article'
          },
          {
            id: '3',
            title: 'Artificial Intelligence: Principles and Applications',
            authors: ['Brown, T.'],
            publicationDate: '2022-11-10',
            isbn: '978-3-16-148410-0',
            publisher: 'Tech Publishing House',
            uploadDate: '2024-12-01',
            fileSize: '5.7 MB',
            type: 'book'
          }
        ];
        
        // Simulate network delay
        setTimeout(() => {
          setDocuments(mockDocuments);
          setLoading(false);
        }, 1000);
      } catch (error) {
        console.error('Error fetching documents:', error);
        setLoading(false);
      }
    };
    
    fetchDocuments();
  }, []);
  
  const handleDocumentClick = (document) => {
    setSelectedDocument(document);
    setDialogOpen(true);
  };
  
  const handleDialogClose = () => {
    setDialogOpen(false);
  };
  
  const handleDeleteDocument = (id) => {
    // In a real app, delete document from backend
    // For demo purposes, we'll just update state
    setDocuments(documents.filter(doc => doc.id !== id));
    setDialogOpen(false);
  };
  
  const DocumentDialog = () => {
    if (!selectedDocument) return null;
    
    return (
      <Dialog 
        open={dialogOpen} 
        onClose={handleDialogClose}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>{selectedDocument.title}</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle1" gutterBottom>
                <strong>Authors:</strong> {selectedDocument.authors.join(', ')}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                <strong>Publication Date:</strong> {selectedDocument.publicationDate}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                <strong>Publisher:</strong> {selectedDocument.publisher}
              </Typography>
              {selectedDocument.doi && (
                <Typography variant="subtitle1" gutterBottom>
                  <strong>DOI:</strong> {selectedDocument.doi}
                </Typography>
              )}
              {selectedDocument.isbn && (
                <Typography variant="subtitle1" gutterBottom>
                  <strong>ISBN:</strong> {selectedDocument.isbn}
                </Typography>
              )}
              <Typography variant="subtitle1" gutterBottom>
                <strong>Uploaded:</strong> {selectedDocument.uploadDate}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                <strong>File Size:</strong> {selectedDocument.fileSize}
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%', bgcolor: '#f5f5f5' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Quick Actions
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Button 
                    variant="contained" 
                    startIcon={<SearchIcon />}
                    href={`/query?doc=${selectedDocument.id}`}
                  >
                    Query This Document
                  </Button>
                  <Button 
                    variant="outlined" 
                    startIcon={<DownloadIcon />}
                  >
                    Download PDF
                  </Button>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Close</Button>
          <Button 
            startIcon={<DeleteIcon />} 
            color="error"
            onClick={() => handleDeleteDocument(selectedDocument.id)}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    );
  };
  
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Your Literature
      </Typography>
      
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button 
          variant="contained" 
          color="primary" 
          href="/upload"
        >
          Upload New Document
        </Button>
      </Box>
      
      {documents.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No documents yet
          </Typography>
          <Typography variant="body1" paragraph>
            Upload your first document to get started
          </Typography>
          <Button 
            variant="contained" 
            color="primary" 
            href="/upload"
          >
            Upload Document
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {documents.map((document) => (
            <Grid item xs={12} sm={6} md={4} key={document.id}>
              <Card 
                sx={{ 
                  height: '100%', 
                  display: 'flex', 
                  flexDirection: 'column',
                  cursor: 'pointer',
                  '&:hover': {
                    boxShadow: 6
                  }
                }}
                onClick={() => handleDocumentClick(document)}
              >
                <CardContent sx={{ flexGrow: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Chip 
                      label={document.type === 'book' ? 'Book' : 'Article'} 
                      size="small" 
                      color={document.type === 'book' ? 'secondary' : 'primary'}
                      sx={{ mb: 1 }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {document.uploadDate}
                    </Typography>
                  </Box>
                  
                  <Typography variant="h6" component="h3" gutterBottom>
                    {document.title}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {document.authors.join(', ')}
                  </Typography>
                  
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {document.publisher}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary">
                    {document.publicationDate}
                  </Typography>
                </CardContent>
                <CardActions sx={{ justifyContent: 'flex-end', p: 1 }}>
                  <IconButton 
                    size="small" 
                    color="primary"
                    onClick={(e) => {
                      e.stopPropagation();
                      window.location.href = `/query?doc=${document.id}`;
                    }}
                  >
                    <SearchIcon />
                  </IconButton>
                  <IconButton 
                    size="small" 
                    color="error"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteDocument(document.id);
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
      
      <DocumentDialog />
    </Box>
  );
};

export default Dashboard;