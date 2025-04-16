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

  // Log state changes for debugging
  useEffect(() => {
    console.log("[DEBUG] Metadata state changed:", metadata);
  }, [metadata]);

  useEffect(() => {
    console.log("[DEBUG] ExtractedIdentifiers state changed:", extractedIdentifiers);
  }, [extractedIdentifiers]);

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
      
      console.log(`[DEBUG] Checking document status for ID: ${id}, attempt: ${statusCheckCount.current}`);
      const response = await documentsApi.getDocumentStatus(id);
      console.log("[DEBUG] Document status response:", response);
      
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
   * Versucht, DOI-Metadaten direkt über die API abzurufen
   */
  const fetchDOIMetadata = async (doi) => {
    console.log(`[DEBUG] Fetching DOI metadata for: ${doi}`);
    try {
      const metadata = await metadataApi.fetchDOIMetadata(doi);
      console.log("[DEBUG] Fetched DOI metadata:", metadata);
      return metadata;
    } catch (error) {
      console.error(`[ERROR] Failed to fetch metadata for DOI ${doi}:`, error);
      return null;
    }
  };

  /**
   * Versucht, ISBN-Metadaten direkt über die API abzurufen
   */
  const fetchISBNMetadata = async (isbn) => {
    console.log(`[DEBUG] Fetching ISBN metadata for: ${isbn}`);
    try {
      const metadata = await metadataApi.fetchISBNMetadata(isbn);
      console.log("[DEBUG] Fetched ISBN metadata:", metadata);
      return metadata;
    } catch (error) {
      console.error(`[ERROR] Failed to fetch metadata for ISBN ${isbn}:`, error);
      return null;
    }
  };

  /**
   * Schnelle Voranalyse der Datei (nur für DOI/ISBN)
   */
  const quickAnalyzeFile = async () => {
    console.log("[DEBUG] Starting quickAnalyzeFile with file:", file ? file.name : "no file");
    
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
      
      const settingsData = {
        quickScan: true,
        maxPages: 10, // Nur die ersten 10 Seiten für DOI/ISBN durchsuchen
        performOCR: settings.performOCR // OCR-Einstellung aus den Benutzereinstellungen übernehmen
      };
      
      console.log("[DEBUG] Sending quick analyze request with settings:", settingsData);
      formData.append('data', JSON.stringify(settingsData));
      
      // Anfrage an den Endpunkt für schnelle Analyse mit detaillierter Fehlerbehandlung
      console.log("[DEBUG] Making quick-analyze fetch request");
      const response = await fetch('/api/documents/quick-analyze', {
        method: 'POST',
        body: formData
      });
      
      console.log("[DEBUG] Quick-analyze response status:", response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error("[ERROR] Server error response:", errorData);
        throw new Error(errorData.error || `Server-Fehler: ${response.status}`);
      }
      
      const result = await response.json();
      console.log("[DEBUG] Quick-analyze result:", result);
      
      // Extrahierte Identifikatoren speichern
      const extractedIds = {
        doi: result.identifiers?.doi,
        isbn: result.identifiers?.isbn
      };
      console.log("[DEBUG] Extracted identifiers:", extractedIds);
      setExtractedIdentifiers(extractedIds);
      
      // Temporäre Dokument-ID für spätere Verarbeitung speichern
      console.log("[DEBUG] Setting temp_id:", result.temp_id);
      setTempDocumentId(result.temp_id);
      
      // Zusätzlicher Versuch, Metadaten direkt über API zu holen, falls im result nicht vorhanden
      let enhancedMetadata = result.metadata || {};
      
      // Wenn DOI gefunden wurde, aber keine Metadaten zurückgegeben wurden, versuchen wir es direkt mit der API
      if (extractedIds.doi && (!result.metadata || Object.keys(result.metadata).length === 0)) {
        console.log("[DEBUG] No metadata in result but DOI found, trying to fetch directly");
        const doiMetadata = await fetchDOIMetadata(extractedIds.doi);
        if (doiMetadata) {
          console.log("[DEBUG] Successfully fetched DOI metadata directly");
          enhancedMetadata = doiMetadata;
        }
      }
      // Dasselbe für ISBN
      else if (extractedIds.isbn && (!result.metadata || Object.keys(result.metadata).length === 0)) {
        console.log("[DEBUG] No metadata in result but ISBN found, trying to fetch directly");
        const isbnMetadata = await fetchISBNMetadata(extractedIds.isbn);
        if (isbnMetadata) {
          console.log("[DEBUG] Successfully fetched ISBN metadata directly");
          enhancedMetadata = isbnMetadata;
        }
      }
      
      // Metadaten setzen und bearbeiten
      if (enhancedMetadata && Object.keys(enhancedMetadata).length > 0) {
        console.log("[DEBUG] Processing metadata:", enhancedMetadata);
        
        // Valid document types in our application
        const validTypes = ['article', 'book', 'edited_book', 'conference', 'thesis', 
                          'report', 'newspaper', 'website', 'interview', 'press', 'other'];
        
        // Mapping function similar to the one in metadata API
        const typeMapping = {
          'journal-article': 'article',
          'book': 'book',
          'book-chapter': 'book',
          'monograph': 'book',
          'edited-book': 'edited_book',
          'proceedings-article': 'conference',
          'proceedings': 'conference',
          'conference-paper': 'conference',
          'dissertation': 'thesis',
          'report': 'report',
          'report-component': 'report',
          'journal': 'article',
          'newspaper-article': 'newspaper',
          'website': 'website',
          'peer-review': 'article',
          'standard': 'report',
          'dataset': 'other',
          'posted-content': 'other',
          'reference-entry': 'other'
        };
        
        // Sanitize the type
        if (enhancedMetadata.type) {
          if (!validTypes.includes(enhancedMetadata.type)) {
            // Try to map the type
            const mappedType = typeMapping[enhancedMetadata.type] || 
                            (enhancedMetadata.type.includes('book') ? 'book' : 
                            (enhancedMetadata.type.includes('journal') ? 'article' : 'other'));
            
            console.log(`[DEBUG] Sanitizing type from ${enhancedMetadata.type} to ${mappedType}`);
            enhancedMetadata.type = mappedType;
          }
        } else {
          // Set a default type if none exists
          const detectedType = detectDocumentType(enhancedMetadata) || 'other';
          console.log(`[DEBUG] No type specified, detected type: ${detectedType}`);
          enhancedMetadata.type = detectedType;
        }
        
        // Ensure authors is properly formatted
        if (enhancedMetadata.authors) {
          console.log("[DEBUG] Original authors format:", enhancedMetadata.authors);
          if (typeof enhancedMetadata.authors === 'string') {
            try {
              // Try to parse JSON string
              enhancedMetadata.authors = JSON.parse(enhancedMetadata.authors);
            } catch (e) {
              // If not valid JSON, treat as comma-separated
              enhancedMetadata.authors = enhancedMetadata.authors.split(',').map(name => ({ name: name.trim() }));
            }
          } else if (!Array.isArray(enhancedMetadata.authors)) {
            // Convert to array if not already
            enhancedMetadata.authors = [{ name: String(enhancedMetadata.authors) }];
          }
          
          // Ensure each author has name property
          enhancedMetadata.authors = enhancedMetadata.authors.map(author => {
            if (typeof author === 'string') {
              return { name: author };
            } else if (typeof author === 'object' && !author.name && (author.given || author.family)) {
              return { 
                name: `${author.family || ''}, ${author.given || ''}`.trim(),
                orcid: author.ORCID || author.orcid || ''
              };
            }
            return author;
          });
          console.log("[DEBUG] Formatted authors:", enhancedMetadata.authors);
        }
        
        // Add DOI and ISBN if available in identifiers but not in metadata
        if (extractedIds.doi && !enhancedMetadata.doi) {
          enhancedMetadata.doi = extractedIds.doi;
        }
        if (extractedIds.isbn && !enhancedMetadata.isbn) {
          enhancedMetadata.isbn = extractedIds.isbn;
        }
        
        // Format date fields to ISO format if needed
        if (enhancedMetadata.publicationDate) {
          enhancedMetadata.publicationDate = formatToISODate(enhancedMetadata.publicationDate);
        }
        
        console.log("[DEBUG] Final enhanced metadata to set:", enhancedMetadata);
        setMetadata(enhancedMetadata);
      } else {
        // Leere Metadaten erstellen, wenn keine gefunden wurden
        console.log("[DEBUG] No metadata found, creating empty metadata");
        createEmptyMetadata({
          doi: extractedIds.doi,
          isbn: extractedIds.isbn
        });
      }
      
      setProcessingStage('Identifikatoren extrahiert');
      setProcessingProgress(100);
      setCurrentStep(2); // Zu Metadaten-Schritt wechseln
      
    } catch (error) {
      console.error('[ERROR] Fehler bei der schnellen Analyse:', error);
      setProcessingError(`Fehler bei der Voranalyse: ${error.message}`);
      
      // Trotz Fehler zum Metadaten-Schritt wechseln, falls wir eine temporäre ID haben
      if (tempDocumentId) {
        console.log("[DEBUG] Despite error, continuing to metadata step with empty metadata");
        createEmptyMetadata();
        setCurrentStep(2);
      } else {
        console.log("[DEBUG] Returning to upload step due to error and no tempDocumentId");
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
    console.log("[DEBUG] File selected:", selectedFile);
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
    console.log("[DEBUG] Resetting upload state");
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
    console.log("[DEBUG] Settings changed:", newSettings);
    setSettings(newSettings);
  };
  
  /**
   * Die Datei verarbeiten
   */
  const processFile = useCallback(async () => {
    console.log("[DEBUG] processFile called");
    // Direkt zur schnellen Analyse wechseln
    await quickAnalyzeFile();
  }, [file, settings]);
  
  /**
   * Leere Metadatenstruktur mit extrahierten Identifikatoren erstellen
   */
  const createEmptyMetadata = (extractedData = {}) => {
    console.log("[DEBUG] Creating empty metadata with:", extractedData);
    // Titel aus Dateinamen ableiten
    const fileTitle = fileName ? fileName.replace(/\.pdf$/i, '') : '';
    
    const emptyMetadata = {
      title: fileTitle,
      authors: [],
      publicationDate: '',
      publisher: '',
      journal: '',
      doi: extractedData?.doi || '',
      isbn: extractedData?.isbn || '',
      abstract: '',
      type: 'other'
    };
    
    console.log("[DEBUG] Setting empty metadata:", emptyMetadata);
    setMetadata(emptyMetadata);
    
    if (!extractedData?.doi && !extractedData?.isbn) {
      setError('Keine DOI oder ISBN konnte aus dem Dokument extrahiert werden. Bitte geben Sie die Metadaten manuell ein.');
      setSnackbarOpen(true);
    }
  };
  
  /**
   * Metadatenänderungen behandeln
   */
  const handleMetadataChange = (field, value) => {
    console.log(`[DEBUG] Metadata field ${field} changed to:`, value);
    
    // Datumsfelder formatieren
    let formattedValue = value;
    if (field === 'publicationDate' || field === 'date' || 
        field === 'conferenceDate' || field === 'lastUpdated' || 
        field === 'accessDate') {
      formattedValue = formatToISODate(value);
    }

    setMetadata(prev => {
      const updated = {
        ...prev,
        [field]: formattedValue,
      };
      console.log(`[DEBUG] Updated metadata after field ${field} change:`, updated);
      return updated;
    });
  };

  /**
   * Verarbeitung abbrechen
   */
  const cancelProcessing = async () => {
    try {
      if (documentId) {
        console.log(`[DEBUG] Canceling processing for document ${documentId}`);
        await fetch(`/api/documents/cancel-processing/${documentId}`, {
          method: 'POST'
        });
        setProcessingFailed(true);
        setError('Verarbeitung wurde abgebrochen');
        setSnackbarOpen(true);
        stopStatusPolling();
      }
    } catch (err) {
      console.error('[ERROR] Fehler beim Abbrechen:', err);
    }
  };
  
  /**
   * Dokument in Datenbank speichern
   */
  const saveToDatabase = async () => {
    console.log("[DEBUG] saveToDatabase called with metadata:", metadata);
    
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
  
      console.log("[DEBUG] Saving document with data:", documentData);
      
      // Dokument mit Datei speichern
      const savedDoc = await documentsApi.saveDocument(documentData, file);
      console.log("[DEBUG] Document saved successfully:", savedDoc);
      
      // Dokument-ID für Statusprüfung speichern
      const docId = savedDoc.document_id || savedDoc.id;
      console.log(`[DEBUG] Setting document ID: ${docId}`);
      setDocumentId(docId);
      setProcessingStage('Verarbeitungsfortschritt überprüfen...');
      setProcessingProgress(0);
      
    } catch (error) {
      console.error('[ERROR] Fehler beim Speichern des Dokuments:', error);
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