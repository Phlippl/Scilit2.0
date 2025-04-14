// src/components/pdf/upload/UploadArea.jsx
import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ArticleIcon from '@mui/icons-material/Article';
import SettingsIcon from '@mui/icons-material/Settings';

/**
 * Upload-Bereich Komponente für PDF-Dateien
 * 
 * @param {Object} props - Komponenten-Properties
 * @param {File} props.file - Die ausgewählte Datei (null wenn keine)
 * @param {string} props.fileName - Name der ausgewählten Datei
 * @param {Function} props.onFileChange - Callback für Dateiänderungen
 * @param {Function} props.onProcess - Callback für Verarbeitungsstart
 * @param {Function} props.onOpenSettings - Callback zum Öffnen der Einstellungen
 * @param {boolean} props.processing - Gibt an, ob gerade verarbeitet wird
 */
const UploadArea = ({ file, fileName, onFileChange, onProcess, onOpenSettings, processing }) => {
  // Dateiauswahl-Funktion
  const handleFileSelect = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      onFileChange(selectedFile);
    }
  };

  return (
    <>
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
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
        <Button
          variant="outlined"
          startIcon={<SettingsIcon />}
          onClick={onOpenSettings}
        >
          Verarbeitungseinstellungen
        </Button>
        
        <Button
          variant="contained"
          color="primary"
          disabled={!file || processing}
          onClick={onProcess}
        >
          PDF verarbeiten
        </Button>
      </Box>
    </>
  );
};

export default UploadArea;