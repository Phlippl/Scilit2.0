// src/components/query/QuerySettings.jsx
import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Switch,
  FormControlLabel,
  Divider,
  IconButton,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
  Slider,
  Grid
} from '@mui/material';

// Icons
import CloseIcon from '@mui/icons-material/Close';
import FormatQuoteIcon from '@mui/icons-material/FormatQuote';
import TextFormatIcon from '@mui/icons-material/TextFormat';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import NumbersIcon from '@mui/icons-material/Numbers';

/**
 * Query settings component for controlling query behavior
 * 
 * @param {Object} props - Component props
 * @param {Object} props.settings - Current settings values
 * @param {Function} props.onChange - Callback when settings change
 * @param {Function} props.onClose - Callback when settings panel is closed
 */
const QuerySettings = ({ settings, onChange, onClose }) => {
  // Handle direct quote toggle
  const handleDirectQuotesChange = (event) => {
    onChange('useDirectQuotes', event.target.checked);
  };
  
  // Handle page numbers toggle
  const handlePageNumbersChange = (event) => {
    onChange('includePageNumbers', event.target.checked);
  };
  
  // Handle results count change
  const handleMaxResultsChange = (event, value) => {
    onChange('maxResults', value);
  };
  
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle1">
          Abfrageeinstellungen
        </Typography>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>
      
      <Grid container spacing={3}>
        {/* Direct quotes setting */}
        <Grid item xs={12} sm={6}>
          <Box sx={{ display: 'flex', flexDirection: 'column', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <FormatQuoteIcon sx={{ mr: 1, color: 'primary.main' }} fontSize="small" />
              <Typography variant="subtitle2">Zitatart</Typography>
              <Tooltip title="Bei direkten Zitaten werden exakte Textpassagen übernommen. Bei indirekten Zitaten wird der Inhalt paraphrasiert.">
                <HelpOutlineIcon sx={{ ml: 1, color: 'action.active' }} fontSize="small" />
              </Tooltip>
            </Box>
            
            <ToggleButtonGroup
              value={settings.useDirectQuotes ? 'direct' : 'indirect'}
              exclusive
              onChange={(e, newValue) => {
                // Prevent deselection
                if (newValue !== null) {
                  onChange('useDirectQuotes', newValue === 'direct');
                }
              }}
              aria-label="Zitatart"
              size="small"
              fullWidth
            >
              <ToggleButton value="direct" aria-label="direkte Zitate">
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <FormatQuoteIcon fontSize="small" />
                  <Typography variant="caption">Direkte</Typography>
                </Box>
              </ToggleButton>
              <ToggleButton value="indirect" aria-label="indirekte Zitate">
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <TextFormatIcon fontSize="small" />
                  <Typography variant="caption">Indirekte</Typography>
                </Box>
              </ToggleButton>
            </ToggleButtonGroup>
            
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {settings.useDirectQuotes 
                ? "Exakte Textpassagen werden zitiert" 
                : "Inhalte werden paraphrasiert"}
            </Typography>
          </Box>
        </Grid>
        
        {/* Page numbers setting */}
        <Grid item xs={12} sm={6}>
          <Box sx={{ display: 'flex', flexDirection: 'column', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <NumbersIcon sx={{ mr: 1, color: 'primary.main' }} fontSize="small" />
              <Typography variant="subtitle2">Seitenzahlen</Typography>
              <Tooltip title="Gibt an, ob Seitenzahlen in den Zitaten angezeigt werden sollen">
                <HelpOutlineIcon sx={{ ml: 1, color: 'action.active' }} fontSize="small" />
              </Tooltip>
            </Box>
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.includePageNumbers}
                  onChange={handlePageNumbersChange}
                  color="primary"
                />
              }
              label={settings.includePageNumbers ? "Seitenzahlen anzeigen" : "Ohne Seitenzahlen"}
            />
            
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {settings.includePageNumbers 
                ? "Quellenangaben enthalten Seitenzahlen" 
                : "Quellenangaben ohne Seitenzahlen"}
            </Typography>
          </Box>
        </Grid>
      </Grid>
      
      <Divider sx={{ my: 2 }} />
      
      {/* Results count setting */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2">Anzahl der Ergebnisse</Typography>
          <Tooltip title="Legt fest, wie viele Ergebnisse maximal zurückgegeben werden">
            <HelpOutlineIcon sx={{ ml: 1, color: 'action.active' }} fontSize="small" />
          </Tooltip>
        </Box>
        
        <Box sx={{ px: 2 }}>
          <Slider
            value={settings.maxResults}
            onChange={handleMaxResultsChange}
            step={1}
            marks={[
              { value: 3, label: '3' },
              { value: 5, label: '5' },
              { value: 7, label: '7' },
              { value: 10, label: '10' }
            ]}
            min={1}
            max={10}
            valueLabelDisplay="auto"
          />
        </Box>
        
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Mehr Ergebnisse geben einen breiteren Überblick, können aber weniger präzise sein
        </Typography>
      </Box>
      
      <Divider sx={{ my: 2 }} />
      
      <Typography variant="caption" color="text.secondary">
        Diese Einstellungen beeinflussen, wie die Abfrage durchgeführt wird und wie Ergebnisse präsentiert werden.
      </Typography>
    </Paper>
  );
};

export default QuerySettings;