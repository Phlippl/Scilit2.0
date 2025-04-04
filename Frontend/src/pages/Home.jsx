import { Link as RouterLink } from 'react-router-dom';
import Typography from '@mui/material/Typography';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardMedia from '@mui/material/CardMedia';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SearchIcon from '@mui/icons-material/Search';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import FormatQuoteIcon from '@mui/icons-material/FormatQuote';

function Home() {
  return (
    <Container maxWidth="lg">
      {/* Hero section */}
      <Box
        sx={{
          pt: 8,
          pb: 6,
          textAlign: 'center',
        }}
      >
        <Typography
          component="h1"
          variant="h2"
          align="center"
          color="text.primary"
          gutterBottom
        >
          SciLit2.0
        </Typography>
        <Typography variant="h5" align="center" color="text.secondary" paragraph>
          A modern approach to scientific literature management, analysis, and citation
        </Typography>
        <Box sx={{ mt: 4 }}>
          <Grid container spacing={2} justifyContent="center">
            <Grid item>
              <Button
                component={RouterLink}
                to="/upload"
                variant="contained"
                size="large"
                startIcon={<CloudUploadIcon />}
              >
                Upload Papers
              </Button>
            </Grid>
            <Grid item>
              <Button
                component={RouterLink}
                to="/register"
                variant="outlined"
                size="large"
              >
                Create Account
              </Button>
            </Grid>
          </Grid>
        </Box>
      </Box>

      {/* Purpose and Benefits section */}
      <Typography variant="h4" component="h2" className="page-title" gutterBottom>
        Purpose & Benefits
      </Typography>
      <Paper elevation={3} className="paper-container">
        <Typography variant="body1" paragraph>
          SciLit2.0 is designed to revolutionize how researchers, students, and academics
          interact with scientific literature. By combining OCR technology, metadata extraction,
          and AI-powered analysis, SciLit2.0 transforms the way you manage, search, and cite
          your research materials.
        </Typography>
      </Paper>

      {/* Features section */}
      <Typography variant="h4" component="h2" className="page-title" sx={{ mt: 6 }} gutterBottom>
        Key Features
      </Typography>
      <Grid container spacing={4}>
        {/* Feature 1 */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardMedia
              component="div"
              sx={{
                pt: '56.25%',
                bgcolor: 'primary.light',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <CloudUploadIcon sx={{ fontSize: 60, color: 'white', position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </CardMedia>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography gutterBottom variant="h5" component="h2">
                Easy Upload & OCR
              </Typography>
              <Typography>
                Upload PDFs of scientific papers and books, which are automatically processed with OCR to extract text content.
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Feature 2 */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardMedia
              component="div"
              sx={{
                pt: '56.25%',
                bgcolor: 'secondary.light',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <SearchIcon sx={{ fontSize: 60, color: 'white', position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </CardMedia>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography gutterBottom variant="h5" component="h2">
                Metadata Extraction
              </Typography>
              <Typography>
                Automatically identify DOI or ISBN and fetch comprehensive metadata from CrossRef and other sources.
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Feature 3 */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardMedia
              component="div"
              sx={{
                pt: '56.25%',
                bgcolor: 'info.light',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <AutoAwesomeIcon sx={{ fontSize: 60, color: 'white', position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </CardMedia>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography gutterBottom variant="h5" component="h2">
                AI-Powered Analysis
              </Typography>
              <Typography>
                Leverage NLP and vector databases to store, analyze, and retrieve insights from your scientific literature.
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Feature 4 */}
        <Grid item xs={12} md={6} lg={3}>
          <Card sx={{ height: '100%' }}>
            <CardMedia
              component="div"
              sx={{
                pt: '56.25%',
                bgcolor: 'success.light',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
              }}
            >
              <FormatQuoteIcon sx={{ fontSize: 60, color: 'white', position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }} />
            </CardMedia>
            <CardContent sx={{ flexGrow: 1 }}>
              <Typography gutterBottom variant="h5" component="h2">
                Smart Citations
              </Typography>
              <Typography>
                Generate proper citations in various styles (APA, Chicago, Harvard) with page numbers and full references.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* How It Works section */}
      <Typography variant="h4" component="h2" className="page-title" sx={{ mt: 6 }} gutterBottom>
        How It Works
      </Typography>
      <Paper elevation={3} className="paper-container">
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              1. Upload & Process
            </Typography>
            <Typography variant="body1" paragraph>
              Upload your scientific literature as PDFs. SciLit2.0 uses OCR to extract text and identifies DOI/ISBN to fetch metadata.
            </Typography>
            
            <Typography variant="h6" gutterBottom>
              2. Review & Store
            </Typography>
            <Typography variant="body1" paragraph>
              Review and edit metadata if needed, then store your document in the database, with content chunked for optimal retrieval.
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" gutterBottom>
              3. Query & Analyze
            </Typography>
            <Typography variant="body1" paragraph>
              Ask questions about your stored literature. The AI will provide answers with appropriate citations.
            </Typography>
            
            <Typography variant="h6" gutterBottom>
              4. Cite & Reference
            </Typography>
            <Typography variant="body1" paragraph>
              Generate citations and references in your preferred academic style (APA, Chicago, Harvard) for use in your research.
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* CTA section */}
      <Box
        sx={{
          bgcolor: 'background.paper',
          pt: 8,
          pb: 6,
          mt: 6,
          textAlign: 'center',
        }}
      >
        <Typography variant="h5" align="center" color="text.secondary" paragraph>
          Ready to transform your research workflow?
        </Typography>
        <Button 
          component={RouterLink}
          to="/upload"
          variant="contained" 
          size="large" 
          sx={{ mt: 2 }}
        >
          Get Started Now
        </Button>
      </Box>
    </Container>
  );
}

export default Home;
