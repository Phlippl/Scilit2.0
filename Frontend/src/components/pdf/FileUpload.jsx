// src/components/pdf/FileUpload.jsx
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Alert, 
  Snackbar, 
  Stepper, 
  Step, 
  StepLabel, 
  Button, 
  CircularProgress,
  LinearProgress 
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

// Services und Utilities
import * as documentsApi from '../../api/documents';
import * as metadataApi from '../../api/metadata';
import { formatToISODate } from '../../utils/dateFormatter';
import { detectDocumentType } from './MetadataForm';

// Subkomponenten
import UploadArea from './upload/UploadArea';
import ProcessingStep from './upload/ProcessingStep';
import MetadataStep from './upload/MetadataStep';
import SaveStep from './upload/SaveStep';
import SettingsDialog from './upload/SettingsDialog';
import ProcessingErrorDialog from './upload/ProcessingErrorDialog';

// Container-Komponente für Vollbreite
const FullWidthContainer = ({ children }) => (
  <Box
    sx={{
      position: 'relative',
      width: '90vw',
      left: '50%',
      right: '50%',
      marginLeft: '-45vw',
      marginRight: '-45vw',
      boxSizing: 'border-box',
      px: { xs: 2, sm: 8 },
      py: 2,
    }}
  >
    {children}
  </Box>
);

const FileUpload = () => {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const statusCheckInterval = 3000; // 3 Sekunden zwischen Statusprüfungen
  const maxStatusChecks = 120; // Max 6 Minuten Polling (120 * 3s = 360s)
  const statusCheckCount = useRef(0);
  const statusIntervalRef = useRef(null);
  
  // Dateizustand
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  
  // Verarbeitungszustand
  const [processing, setProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  
  // Dokument-Tracking
  const [documentId, setDocumentId] = useState(null);
  const [tempDocumentId, setTempDocumentId] = useState(null);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [processingFailed, setProcessingFailed] = useState(false);
  
  // Fehlerbehandlung
  const [processingError, setProcessingError] = useState(null);
  
  // Verarbeitungseinstellungen
  const [settings, setSettings] = useState({
    maxPages: 0,
    chunkSize: 1000,
    chunkOverlap: 200,
    performOCR: false
  });
  const [showSettings, setShowSettings] = useState(false);
  
  // Ergebnisse
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
    'Dokument vorverarbeiten', 
    'Metadaten prüfen', 
    'In Datenbank speichern'
  ];

  // Authentifizierungsprüfung
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/upload' } });
    }
  }, [isAuthenticated, navigate]);
  
  // Bereinigung des Status-Polling beim Unmount
  useEffect(() => {
    return () => {
      if (statusIntervalRef.current) {
        clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
      }
    };
  }, []);
  
  // Polling für Dokumentstatus wenn documentId gesetzt ist
  useEffect(() => {
    if (documentId && currentStep === 3 && !processingComplete && !processingFailed) {
      // Polling starten
      if (!statusIntervalRef.current) {
        setIsCheckingStatus(true);
        statusCheckCount.current = 0;
        checkDocumentStatus(documentId);
        
        statusIntervalRef.current = setInterval(() => {
          checkDocumentStatus(documentId);
        }, statusCheckInterval);
      }
    } else if (processingComplete || processingFailed) {
      // Polling stoppen wenn Verarbeitung abgeschlossen oder fehlgeschlagen
      stopStatusPolling();
    }
    
    return () => stopStatusPolling();
  }, [documentId, currentStep, processingComplete, processingFailed]);
  
  // Sicherheits-Timeout für lang laufende Verarbeitungen
  useEffect(() => {
    let processingTimer = null;
    
    if (processing) {
      processingTimer = setTimeout(() => {
        if (processing) {
          setProcessing(false);
          setProcessingError("Die Verarbeitung hat zu lange gedauert. Die Operation läuft möglicherweise noch im Hintergrund, aber die Benutzeroberfläche wurde entsperrt.");
        }
      }, 600000); // 10 Minuten
    }
    
    return () => {
      if (processingTimer) {
        clearTimeout(processingTimer);
      }
    };
  }, [processing]);
  
  /**
   * Statuspolling stoppen
   */
  const stopStatusPolling = () => {
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
      statusIntervalRef.current = null;
      setIsCheckingStatus(false);
    }
  };
  
  /**
   * Dokumentverarbeitungsstatus prüfen
   */
  const checkDocumentStatus = async (id) => {
    try {
      // Zähler erhöhen
      statusCheckCount.current++;
      
      // Polling nach Max-Versuchen stoppen
      if (statusCheckCount.current > maxStatusChecks) {
        setProcessingError("Zeitüberschreitung bei der Dokumentverarbeitung.");
        stopStatusPolling();
        return;
      }
      
      const response = await documentsApi.getDocumentStatus(id);
      
      // Status prüfen
      switch (response.status) {
        case 'completed':
          setProcessingProgress(100);
          setProcessingStage('Verarbeitung abgeschlossen');
          setProcessingComplete(true);
          setSaveSuccess(true);
          stopStatusPolling();
          break;
          
        case 'completed_with_warnings':
          setProcessingProgress(100);
          setProcessingStage('Verarbeitung mit Warnungen abgeschlossen');
          setProcessingComplete(true);
          setSaveSuccess(true);
          stopStatusPolling();
          break;
          
        case 'processing':
          setProcessingProgress(response.progress || 0);
          setProcessingStage(response.message || 'Verarbeitung läuft...');
          break;
          
        case 'error':
          setProcessingFailed(true);
          setError(response.message || 'Fehler bei der Verarbeitung');
          setSnackbarOpen(true);
          stopStatusPolling();
          break;

        case 'canceled':
          setProcessingFailed(true);
          setError('Verarbeitung wurde abgebrochen');
          setSnackbarOpen(true);
          stopStatusPolling();
          break;
          
        default:
          // Unbekannten Status behandeln
          console.warn(`Unbekannter Verarbeitungsstatus: ${response.status}`);
      }
    } catch (error) {
      console.error('Fehler beim Prüfen des Dokumentstatus:', error);
      // Bei Netzwerkfehlern Polling nicht stoppen - könnte temporär sein
    }
  };

  /**
 * Schnelle Voranalyse der Datei (nur für DOI/ISBN)
 */
