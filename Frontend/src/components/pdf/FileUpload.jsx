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
  DialogActions
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

// Hooks
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

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
    setMetadata(prev => ({
      ...prev,
      [field]: value,
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
      // Dokumentdaten für Speicherung vorbereiten
      const documentData = {
        metadata: {
          ...metadata,
          // Datumsformat korrigieren
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
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('data', JSON.stringify(documentData));

      // In Datenbank speichern
      const savedDoc = await documentsApi.saveDocument(documentData, file);
    
      console.log("Dokument erfolgreich gespeichert:", savedDoc);
      
      setSaveSuccess(true);
      setCurrentStep(3); // Zum finalen Schritt
    } catch (error) {
      console.error('Fehler beim Speichern des Dokuments:', error);
      setError(`Fehler beim Speichern des Dokuments: ${error.message || 'Unbekannter Fehler'}`);
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
        
      case 2: // Metadaten-Überprüfung
        return (
          <>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6">Dokument-Metadaten</Typography>
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
                In Datenbank speichern
              </Button>
            </Box>
            
            {processing && renderProcessingStatus()}
          </>
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
    </Paper>
  );
};

export default FileUpload;