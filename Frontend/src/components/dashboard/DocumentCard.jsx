// src/components/dashboard/DocumentCard.jsx
import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Chip, 
  CardActions, 
  IconButton, 
  Tooltip 
} from '@mui/material';
import { 
  Search as SearchIcon, 
  DeleteOutline as DeleteIcon,
  Article as ArticleIcon
} from '@mui/icons-material';

/**
 * Dokumentkartenkomponente für das Dashboard
 * 
 * @param {Object} props - Komponentenprops
 * @param {Object} props.document - Dokumentdaten
 * @param {Function} props.onDelete - Callback für Löschaktion
 * @param {Function} props.onView - Callback für Ansichtsaktion
 * @param {Function} [props.onClick] - Optionaler Callback für Klick auf die gesamte Karte
 */
const DocumentCard = ({ document, onDelete, onView, onClick }) => {
  // Verhindere Event-Bubbling
  const handleActionClick = (e, action) => {
    e.stopPropagation();
    action();
  };
  
  // Formatiere das Datum
  const formatDate = (dateString) => {
    if (!dateString) return '';
    
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('de-DE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      }).format(date);
    } catch (error) {
      return dateString;
    }
  };
  
  return (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': onClick ? {
          boxShadow: 6
        } : {}
      }}
      onClick={onClick}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Chip 
            label={document.type === 'book' ? 'Buch' : 'Artikel'} 
            size="small" 
            color={document.type === 'book' ? 'secondary' : 'primary'}
            sx={{ mb: 1 }}
          />
          <Typography variant="caption" color="text.secondary">
            {formatDate(document.uploadDate)}
          </Typography>
        </Box>
        
        <Typography variant="h6" component="h3" gutterBottom>
          {document.title}
        </Typography>
        
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {document.authors && 
           Array.isArray(document.authors) ? 
           document.authors.map(a => typeof a === 'string' ? a : a.name).join(', ') : 
           document.authors}
        </Typography>
        
        <Typography variant="body2" sx={{ mt: 1 }}>
          {document.publisher || document.journal || ''}
        </Typography>
        
        <Typography variant="body2" color="text.secondary">
          {formatDate(document.publicationDate)}
        </Typography>
      </CardContent>
      <CardActions sx={{ justifyContent: 'flex-end', p: 1 }}>
        <Tooltip title="Dieses Dokument abfragen">
          <IconButton 
            size="small" 
            color="primary"
            onClick={(e) => handleActionClick(e, onView)}
          >
            <SearchIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Dokument löschen">
          <IconButton 
            size="small" 
            color="error"
            onClick={(e) => handleActionClick(e, onDelete)}
          >
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      </CardActions>
    </Card>
  );
};

export default DocumentCard;