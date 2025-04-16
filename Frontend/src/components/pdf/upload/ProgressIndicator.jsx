import React from 'react';
import { Box, LinearProgress, Typography, Paper } from '@mui/material';

const ProgressIndicator = ({ progress, message, estimated }) => {
  return (
    <Paper sx={{ p: 3, width: '100%' }}>
      <Typography variant="h6" gutterBottom>
        Verarbeitung läuft...
      </Typography>
      
      <Typography variant="body2" color="text.secondary" gutterBottom>
        {message}
      </Typography>
      
      <LinearProgress 
        variant="determinate" 
        value={progress} 
        sx={{ height: 10, borderRadius: 5, my: 2 }}
      />
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography variant="body2" color="text.secondary">
          {progress}% abgeschlossen
        </Typography>
        {estimated && (
          <Typography variant="body2" color="text.secondary">
            Geschätzte Zeit: {estimated}
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

export default ProgressIndicator;