// src/pages/HomePage.jsx
import React from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  Container, 
  Grid, 
  Paper, 
  Card, 
  CardContent, 
  CardMedia, 
  CardActions 
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// Icons
import UploadFileIcon from '@mui/icons-material/UploadFile';
import SearchIcon from '@mui/icons-material/Search';
import MenuBookIcon from '@mui/icons-material/MenuBook';

const HomePage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  return (
    <Box>
      {/* Hero-Bereich */}
      <Box 
        sx={{ 
          py: 8, 
          bgcolor: 'primary.main', 
          color: 'primary.contrastText',
          textAlign: 'center',
          borderRadius: { xs: 0, sm: 2 },
          mb: 6
        }}
      >
        <Container maxWidth="md">
          <Typography variant="h2" component="h1" gutterBottom>
            SciLit2.0
          </Typography>
          
          <Typography variant="h5" component="h2" paragraph>
            Intelligente Verwaltung wissenschaftlicher Literatur
          </Typography>
          
          <Typography variant="body1" paragraph sx={{ mb: 4 }}>
            Lade deine wissenschaftlichen Publikationen hoch, verwalte die Metadaten 
            und stelle präzise Abfragen mit automatischer Zitierung.
          </Typography>
          
          <Box sx={{ mt: 4 }}>
            {isAuthenticated ? (
              <Button 
                variant="contained" 
                color="secondary" 
                size="large"
                onClick={() => navigate('/dashboard')}
                sx={{ px: 4, py: 1.5 }}
              >
                Zum Dashboard
              </Button>
            ) : (
              <Grid container spacing={2} justifyContent="center">
                <Grid item>
                  <Button 
                    variant="contained" 
                    color="secondary" 
                    size="large"
                    onClick={() => navigate('/login')}
                  >
                    Anmelden
                  </Button>
                </Grid>
                <Grid item>
                  <Button 
                    variant="outlined" 
                    color="inherit" 
                    size="large"
                    onClick={() => navigate('/register')}
                  >
                    Registrieren
                  </Button>
                </Grid>
              </Grid>
            )}
          </Box>
        </Container>
      </Box>
      
      {/* Funktionsbereich */}
      <Container maxWidth="lg">
        <Typography variant="h4" component="h2" align="center" gutterBottom sx={{ mb: 4 }}>
          Funktionen
        </Typography>
        
        <Grid container spacing={4}>
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <UploadFileIcon sx={{ fontSize: 60, color: 'primary.main' }} />
                </Box>
                <Typography variant="h5" component="h3" gutterBottom align="center">
                  PDF-Upload
                </Typography>
                <Typography variant="body1">
                  Lade wissenschaftliche Publikationen als PDF hoch. 
                  Das System extrahiert automatisch Metadaten wie DOI oder ISBN
                  und ruft weitere Informationen von CrossRef ab.
                </Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: 'center', pb: 2 }}>
                {isAuthenticated && (
                  <Button 
                    variant="outlined" 
                    onClick={() => navigate('/upload')}
                  >
                    Publikation hochladen
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <MenuBookIcon sx={{ fontSize: 60, color: 'primary.main' }} />
                </Box>
                <Typography variant="h5" component="h3" gutterBottom align="center">
                  Literaturverwaltung
                </Typography>
                <Typography variant="body1">
                  Verwalte deine wissenschaftliche Literatur an einem Ort.
                  Bearbeite Metadaten, organisiere Publikationen und
                  behalte den Überblick über deine Quellen.
                </Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: 'center', pb: 2 }}>
                {isAuthenticated && (
                  <Button 
                    variant="outlined" 
                    onClick={() => navigate('/dashboard')}
                  >
                    Literatur verwalten
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                  <SearchIcon sx={{ fontSize: 60, color: 'primary.main' }} />
                </Box>
                <Typography variant="h5" component="h3" gutterBottom align="center">
                  Intelligente Abfragen
                </Typography>
                <Typography variant="body1">
                  Stelle präzise Fragen an deine Literatursammlung und erhalte
                  Antworten mit automatischen Zitierungen. Wähle zwischen verschiedenen
                  Zitationsstilen wie APA, Chicago oder Harvard.
                </Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: 'center', pb: 2 }}>
                {isAuthenticated && (
                  <Button 
                    variant="outlined" 
                    onClick={() => navigate('/query')}
                  >
                    Literatur abfragen
                  </Button>
                )}
              </CardActions>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
};

export default HomePage;