const quickAnalyzeFile = async () => {
  if (!file) {
    setError('Bitte wähle zuerst eine Datei aus');
    setSnackbarOpen(true);
    return;
  }

  setProcessing(true);
  setCurrentStep(1); // Zu Vorverarbeitungsschritt wechseln
  setProcessingStage('Identifikatoren extrahieren...');
  setProcessingProgress(10);
  
  try {
    // Formular nur mit Datei und Einstellung für schnelle Analyse
    const formData = new FormData();
    formData.append('file', file);
    formData.append('data', JSON.stringify({
      quickScan: true,
      maxPages: 10 // Nur die ersten 10 Seiten für DOI/ISBN durchsuchen
    }));
    
    // Anfrage an den Endpunkt für schnelle Analyse mit Fehlerbehandlung
    const response = await fetch('/api/documents/quick-analyze', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Server-Fehler: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Extrahierte Identifikatoren speichern
    setExtractedIdentifiers({
      doi: result.identifiers?.doi,
      isbn: result.identifiers?.isbn
    });
    
    // Temporäre Dokument-ID für spätere Verarbeitung speichern
    setTempDocumentId(result.temp_id);
    
    // Metadaten setzen und bearbeiten
    if (result.metadata && Object.keys(result.metadata).length > 0) {
      setMetadata({
        ...result.metadata,
        type: result.metadata.type || detectDocumentType(result.metadata) || 'other'
      });
    } else {
      // Leere Metadaten erstellen, wenn keine gefunden wurden
      createEmptyMetadata({
        doi: result.identifiers?.doi,
        isbn: result.identifiers?.isbn
      });
    }
    
    setProcessingStage('Identifikatoren extrahiert');
    setProcessingProgress(100);
    setCurrentStep(2); // Zu Metadaten-Schritt wechseln
    
  } catch (error) {
    console.error('Fehler bei der schnellen Analyse:', error);
    setProcessingError(`Fehler bei der Voranalyse: ${error.message}`);
    
    // Trotz Fehler zum Metadaten-Schritt wechseln, falls wir eine temporäre ID haben
    if (tempDocumentId) {
      createEmptyMetadata();
      setCurrentStep(2);
    } else {
      setCurrentStep(0); // Zurück zum Upload-Schritt
    }
  } finally {
    setProcessing(false);
  }
};
  
  /**
   * Dateiauswahl behandeln
   */
  const handleFileChange = (selectedFile) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setFileName(selectedFile.name);
      resetUploadState();
    } else {
      setError('Bitte wähle eine gültige PDF-Datei aus');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Upload-Zustand zurücksetzen
   */
  const resetUploadState = () => {
    setMetadata(null);
    setExtractedIdentifiers({ doi: null, isbn: null });
    setChunks([]);
    setError('');
    setCurrentStep(0);
    setSaveSuccess(false);
    setProcessingComplete(false);
    setProcessingFailed(false);
    setDocumentId(null);
    setTempDocumentId(null);
    setProcessingError(null);
    stopStatusPolling();
  };
  
  /**
   * Verarbeitungseinstellungen aktualisieren
   */
  const handleSettingsChange = (newSettings) => {
    setSettings(newSettings);
  };
  
  /**
   * Die Datei verarbeiten
   */
  const processFile = useCallback(async () => {
    // Direkt zur schnellen Analyse wechseln
    await quickAnalyzeFile();
  }, [file, settings]);
  
  /**
   * Leere Metadatenstruktur mit extrahierten Identifikatoren erstellen
   */
  const createEmptyMetadata = (extractedData = {}) => {
    // Titel aus Dateinamen ableiten
    const fileTitle = fileName ? fileName.replace(/\.pdf$/i, '') : '';
    
    setMetadata({
      title: fileTitle,
      authors: [],
      publicationDate: '',
      publisher: '',
      journal: '',
      doi: extractedData?.doi || '',
      isbn: extractedData?.isbn || '',
      abstract: '',
      type: 'other'
    });
    
    if (!extractedData?.doi && !extractedData?.isbn) {
      setError('Keine DOI oder ISBN konnte aus dem Dokument extrahiert werden. Bitte geben Sie die Metadaten manuell ein.');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Metadatenänderungen behandeln
   */
  const handleMetadataChange = (field, value) => {
    // Datumsfelder formatieren
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
   * Verarbeitung abbrechen
   */
  const cancelProcessing = async () => {
    try {
      if (documentId) {
        await fetch(`/api/documents/cancel-processing/${documentId}`, {
          method: 'POST'
        });
        setProcessingFailed(true);
        setError('Verarbeitung wurde abgebrochen');
        setSnackbarOpen(true);
        stopStatusPolling();
      }
    } catch (err) {
      console.error('Fehler beim Abbrechen:', err);
    }
  };
  
  /**
   * Dokument in Datenbank speichern
   */
  const saveToDatabase = async () => {
    if (!metadata || !metadata.title) {
      setError('Titel ist erforderlich');
      setSnackbarOpen(true);
      return;
    }
  
    setProcessing(true);
    setProcessingStage('Speichere in Datenbank...');
    setCurrentStep(3); // Zu Speichern-Schritt wechseln
    
    try {
      // Dokument-Daten erstellen
      const documentData = {
        title: metadata.title.trim(),
        type: metadata.type || 'article',
        authors: metadata.authors || [],
        publicationDate: formatToISODate(metadata.publicationDate) || new Date().toISOString().split('T')[0],
        date: metadata.date ? formatToISODate(metadata.date) : undefined,
        conferenceDate: metadata.conferenceDate ? formatToISODate(metadata.conferenceDate) : undefined,
        lastUpdated: metadata.lastUpdated ? formatToISODate(metadata.lastUpdated) : undefined,
        accessDate: metadata.accessDate ? formatToISODate(metadata.accessDate) : undefined,
        journal: metadata.journal,
        volume: metadata.volume,
        issue: metadata.issue,
        pages: metadata.pages,
        publisher: metadata.publisher,
        doi: metadata.doi,
        isbn: metadata.isbn,
        abstract: metadata.abstract,
        // Verarbeitungseinstellungen
        maxPages: settings.maxPages,
        performOCR: settings.performOCR,
        chunkSize: settings.chunkSize,
        chunkOverlap: settings.chunkOverlap,
        // Temporäre ID aus dem ersten Schritt
        temp_document_id: tempDocumentId
      };
  
      // Dokument mit Datei speichern
      const savedDoc = await documentsApi.saveDocument(documentData, file);
      
      // Dokument-ID für Statusprüfung speichern
      setDocumentId(savedDoc.document_id || savedDoc.id);
      setProcessingStage('Verarbeitungsfortschritt überprüfen...');
      setProcessingProgress(0);
      
    } catch (error) {
      console.error('Fehler beim Speichern des Dokuments:', error);
      let errorMsg = "Fehler beim Speichern des Dokuments: ";
      
      if (error.response?.data?.error) {
        errorMsg += error.response.data.error;
      } else if (error.message) {
        errorMsg += error.message;
      } else {
        errorMsg += "Unbekannter Fehler";
      }
      
      setError(errorMsg);
      setSnackbarOpen(true);
      setProcessingFailed(true);
    } finally {
      setProcessing(false);
    }
  };
  
  /**
   * Zum Dashboard nach erfolgreichem Speichern gehen
   */
  const goToDashboard = () => {
    navigate('/dashboard');
  };
  
  /**
   * Inhalt basierend auf aktuellem Schritt rendern
   */
  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Upload-Schritt
        return (
          <UploadArea 
            file={file}
            fileName={fileName}
            onFileChange={handleFileChange}
            onProcess={processFile}
            onOpenSettings={() => setShowSettings(true)}
            processing={processing}
          />
        );
        
      case 1: // Vorverarbeitungsschritt
        return (
          <ProcessingStep 
            fileName={fileName}
            processingStage={processingStage}
            processingProgress={processingProgress}
            extractedIdentifiers={extractedIdentifiers}
            chunks={chunks}
          />
        );
        
      case 2: // Metadaten-Schritt
        return (
          <MetadataStep 
            metadata={metadata}
            file={file}
            onMetadataChange={handleMetadataChange}
            onSave={saveToDatabase}
            processing={processing}
          />
        );
      
      case 3: // Speichern/Erfolg-Schritt
        return (
          <SaveStep 
            isCheckingStatus={isCheckingStatus}
            processingFailed={processingFailed}
            saveSuccess={saveSuccess}
            processingComplete={processingComplete}
            error={error}
            processingStage={processingStage}
            processingProgress={processingProgress}
            onGoToDashboard={goToDashboard}
            onRetry={() => setCurrentStep(0)}
            onCancel={cancelProcessing}
          />
        );
        
      default:
        return null;
    }
  };
  
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
            maxWidth: 1500
          }}
        >
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
          
          {/* Schrittinhalt */}
          <Box sx={{ width: '100%' }}>
            {renderStepContent()}
          </Box>
        </Paper>
        
        {/* Dialoge */}
        <SettingsDialog
          open={showSettings}
          settings={settings}
          onClose={() => setShowSettings(false)}
          onChange={handleSettingsChange}
        />
        
        {processingError && (
          <ProcessingErrorDialog
            open={!!processingError}
            error={processingError}
            processingStage={processingStage}
            onClose={() => setProcessingError(null)}
            onRetry={() => {
              setProcessingError(null);
              processFile();
            }}
            onChangeSettings={() => {
              setProcessingError(null);
              setShowSettings(true);
            }}
          />
        )}
        
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