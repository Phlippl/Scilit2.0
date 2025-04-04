// src/components/pdf/ProcessingSettings.jsx
import React from 'react';
import { 
  Box, 
  Typography, 
  Slider, 
  TextField, 
  FormControlLabel,
  Switch,
  Divider,
  Paper,
  Grid,
  Tooltip,
  IconButton
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

const ProcessingSettings = ({ settings, onChange }) => {
  // Handle slider changes
  const handleSliderChange = (field) => (event, newValue) => {
    onChange({
      ...settings,
      [field]: newValue
    });
  };

  // Handle text input changes
  const handleInputChange = (field) => (event) => {
    const value = event.target.type === 'checkbox' 
      ? event.target.checked 
      : event.target.value === '' ? 0 : Number(event.target.value);
    
    onChange({
      ...settings,
      [field]: value
    });
  };

  // Handle switch changes
  const handleSwitchChange = (field) => (event) => {
    onChange({
      ...settings,
      [field]: event.target.checked
    });
  };

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Page Processing
        </Typography>
        
        <Grid container spacing={2} alignItems="center">
          <Grid item xs>
            <Typography variant="body2">
              Maximum Pages to Process
            </Typography>
          </Grid>
          <Grid item>
            <Tooltip title="Set to 0 to process all pages">
              <IconButton size="small">
                <HelpOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Grid>
          <Grid item xs={12} sm={7}>
            <Slider
              value={settings.maxPages}
              onChange={handleSliderChange('maxPages')}
              step={5}
              marks={[
                { value: 0, label: 'All' },
                { value: 25, label: '25' },
                { value: 50, label: '50' },
                { value: 100, label: '100' }
              ]}
              min={0}
              max={100}
              valueLabelDisplay="auto"
            />
          </Grid>
          <Grid item>
            <TextField
              value={settings.maxPages}
              onChange={handleInputChange('maxPages')}
              inputProps={{
                step: 5,
                min: 0,
                max: 100,
                type: 'number',
                'aria-labelledby': 'max-pages-slider',
              }}
              size="small"
              sx={{ width: 80 }}
            />
          </Grid>
        </Grid>
      </Box>

      <Divider sx={{ my: 2 }} />

      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Text Chunking
          <Tooltip title="Chunking divides text into smaller pieces for more efficient processing and querying">
            <IconButton size="small">
              <HelpOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Typography>
        
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <Typography variant="body2">
              Chunk Size (characters)
            </Typography>
          </Grid>
          <Grid item xs={12} sm={7}>
            <Slider
              value={settings.chunkSize}
              onChange={handleSliderChange('chunkSize')}
              step={100}
              marks={[
                { value: 500, label: '500' },
                { value: 1000, label: '1k' },
                { value: 2000, label: '2k' },
                { value: 4000, label: '4k' }
              ]}
              min={200}
              max={4000}
              valueLabelDisplay="auto"
            />
          </Grid>
          <Grid item>
            <TextField
              value={settings.chunkSize}
              onChange={handleInputChange('chunkSize')}
              inputProps={{
                step: 100,
                min: 200,
                max: 4000,
                type: 'number',
              }}
              size="small"
              sx={{ width: 80 }}
            />
          </Grid>
        </Grid>

        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Small chunks (500-1000) are better for specific queries.
            Larger chunks (2000-4000) provide more context but may be less precise.
          </Typography>
        </Box>

        <Grid container spacing={2} alignItems="center" sx={{ mt: 1 }}>
          <Grid item xs={12} sm={3}>
            <Typography variant="body2">
              Chunk Overlap
            </Typography>
          </Grid>
          <Grid item xs={12} sm={7}>
            <Slider
              value={settings.chunkOverlap}
              onChange={handleSliderChange('chunkOverlap')}
              step={50}
              marks={[
                { value: 0, label: '0' },
                { value: 100, label: '100' },
                { value: 200, label: '200' },
                { value: 400, label: '400' }
              ]}
              min={0}
              max={400}
              valueLabelDisplay="auto"
            />
          </Grid>
          <Grid item>
            <TextField
              value={settings.chunkOverlap}
              onChange={handleInputChange('chunkOverlap')}
              inputProps={{
                step: 50,
                min: 0,
                max: Math.min(400, settings.chunkSize / 2),
                type: 'number',
              }}
              size="small"
              sx={{ width: 80 }}
            />
          </Grid>
        </Grid>

        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Overlap ensures that context isn't lost between chunks.
            Recommended: 10-20% of chunk size.
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ my: 2 }} />

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Advanced Options
        </Typography>
        
        <FormControlLabel
          control={
            <Switch
              checked={settings.performOCR || false}
              onChange={handleSwitchChange('performOCR')}
            />
          }
          label="Perform OCR if needed"
        />
        <Typography variant="body2" color="text.secondary">
          Enables optical character recognition for scanned documents.
          May increase processing time.
        </Typography>
      </Box>
    </Paper>
  );
};

export default ProcessingSettings;