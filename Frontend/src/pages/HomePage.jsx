// src/pages/HomePage.jsx
import React from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Button, 
  Paper, 
  Grid, 
  Card, 
  CardContent, 
  CardActions 
} from '@mui/material';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// Icons
import SearchIcon from '@mui/icons-material/Search';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import SchoolIcon from '@mui/icons-material/School';

const HomePage = () => {
  const { isAuthenticated } = useAuth();
  
  return (
    <Container maxWidth="lg">
      {/* Hero Section */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 4, md: 6 },
          mt: 4,
          mb: 6,
          backgroundColor: 'primary.light',
          color: 'primary.contrastText',
          borderRadius: 2,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ maxWidth: { xs: '100%', md: '60%' } }}>
          <Typography variant="h3" component="h1" gutterBottom fontWeight="bold">
            Manage Academic Literature with AI
          </Typography>
          
          <Typography variant="h6" sx={{ mb: 4 }} color="primary.contrastText">
            Upload papers, extract metadata automatically, and use AI to query and cite your academic collection.
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {isAuthenticated ? (
              <>
                <Button 
                  component={Link} 
                  to="/dashboard" 
                  variant="contained" 
                  size="large" 
                  color="secondary"
                >
                  Go to Dashboard
                </Button>
                <Button 
                  component={Link} 
                  to="/upload" 
                  variant="outlined" 
                  size="large"
                  sx={{ backgroundColor: 'rgba(255,255,255,0.9)' }}
                >
                  Upload Paper
                </Button>
              </>
            ) : (
              <>
                <Button 
                  component={Link} 
                  to="/register" 
                  variant="contained" 
                  size="large"
                  color="secondary"
                >
                  Get Started
                </Button>
                <Button 
                  component={Link} 
                  to="/login" 
                  variant="outlined" 
                  size="large"
                  sx={{ backgroundColor: 'rgba(255,255,255,0.9)' }}
                >
                  Log In
                </Button>
              </>
            )}
          </Box>
        </Box>
        
        {/* Background decoration */}
        <Box 
          sx={{ 
            position: 'absolute',
            right: { xs: -100, md: 0 },
            bottom: { xs: -50, md: 0 },
            opacity: 0.2,
            transform: 'rotate(-10deg)',
            fontSize: 300
          }}
        >
          <SchoolIcon sx={{ fontSize: 'inherit' }} />
        </Box>
      </Paper>
      
      {/* Features Section */}
      <Box sx={{ py: 6 }}>
        <Typography variant="h4" component="h2" textAlign="center" gutterBottom>
          Key Features
        </Typography>
        
        <Typography variant="body1" textAlign="center" color="text.secondary" sx={{ mb: 6, maxWidth: 700, mx: 'auto' }}>
          SciLit2.0 helps you manage your academic resources efficiently with powerful AI-driven tools.
        </Typography>
        
        <Grid container spacing={4}>
          {/* Feature 1 */}
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <UploadFileIcon color="primary" sx={{ fontSize: 50 }} />
                </Box>
                <Typography variant="h5" component="h3" textAlign="center" gutterBottom>
                  Smart PDF Processing
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Upload academic PDFs and automatically extract DOI, ISBN, and metadata from CrossRef. OCR processing ensures even scanned documents are searchable.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          {/* Feature 2 */}
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <MenuBookIcon color="primary" sx={{ fontSize: 50 }} />
                </Box>
                <Typography variant="h5" component="h3" textAlign="center" gutterBottom>
                  Vector Database Storage
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Your documents are intelligently chunked and stored in a vector database, enabling semantic search and retrieval for more accurate information access.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          {/* Feature 3 */}
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <SearchIcon color="primary" sx={{ fontSize: 50 }} />
                </Box>
                <Typography variant="h5" component="h3" textAlign="center" gutterBottom>
                  AI-Powered Querying
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Ask questions in natural language and get answers with proper citations. Choose from APA, Chicago, or Harvard citation styles for academic writing.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
      
      {/* Call to Action */}
      <Paper sx={{ p: 4, mb: 6, textAlign: 'center', borderRadius: 2 }}>
        <Typography variant="h5" gutterBottom>
          Ready to organize your research?
        </Typography>
        <Typography variant="body1" paragraph>
          Start using SciLit2.0 today to manage your academic literature more efficiently.
        </Typography>
        <Button 
          component={Link} 
          to={isAuthenticated ? "/dashboard" : "/register"} 
          variant="contained" 
          size="large"
        >
          {isAuthenticated ? "Go to Dashboard" : "Sign Up Now"}
        </Button>
      </Paper>
    </Container>
  );
};

export default HomePage;