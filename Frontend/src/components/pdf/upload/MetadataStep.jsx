// src/components/pdf/upload/MetadataStep.jsx
import React from 'react';
import { Box, Button } from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';

// Import existing components
import MetadataForm from '../MetadataForm';
import PDFViewer from '../PDFViewer';

/**
 * Komponente für den Metadaten-Bearbeitungsschritt beim PDF-Upload
 * 
 * @param {Object} props - Komponenten-Properties
 * @param {Object} props.metadata - Metadaten des Dokuments
 * @param {File} props.file - Die PDF-Datei
 * @param {Function} props.onMetadataChange - Callback für Metadaten-Änderungen
 * @param {Function} props.onSave - Callback zum Speichern
 * @param {boolean} props.processing - Flag für laufende Verarbeitung
 */
const MetadataStep = ({ metadata, file, onMetadataChange, onSave, processing }) => {
  return (
    <Box sx={{ display: 'flex', gap: 4, flexDirection: { xs: 'column', md: 'row' } }}>
      {/* Metadata on left */}
      <Box sx={{ width: { xs: '100%', md: '55%' } }}>
        {metadata && (
          <MetadataForm
            metadata={metadata}
            onChange={onMetadataChange}
          />
        )}

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<SaveIcon />}
            onClick={onSave}
            disabled={processing || !metadata?.title}
          >
            In Datenbank speichern
          </Button>
        </Box>
      </Box>

      {/* PDF on right */}
      <Box sx={{ width: { xs: '100%', md: '45%' } }}>
        {file && <PDFViewer file={file} height="750px" />}
      </Box>
    </Box>
  );
};

export default MetadataStep;