// src/components/query/Results.jsx
import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Divider,
  Chip,
  Tooltip,
  IconButton
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

/**
 * Komponente zur Anzeige der Abfrageergebnisse
 * 
 * @param {Object} props - Komponenten-Props
 * @param {Array} props.results - Array der Ergebnisse mit Text und Quelle
 * @param {Function} [props.onCopyResult] - Optional: Callback zum Kopieren eines einzelnen Ergebnisses
 */
const Results = ({ results, onCopyResult }) => {
  
  /**
   * Einzelnes Ergebnis in die Zwischenablage kopieren
   */
  const copyToClipboard = (text, source) => {
    if (onCopyResult) {
      onCopyResult(text, source);
    } else {
      try {
        const content = `${text}\n(${source})`;
        navigator.clipboard.writeText(content);
      } catch (error) {
        console.error('Fehler beim Kopieren in die Zwischenablage:', error);
      }
    }
  };
  
  /**
   * Extrahiert Seitenzahlen aus der Quellenangabe, falls vorhanden
   */
  const extractPageInfo = (source) => {
    const pageMatch = source.match(/\(([^)]+), S\. (\d+(?:-\d+)?)\)/);
    if (pageMatch && pageMatch[2]) {
      return {
        citation: pageMatch[1],
        pages: pageMatch[2]
      };
    }
    return {
      citation: source,
      pages: null
    };
  };
  
  if (!results || results.length === 0) {
    return (
      <Box sx={{ py: 2, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Keine Ergebnisse gefunden
        </Typography>
      </Box>
    );
  }
  
  return (
    <Box>
      {results.map((result, index) => {
        const { citation, pages } = extractPageInfo(result.source);
        
        return (
          <Card key={index} sx={{ mb: 2, backgroundColor: '#f9f9f9' }}>
            <CardContent>
              <Typography variant="body1" paragraph>
                {result.text}
              </Typography>
              
              <Box sx={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                borderTop: '1px solid #e0e0e0',
                pt: 1,
                mt: 1
              }}>
                <Typography variant="body2" color="text.secondary">
                  {citation}
                  {pages && (
                    <Chip 
                      label={`S. ${pages}`} 
                      size="small" 
                      variant="outlined" 
                      sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
                    />
                  )}
                </Typography>
                
                <Tooltip title="Kopieren">
                  <IconButton 
                    size="small" 
                    onClick={() => copyToClipboard(result.text, result.source)}
                  >
                    <ContentCopyIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            </CardContent>
          </Card>
        );
      })}
    </Box>
  );
};

export default Results;