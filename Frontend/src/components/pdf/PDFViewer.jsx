// src/components/pdf/PDFViewer.jsx
// Diese Komponente wird für die Anzeige von PDF-Dateien während des Upload-Prozesses verwendet
import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { 
  Box, 
  Typography, 
  IconButton, 
  Paper, 
  CircularProgress,
  Pagination,
  Tooltip
} from '@mui/material';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import RotateLeftIcon from '@mui/icons-material/RotateLeft';
import RotateRightIcon from '@mui/icons-material/RotateRight';
import FullscreenIcon from '@mui/icons-material/Fullscreen';

// Set up PDF.js worker source (required for react-pdf)
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

/**
 * PDF Viewer component
 * 
 * @param {Object} props - Component props
 * @param {File|string} props.file - PDF file to display (File object or URL)
 * @param {number} props.initialPage - Initial page to display (1-based)
 * @param {string} props.height - Height of PDF container
 */
const PDFViewer = ({ file, initialPage = 1, height = '700px' }) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(initialPage);
  const [loading, setLoading] = useState(true);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [error, setError] = useState(null);

  /**
   * Handle successful document loading
   */
  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  /**
   * Handle document loading error
   */
  const onDocumentLoadError = (error) => {
    console.error('Error loading PDF:', error);
    setError('PDF konnte nicht geladen werden');
    setLoading(false);
  };

  /**
   * Change page number
   */
  const handlePageChange = (event, value) => {
    setPageNumber(value);
  };

  /**
   * Zoom in/out
   */
  const handleZoom = (delta) => {
    setScale(prevScale => {
      const newScale = prevScale + delta;
      // Limit scale between 0.5 and 2.5
      return Math.max(0.5, Math.min(2.5, newScale));
    });
  };

  /**
   * Rotate document
   */
  const handleRotate = (delta) => {
    setRotation(prevRotation => (prevRotation + delta) % 360);
  };

  /**
   * Open document in full screen
   */
  const handleFullScreen = () => {
    if (file instanceof File) {
      // Create blob URL for local file
      const url = URL.createObjectURL(file);
      window.open(url, '_blank');
    } else if (typeof file === 'string') {
      // Open URL directly
      window.open(file, '_blank');
    }
  };

  return (
    <Paper 
      elevation={2} 
      sx={{ 
        height, 
        overflow: 'hidden', 
        display: 'flex', 
        flexDirection: 'column',
        position: 'relative'
      }}
    >
      {/* PDF Controls */}
      <Box 
        sx={{ 
          p: 1, 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          borderBottom: '1px solid #e0e0e0',
        }}
      >
        <Typography variant="body2">
          {numPages ? `Seite ${pageNumber} von ${numPages}` : ''}
        </Typography>
        
        <Box>
          <Tooltip title="Verkleinern">
            <IconButton size="small" onClick={() => handleZoom(-0.1)}>
              <ZoomOutIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Vergrößern">
            <IconButton size="small" onClick={() => handleZoom(0.1)}>
              <ZoomInIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Nach links drehen">
            <IconButton size="small" onClick={() => handleRotate(-90)}>
              <RotateLeftIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Nach rechts drehen">
            <IconButton size="small" onClick={() => handleRotate(90)}>
              <RotateRightIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="In neuem Tab öffnen">
            <IconButton size="small" onClick={handleFullScreen}>
              <FullscreenIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      
      {/* PDF Document */}
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'flex-start',
        p: 2,
        bgcolor: '#f5f5f5'
      }}>
        {loading && (
          <Box sx={{ 
            position: 'absolute', 
            top: '50%', 
            left: '50%', 
            transform: 'translate(-50%, -50%)'
          }}>
            <CircularProgress />
          </Box>
        )}
        
        {error ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography color="error">{error}</Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Versuche, das PDF in einem externen Programm zu öffnen.
            </Typography>
          </Box>
        ) : (
          <Document
            file={file}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={null} // We handle loading ourselves
          >
            <Page 
              pageNumber={pageNumber} 
              scale={scale}
              rotate={rotation}
              renderTextLayer={false}
              renderAnnotationLayer={false}
            />
          </Document>
        )}
      </Box>
      
      {/* Pagination */}
      {numPages && numPages > 1 && (
        <Box sx={{ 
          p: 1, 
          display: 'flex', 
          justifyContent: 'center',
          borderTop: '1px solid #e0e0e0'
        }}>
          <Pagination 
            count={numPages} 
            page={pageNumber} 
            onChange={handlePageChange} 
            size="small"
            siblingCount={1}
            boundaryCount={1}
          />
        </Box>
      )}
    </Paper>
  );
};

export default PDFViewer;