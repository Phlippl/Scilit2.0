import { useState, useEffect } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardActions from '@mui/material/CardActions';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import SearchIcon from '@mui/icons-material/Search';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer';
import LibraryBooksIcon from '@mui/icons-material/LibraryBooks';
import PostAddIcon from '@mui/icons-material/PostAdd';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Alert from '@mui/material/Alert';

// Sample data to mimic what would come from an API
const sampleDocuments = [
  {
    id: 1,
    title: 'Understanding Vector Databases in Scientific Research',
    authors: 'Smith, John; Johnson, Emily; Lee, Robert',
    year: '2023',
    journal: 'Journal of Data Science',
    uploadDate: '2023-12-15',
    pages: 18,
    citationStyle: 'APA 7th Edition',
    type: 'article',
  },
  {
    id: 2,
    title: 'The Future of AI in Academic Publishing',
    authors: 'Williams, Sarah; Brown, David',
    year: '2022',
    journal: 'AI Review',
    uploadDate: '2023-11-23',
    pages: 25,
    citationStyle: 'Chicago 18th Edition',
    type: 'article',
  },
  {
    id: 3,
    title: 'Natural Language Processing: Fundamentals and Applications',
    authors: 'Garcia, Maria',
    year: '2021',
    publisher: 'Academic Press',
    uploadDate: '2023-10-05',
    pages: 342,
    citationStyle: 'Harvard',
    type: 'book',
  },
];

function Dashboard() {
  const [searchQuery, setSearchQuery] = useState('');
  const [documents, setDocuments] = useState([]);
  const [filteredDocuments, setFilteredDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState(0);
  const [showWelcome, setShowWelcome] = useState(true);

  useEffect(() => {
    // Simulate fetching documents from an API
    setDocuments(sampleDocuments);
    setFilteredDocuments(sampleDocuments);
    
    // After the first visit, don't show the welcome message again
    const timer = setTimeout(() => {
      setShowWelcome(false);
    }, 5000);
    
    return () => clearTimeout(timer);
  }, []);

  const handleSearchChange = (event) => {
    const query = event.target.value.toLowerCase();
    setSearchQuery(query);
    
    if (query.trim() === '') {
      setFilteredDocuments(documents);
    } else {
      const filtered = documents.filter(
        doc => 
          doc.title.toLowerCase().includes(query) ||
          doc.authors.toLowerCase().includes(query) ||
          doc.year.includes(query) ||
          (doc.journal && doc.journal.toLowerCase().includes(query)) ||
          (doc.publisher && doc.publisher.toLowerCase().includes(query))
      );
      setFilteredDocuments(filtered);
    }
  };

  const handleDeleteDocument = (id) => {
    // In a real app, you would call an API to delete the document
    const updatedDocs = documents.filter(doc => doc.id !== id);
    setDocuments(updatedDocs);
    setFilteredDocuments(updatedDocs);
  };

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  return (
    <Container maxWidth="lg">
      {showWelcome && (
        <Alert severity="info" sx={{ mt: 2, mb: 2 }} onClose={() => setShowWelcome(false)}>
          Welcome to your SciLit2.0 Dashboard! Here you can manage all your uploaded documents and access the AI features.
        </Alert>
      )}
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 3, mb: 3 }}>
        <Typography variant="h4" component="h1">
          My Scientific Literature
        </Typography>
        <Button
          component={RouterLink}
          to="/upload"
          variant="contained"
          startIcon={<PostAddIcon />}
        >
          Upload New Document
        </Button>
      </Box>
      
      <Paper elevation={3} sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Search Documents"
              variant="outlined"
              value={searchQuery}
              onChange={handleSearchChange}
              InputProps={{
                endAdornment: <SearchIcon color="action" />,
              }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', justifyContent: { xs: 'flex-start', md: 'flex-end' }, mt: { xs: 1, md: 0 } }}>
              <Tabs value={activeTab} onChange={handleTabChange} aria-label="document type tabs">
                <Tab label="All Documents" />
                <Tab label="Articles" />
                <Tab label="Books" />
              </Tabs>
            </Box>
          </Grid>
        </Grid>
      </Paper>
      
      <Grid container spacing={3}>
        {filteredDocuments.length > 0 ? (
          filteredDocuments
            .filter(doc => {
              if (activeTab === 0) return true;
              if (activeTab === 1) return doc.type === 'article';
              if (activeTab === 2) return doc.type === 'book';
              return true;
            })
            .map((doc) => (
              <Grid item xs={12} key={doc.id}>
                <Card sx={{ display: 'flex', flexDirection: 'column' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box>
                        <Typography variant="h6" component="div" gutterBottom>
                          {doc.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {doc.authors} ({doc.year})
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {doc.journal || doc.publisher} • {doc.pages} pages • Uploaded on {doc.uploadDate}
                        </Typography>
                        <Box sx={{ mt: 1 }}>
                          <Chip 
                            label={doc.type === 'article' ? 'Article' : 'Book'} 
                            size="small" 
                            color={doc.type === 'article' ? 'primary' : 'secondary'} 
                            sx={{ mr: 1 }}
                          />
                          <Chip label={doc.citationStyle} size="small" variant="outlined" />
                        </Box>
                      </Box>
                      <Box>
                        <IconButton aria-label="delete" onClick={() => handleDeleteDocument(doc.id)}>
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    </Box>
                  </CardContent>
                  <Divider />
                  <CardActions>
                    <Button 
                      size="small" 
                      startIcon={<VisibilityIcon />}
                    >
                      View PDF
                    </Button>
                    <Button 
                      size="small" 
                      startIcon={<EditIcon />}
                    >
                      Edit Metadata
                    </Button>
                    <Button 
                      size="small" 
                      startIcon={<QuestionAnswerIcon />}
                      color="primary"
                    >
                      Ask Questions
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            ))
        ) : (
          <Grid item xs={12}>
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <LibraryBooksIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                No Documents Found
              </Typography>
              <Typography variant="body1" color="text.secondary" paragraph>
                {documents.length === 0 
                  ? "You haven't uploaded any documents yet." 
                  : "No documents match your search criteria."}
              </Typography>
              {documents.length === 0 && (
                <Button
                  component={RouterLink}
                  to="/upload"
                  variant="contained"
                  startIcon={<PostAddIcon />}
                >
                  Upload Your First Document
                </Button>
              )}
            </Paper>
          </Grid>
        )}
      </Grid>
    </Container>
  );
}

export default Dashboard;
