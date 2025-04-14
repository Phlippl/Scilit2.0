// src/components/dashboard/DocumentCard.jsx
import React from 'react';
import { 
  Card, 
  CardContent,
  CardMedia, 
  Typography, 
  Box, 
  Chip, 
  CardActions, 
  IconButton, 
  Tooltip,
  Divider,
  alpha
} from '@mui/material';
import { 
  Search as SearchIcon, 
  DeleteOutline as DeleteIcon,
  OpenInNew as OpenInNewIcon,
  Download as DownloadIcon,
  LibraryBooks as LibraryBooksIcon,
  InsertDriveFile as InsertDriveFileIcon,
  MenuBook as MenuBookIcon,
  Article as ArticleIcon
} from '@mui/icons-material';

/**
 * Enhanced document card component for the dashboard
 * 
 * @param {Object} props - Component props
 * @param {Object} props.document - Document data
 * @param {Function} props.onDelete - Callback for delete action
 * @param {Function} props.onView - Callback for query/view action
 * @param {Function} props.onDownload - Callback for download action (optional)
 * @param {Function} props.onClick - Optional callback for click on the card
 */
const DocumentCard = ({ document, onDelete, onView, onDownload, onClick }) => {
  // Prevent event bubbling
  const handleActionClick = (e, action) => {
    e.stopPropagation();
    action();
  };
  
  // Format a date string
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
  
  // Get document type icon
  const getDocTypeIcon = () => {
    switch(document.type) {
      case 'book':
        return <MenuBookIcon fontSize="small" />;
      case 'article':
        return <ArticleIcon fontSize="small" />;
      case 'conference':
        return <LibraryBooksIcon fontSize="small" />;
      default:
        return <InsertDriveFileIcon fontSize="small" />;
    }
  };
  
  // Get formatted document type label
  const getDocTypeLabel = () => {
    switch(document.type) {
      case 'book':
        return 'Buch';
      case 'article':
        return 'Artikel';
      case 'conference':
        return 'Konferenz';
      case 'thesis':
        return 'Hochschulschrift';
      case 'edited_book':
        return 'Sammelwerk';
      case 'report':
        return 'Bericht';
      case 'website':
        return 'Webseite';
      default:
        return document.type || 'Dokument';
    }
  };
  
  // Format authors list for display
  const formatAuthors = () => {
    if (!document.authors) return '';
    
    let authorsList = [];
    if (Array.isArray(document.authors)) {
      authorsList = document.authors.map(a => 
        typeof a === 'string' ? a : (a.name || '')
      );
    } else if (typeof document.authors === 'string') {
      authorsList = [document.authors];
    }
    
    if (authorsList.length === 0) return '';
    if (authorsList.length === 1) return authorsList[0];
    if (authorsList.length === 2) return `${authorsList[0]} & ${authorsList[1]}`;
    return `${authorsList[0]} et al.`;
  };
  
  // Get document identifier (DOI or ISBN)
  const getIdentifier = () => {
    if (document.doi) return `DOI: ${document.doi}`;
    if (document.isbn) return `ISBN: ${document.isbn}`;
    return null;
  };
  
  // Get document source (journal or publisher)
  const getSourceInfo = () => {
    if (document.journal) {
      let info = document.journal;
      if (document.volume) {
        info += `, ${document.volume}`;
        if (document.issue) info += `(${document.issue})`;
      }
      if (document.pages) info += `, ${document.pages}`;
      return info;
    }
    
    if (document.publisher) return document.publisher;
    return null;
  };
  
  // Get color for document type
  const getTypeColor = () => {
    switch(document.type) {
      case 'book':
        return 'secondary';
      case 'article':
        return 'primary';
      case 'conference':
        return 'success';
      case 'thesis':
        return 'info';
      default:
        return 'default';
    }
  };
  
  return (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease-in-out',
        '&:hover': onClick ? {
          boxShadow: 6,
          transform: 'translateY(-4px)'
        } : {},
        position: 'relative',
        overflow: 'visible'
      }}
      onClick={onClick}
    >
      {/* Document Type Badge */}
      <Box 
        sx={{ 
          position: 'absolute', 
          top: -12, 
          left: 16, 
          zIndex: 10 
        }}
      >
        <Chip 
          icon={getDocTypeIcon()}
          label={getDocTypeLabel()} 
          size="small" 
          color={getTypeColor()}
          sx={{ boxShadow: 1 }}
        />
      </Box>
      
      {/* Media Section - could be a PDF preview */}
      <CardMedia
        sx={{
          height: 48,
          backgroundColor: theme => alpha(theme.palette[getTypeColor()].main, 0.1),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          px: 2
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {formatDate(document.uploadDate)}
        </Typography>
      </CardMedia>
      
      <CardContent sx={{ flexGrow: 1, pt: 1.5 }}>
        <Typography variant="h6" component="h3" gutterBottom noWrap title={document.title}>
          {document.title}
        </Typography>
        
        <Typography variant="body2" gutterBottom noWrap>
          {formatAuthors()}
        </Typography>
        
        {getSourceInfo() && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }} noWrap>
            {getSourceInfo()}
          </Typography>
        )}
        
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, mb: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            {formatDate(document.publicationDate)}
          </Typography>
          
          {getIdentifier() && (
            <>
              <Box 
                component="span" 
                sx={{ 
                  display: 'inline-block', 
                  mx: 0.75, 
                  width: 4, 
                  height: 4, 
                  borderRadius: '50%', 
                  bgcolor: 'text.disabled' 
                }}
              />
              <Tooltip title={getIdentifier()}>
                <Typography 
                  variant="body2" 
                  color="text.secondary" 
                  sx={{ 
                    maxWidth: 140, 
                    overflow: 'hidden', 
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap' 
                  }}
                >
                  {getIdentifier()}
                </Typography>
              </Tooltip>
            </>
          )}
        </Box>
        
        {document.chunks && (
          <Box 
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              mt: 1 
            }}
          >
            <Chip
              size="small"
              variant="outlined"
              label={`${document.num_chunks || (Array.isArray(document.chunks) ? document.chunks.length : 0)} Chunks`}
              sx={{ height: 20, fontSize: '0.7rem' }}
            />
            
            {document.totalPages && (
              <Chip
                size="small"
                variant="outlined"
                label={`${document.processedPages || document.totalPages} Seiten`}
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            )}
          </Box>
        )}
      </CardContent>
      
      <Divider />
      
      <CardActions sx={{ justifyContent: 'space-between', p: 1 }}>
        <Tooltip title="Dieses Dokument abfragen">
          <IconButton 
            size="small" 
            color="primary"
            onClick={(e) => handleActionClick(e, onView)}
          >
            <SearchIcon />
          </IconButton>
        </Tooltip>
        
        {onDownload && (
          <Tooltip title="PDF herunterladen">
            <IconButton 
              size="small" 
              color="default"
              onClick={(e) => handleActionClick(e, onDownload)}
            >
              <DownloadIcon />
            </IconButton>
          </Tooltip>
        )}
        
        <Tooltip title="In neuem Tab öffnen">
          <IconButton 
            size="small" 
            color="default"
            onClick={(e) => {
              e.stopPropagation();
              // Open document in a new tab - assuming there's a route for direct document view
              window.open(`/document/${document.id}`, '_blank');
            }}
          >
            <OpenInNewIcon />
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