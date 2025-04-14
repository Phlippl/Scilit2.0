// src/components/pdf/upload/ProcessingStep.jsx
import React from 'react';
import { Box, Typography, LinearProgress, Alert } from '@mui/material';
import ArticleIcon from '@mui/icons-material/Article';

/**
 * Komponente für den Verarbeitungsschritt beim PDF-Upload
 * 
 * @param {Object} props - Komponenten-Properties
 * @param {string} props.fileName - Name der Datei, die verarbeitet wird
 * @param {string} props.processingStage - Aktuelle Verarbeitungsphase
 * @param {number} props.processingProgress - Aktueller Fortschritt (0-100)
 * @param {Object} props.extractedIdentifiers - Extrahierte Identifikatoren (doi, isbn)
 * @param {Array} props.chunks - Extrahierte Textchunks
 */
const ProcessingStep = ({ 
  fileName, 
  processingStage, 
  processingProgress, 
  extractedIdentifiers, 
  chunks 
}) => {
  return (
    <>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <ArticleIcon sx={{ fontSize: 40, color: 'primary.main', mr: 2 }} />
        <Typography variant="h6">{fileName}</Typography>
      </Box>
      
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
    </>
  );
};

export default ProcessingStep;