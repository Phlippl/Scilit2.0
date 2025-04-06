// src/components/pdf/FileUpload.jsx
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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
} from '@mui/material';

// Icons
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ArticleIcon from '@mui/icons-material/Article';
import SettingsIcon from '@mui/icons-material/Settings';
import SaveIcon from '@mui/icons-material/Save';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

// Services und Komponenten
import pdfService from '../../services/pdfService';
import * as metadataApi from '../../api/metadata';
import * as documentsApi from '../../api/documents';
import ProcessingSettings from './ProcessingSettings';
import MetadataForm, { detectDocumentType } from './MetadataForm';
import PDFViewer from './PDFViewer';
import { formatToISODate } from '../../utils/dateFormatter';

// Hooks
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

// Full viewport width container wrapper component
const FullWidthContainer = ({ children }) => (
  <Box
    sx={{
      position: 'relative',
      width: '90vw', // Slightly narrower than full viewport width
      left: '50%',
      right: '50%',
      marginLeft: '-45vw', // Half of the width
      marginRight: '-45vw', // Half of the width
      boxSizing: 'border-box',
      px: { xs: 6, sm: 8 }, // More horizontal padding
      py: 2,
    }}
  >
    {children}
  </Box>
);

const FileUpload = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // File-State
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  
  // Verarbeitungs-State
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Verarbeitungseinstellungen
  const [settings, setSettings] = useState({
    maxPages: 0, // 0 bedeutet alle Seiten
    chunkSize: 1000,
    chunkOverlap: 200,
    performOCR: false
  });
  const [showSettings, setShowSettings] = useState(false);
  
  // Ergebnisse
  const [extractedText, setExtractedText] = useState('');
  const [extractedIdentifiers, setExtractedIdentifiers] = useState({ doi: null, isbn: null });
  const [chunks, setChunks] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  // Fehler
  const [error, setError] = useState('');
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Verarbeitungsschritte
  const steps = [
    'PDF hochladen', 
    'Dokument verarbeiten', 
    'Metadaten prüfen', 
    'In Datenbank speichern'
  ];

  // Authentifizierungsprüfung
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/upload' } });
    }
  }, [isAuthenticated, navigate]);
  
  /**
   * Behandelt die Dateiauswahl
   */
  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      // Status für neuen Upload zurücksetzen
      setMetadata(null);
      setExtractedIdentifiers({ doi: null, isbn: null });
      setExtractedText('');
      setChunks([]);
      setError('');
      setCurrentStep(0); // Zurück zum ersten Schritt
      setSaveSuccess(false);
    } else {
      setError('Bitte wähle eine gültige PDF-Datei aus');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Aktualisiert die Verarbeitungseinstellungen
   */
  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings);
  };
  
  /**
   * Verarbeitet die hochgeladene PDF
   */
  const processFile = useCallback(async () => {
    if (!file) {
      setError('Bitte wähle zuerst eine Datei aus');
      setSnackbarOpen(true);
      return;
    }

    setProcessing(true);
    setCurrentStep(1); // Zum Verarbeitungsschritt wechseln
    
    try {
      // PDF-Datei mit Fortschrittsanzeige verarbeiten
      const result = await pdfService.processFile(file, {
        ...settings,
        progressCallback: (stage, percent) => {
          setProcessingStage(stage);
          setProcessingProgress(percent);
        }
      });
      
      // Ergebnisse speichern
      setExtractedText(result.text);
      setChunks(result.chunks);
      setExtractedIdentifiers({
        doi: result.metadata.doi,
        isbn: result.metadata.isbn
      });
      
      // Wenn DOI oder ISBN gefunden wurde, versuche Metadaten zu holen
      if (result.metadata.doi || result.metadata.isbn) {
        setProcessingStage('Hole Metadaten...');
        try {
          let fetchedMetadata = null;
          
          // Zuerst DOI versuchen
          if (result.metadata.doi) {
            fetchedMetadata = await metadataApi.fetchDOIMetadata(result.metadata.doi);
          }
          
          // Wenn DOI nicht funktioniert hat, ISBN versuchen
          if (!fetchedMetadata && result.metadata.isbn) {
            fetchedMetadata = await metadataApi.fetchISBNMetadata(result.metadata.isbn);
          }
          
          if (fetchedMetadata) {
            // Dokumenttyp erkennen und setzen
            const detectedType = detectDocumentType(fetchedMetadata);
            
            // Metadaten mit Dokumenttyp setzen
            setMetadata({
              ...fetchedMetadata,
              type: detectedType
            });
          } else {
            // Leere Metadatenstruktur erstellen
            setMetadata({
              title: '',
              authors: [],
              publicationDate: '',
              publisher: '',
              journal: '',
              doi: result.metadata.doi || '',
              isbn: result.metadata.isbn || '',
              abstract: '',
              type: 'other' // Standard-Dokumenttyp
            });
          }
        } catch (metadataError) {
          console.error('Fehler beim Abrufen der Metadaten:', metadataError);
          
          // Leere Metadatenstruktur erstellen
          setMetadata({
            title: '',
            authors: [],
            publicationDate: '',
            publisher: '',
            journal: '',
            doi: result.metadata.doi || '',
            isbn: result.metadata.isbn || '',
            abstract: '',
            type: 'other' // Standard-Dokumenttyp
          });
        }
      } else {
        // Wenn keine Identifikatoren gefunden wurden
        setMetadata({
          title: '',
          authors: [],
          publicationDate: '',
          publisher: '',
          journal: '',
          doi: '',
          isbn: '',
          abstract: '',
          type: 'other' // Standard-Dokumenttyp
        });
        
        setError('Keine DOI oder ISBN konnte aus dem Dokument extrahiert werden. Bitte gib die Metadaten manuell ein.');
        setSnackbarOpen(true);
      }
      
      setProcessingStage('Verarbeitung abgeschlossen');
      setProcessingProgress(100);
      
      // Zum nächsten Schritt
      setCurrentStep(2);
    } catch (error) {
      console.error('Fehler bei der Dateiverarbeitung:', error);
      setError(`Fehler bei der Dateiverarbeitung: ${error.message}`);
      setSnackbarOpen(true);
      setCurrentStep(0); // Zurück zum Upload-Schritt
    } finally {
      setProcessing(false);
    }
  }, [file, settings]);
  
  /**
   * Behandelt Metadaten-Updates
   */
  const handleMetadataChange = (field, value) => {
    // Datum-Felder in das ISO-Format konvertieren
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
   * Speichert Dokument in Datenbank
   */
  const saveToDatabase = async () => {
    if (!metadata || !metadata.title) {
      setError('Titel ist erforderlich');
      setSnackbarOpen(true);
      return;
    }
  
    setProcessing(true);
    setProcessingStage('Speichere in Datenbank...');
    
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
      
      // Prepare document data with enhanced page tracking
      const documentData = {
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
        chunks: chunksWithPages, // Enhanced chunks with page numbers
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
  
      console.log("Document successfully saved:", savedDoc);
      
      setSaveSuccess(true);
      setCurrentStep(3); // Move to final step
    } catch (error) {
      console.error('Error saving document:', error);
      setError(`Error saving document: ${error.message || 'Unknown error'}`);
      setSnackbarOpen(true);
    } finally {
      setProcessing(false);
      setProcessingStage('');
    }
  };
  
  /**
   * Nach erfolgreicher Speicherung zum Dashboard
   */
  const goToDashboard = () => {
    navigate('/dashboard');
  };
  
  /**
   * Rendert den Upload-Bereich
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
            Klicke, um Datei zu ändern
          </Typography>
        </>
      ) : (
        <>
          <CloudUploadIcon sx={{ fontSize: 50, color: 'primary.main', mb: 1 }} />
          <Typography>PDF-Datei hier ablegen oder klicken zum Durchsuchen</Typography>
          <Typography variant="body2" color="textSecondary">
            Unterstützt PDF-Dateien bis 20MB
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
   * Rendert Status der Verarbeitung
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
          DOI erkannt: {extractedIdentifiers.doi}
        </Alert>
      )}
      
      {extractedIdentifiers.isbn && (
        <Alert severity="success" sx={{ mt: 2 }}>
          ISBN erkannt: {extractedIdentifiers.isbn}
        </Alert>
      )}
      
      {chunks.length > 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Dokument in {chunks.length} Chunks für die Verarbeitung aufgeteilt
        </Alert>
      )}
    </Box>
  );
  
  /**
   * Rendert Inhalt basierend auf aktuellem Schritt
   */
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Upload-Schritt
        return (
          <>
            {renderUploadArea()}
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
              <Button
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => setShowSettings(true)}
              >
                Verarbeitungseinstellungen
              </Button>
              
              <Button
                variant="contained"
                color="primary"
                disabled={!file || processing}
                onClick={processFile}
              >
                PDF verarbeiten
              </Button>
            </Box>
          </>
        );
        
      case 1: // Verarbeitungsschritt
        return (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <ArticleIcon sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
              <Typography variant="h6">{fileName}</Typography>
            </Box>
            
            {renderProcessingStatus()}
          </>
        );
        
      case 2: // Metadaten-Schritt
        return (
          <Box sx={{ display: 'flex', gap: 4, flexDirection: { xs: 'column', md: 'row' } }}>
            {/* Metadaten links */}
            <Box sx={{ width: { xs: '100%', md: '55%' } }}>
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
                  In Datenbank speichern
                </Button>
              </Box>
            </Box>
      
            {/* PDF rechts */}
            <Box sx={{ width: { xs: '100%', md: '45%' } }}>
              {file && <PDFViewer file={file} height="750px" />}
            </Box>
      
            {/* Optional: Ladeanzeige */}
            {processing && renderProcessingStatus()}
          </Box>
        );
      
      case 3: // Erfolgsschritt
        return (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CheckCircleIcon sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              Dokument erfolgreich gespeichert
            </Typography>
            <Typography variant="body1" paragraph>
              Dein Dokument wurde verarbeitet und zu deiner Literaturdatenbank hinzugefügt.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={goToDashboard}
              sx={{ mt: 2 }}
            >
              Zum Dashboard
            </Button>
          </Box>
        );
        
      default:
        return null;
    }
  };
  
  // Das Settings-Dialog rendern
  const renderSettingsDialog = () => (
    <Dialog
      open={showSettings}
      onClose={() => setShowSettings(false)}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Verarbeitungseinstellungen</DialogTitle>
      <DialogContent>
        <ProcessingSettings 
          settings={settings}
          onChange={handleSettingsChange}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setShowSettings(false)}>Abbrechen</Button>
        <Button onClick={() => setShowSettings(false)} variant="contained">
          Einstellungen übernehmen
        </Button>
      </DialogActions>
    </Dialog>
  );
  
  // Use the full-width container for the entire component
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
            maxWidth: 1500 // Set a maximum width for the paper component
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
          
          {/* Schritt-Inhalt */}
          <Box sx={{ width: '100%' }}>
            {renderStepContent()}
          </Box>
        </Paper>
        
        {/* Settings-Dialog */}
        {renderSettingsDialog()}
        
        {/* Fehler-Snackbar */}
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