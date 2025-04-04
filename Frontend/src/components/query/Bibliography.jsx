// src/components/query/Bibliography.jsx
import React from 'react';
import {
  Box,
  Typography,
  Tooltip,
  IconButton,
  Paper,
  Divider
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

/**
 * Komponente zur Anzeige des Literaturverzeichnisses
 * 
 * @param {Object} props - Komponenten-Props
 * @param {Array} props.citations - Array von Literaturangaben
 * @param {string} [props.title] - Optional: Titel des Literaturverzeichnisses
 * @param {Function} [props.onCopyCitation] - Optional: Callback zum Kopieren einer Literaturangabe
 * @param {Function} [props.onCopyAll] - Optional: Callback zum Kopieren aller Literaturangaben
 */
const Bibliography = ({ 
  citations, 
  title = 'Literaturverzeichnis', 
  onCopyCitation,
  onCopyAll
}) => {
  
  /**
   * Einzelne Literaturangabe in die Zwischenablage kopieren
   */
  const copyCitation = (citation) => {
    if (onCopyCitation) {
      onCopyCitation(citation);
    } else {
      try {
        navigator.clipboard.writeText(citation);
      } catch (error) {
        console.error('Fehler beim Kopieren in die Zwischenablage:', error);
      }
    }
  };
  
  /**
   * Alle Literaturangaben in die Zwischenablage kopieren
   */
  const copyAllCitations = () => {
    if (onCopyAll) {
      onCopyAll(citations);
    } else {
      try {
        const allCitations = citations.join('\n\n');
        navigator.clipboard.writeText(allCitations);
      } catch (error) {
        console.error('Fehler beim Kopieren in die Zwischenablage:', error);
      }
    }
  };
  
  if (!citations || citations.length === 0) {
    return null;
  }
  
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          {title}
        </Typography>
        
        <Tooltip title="Alle Literaturangaben kopieren">
          <IconButton onClick={copyAllCitations}>
            <ContentCopyIcon />
          </IconButton>
        </Tooltip>
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      <Box component="ol" sx={{ pl: 2, m: 0 }}>
        {citations.map((citation, index) => (
          <Box
            key={index}
            component="li"
            sx={{
              mb: 2,
              pb: 1,
              borderBottom: index < citations.length - 1 ? '1px dashed #e0e0e0' : 'none',
              position: 'relative',
              pl: 0,
              ml: 3,
              '&:hover .copyButton': {
                opacity: 1,
              }
            }}
          >
            <Typography 
              variant="body2"
              sx={{ 
                textIndent: '-1.5em', 
                paddingLeft: '1.5em',
              }}
            >
              {citation}
            </Typography>
            
            <Tooltip title="Kopieren">
              <IconButton 
                size="small" 
                onClick={() => copyCitation(citation)}
                className="copyButton"
                sx={{ 
                  position: 'absolute', 
                  right: 0, 
                  top: 0,
                  opacity: 0,
                  transition: 'opacity 0.2s',
                }}
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ))}
      </Box>
    </Paper>
  );
};

export default Bibliography;