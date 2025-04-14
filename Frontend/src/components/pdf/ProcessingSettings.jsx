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
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
  alpha
} from '@mui/material';

// Icons
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TuneIcon from '@mui/icons-material/Tune';
import SplitscreenIcon from '@mui/icons-material/Splitscreen';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SettingsApplicationsIcon from '@mui/icons-material/SettingsApplications';
import SpeedIcon from '@mui/icons-material/Speed';

/**
 * Enhanced document processing settings component
 * 
 * @param {Object} props - Component props
 * @param {Object} props.settings - Current settings values
 * @param {Function} props.onChange - Callback when settings change
 */
const ProcessingSettings = ({ settings, onChange }) => {
  const theme = useTheme();
  
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
    <Paper variant="outlined" sx={{ p: 0 }}>
      {/* Main settings */}
      <Box sx={{ p: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Dokumentverarbeitung
        </Typography>
        
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12}>
            <Box sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
              <SpeedIcon sx={{ fontSize: 20, mr: 1, color: 'primary.main' }}/>
              <Typography variant="subtitle2">
                Maximale Seitenzahl zur Verarbeitung
              </Typography>
              <Tooltip title="Stellen Sie auf 0, um alle Seiten zu verarbeiten. Bei größeren Dokumenten kann die Begrenzung der Seitenzahl die Verarbeitung beschleunigen.">
                <IconButton size="small">
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            
            <Box sx={{ px: 1 }}>
              <Slider
                value={settings.maxPages}
                onChange={handleSliderChange('maxPages')}
                step={5}
                marks={[
                  { value: 0, label: 'Alle' },
                  { value: 25, label: '25' },
                  { value: 50, label: '50' },
                  { value: 100, label: '100' }
                ]}
                min={0}
                max={100}
                valueLabelDisplay="auto"
                sx={{ 
                  '& .MuiSlider-markLabel': {
                    fontSize: '0.75rem'
                  }
                }}
              />
            </Box>
            
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1, color: 'text.secondary' }}>
              <Typography variant="caption">
                {settings.maxPages === 0 
                  ? 'Alle Seiten verarbeiten (kann länger dauern)'
                  : `Die ersten ${settings.maxPages} Seiten verarbeiten`}
              </Typography>
              
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
                sx={{ width: 60 }}
              />
            </Box>
          </Grid>
          
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.performOCR || false}
                  onChange={handleSwitchChange('performOCR')}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <AutoAwesomeIcon sx={{ fontSize: 20, mr: 1, color: settings.performOCR ? 'primary.main' : 'text.disabled' }}/>
                  <Typography variant="subtitle2">
                    OCR bei Bedarf durchführen
                  </Typography>
                  <Tooltip title="Aktiviert die optische Zeichenerkennung für gescannte Dokumente. Dies kann die Verarbeitungszeit erhöhen.">
                    <IconButton size="small">
                      <HelpOutlineIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              }
            />
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', ml: 9 }}>
              {settings.performOCR 
                ? 'OCR wird für Seiten mit wenig oder keinem Text durchgeführt (langsamer)' 
                : 'OCR ist deaktiviert (schneller, jedoch möglicherweise weniger Text aus gescannten Dokumenten)'}
            </Typography>
          </Grid>
        </Grid>
      </Box>
      
      {/* Advanced settings (in accordion) */}
      <Accordion 
        disableGutters 
        elevation={0}
        sx={{
          '&:before': { display: 'none' },
          borderTop: `1px solid ${theme.palette.divider}`
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{ 
            backgroundColor: alpha(theme.palette.primary.main, 0.03),
            '&:hover': {
              backgroundColor: alpha(theme.palette.primary.main, 0.05),
            }
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <SettingsApplicationsIcon sx={{ mr: 1, fontSize: 20, color: 'primary.main' }} />
            <Typography variant="subtitle2">Erweiterte Einstellungen für die Textverarbeitung</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 2, pt: 3 }}>
          <Box sx={{ mb: 3 }}>
            <Box sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
              <SplitscreenIcon sx={{ fontSize: 20, mr: 1, color: 'primary.main' }}/>
              <Typography variant="subtitle2">
                Text-Chunking
              </Typography>
              <Tooltip title="Chunking teilt den Text in kleinere Stücke für eine effizientere Verarbeitung und Abfrage">
                <IconButton size="small">
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
            
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={4}>
                <Typography variant="body2">
                  Chunk-Größe (Zeichen)
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
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
              <Grid item xs={12} sm={2}>
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
                  sx={{ width: '100%' }}
                />
              </Grid>
            </Grid>

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, mb: 2 }}>
              Kleine Chunks (500-1000) sind besser für spezifische Abfragen.
              Größere Chunks (2000-4000) bieten mehr Kontext, können aber weniger präzise sein.
            </Typography>

            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={4}>
                <Typography variant="body2">
                  Chunk-Überlappung
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
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
              <Grid item xs={12} sm={2}>
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
                  sx={{ width: '100%' }}
                />
              </Grid>
            </Grid>

            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              Überlappung stellt sicher, dass Kontext zwischen Chunks nicht verloren geht.
              Empfohlen: 10-20% der Chunk-Größe.
            </Typography>
          </Box>
          
          <Box sx={{ 
            p: 2, 
            borderRadius: 1, 
            bgcolor: theme.palette.mode === 'dark' 
              ? alpha(theme.palette.info.main, 0.1) 
              : alpha(theme.palette.info.main, 0.05),
            border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`
          }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Empfehlungen:</strong> Für optimale Ergebnisse bei der Verarbeitung großer wissenschaftlicher Dokumente 
              empfehlen wir eine Chunk-Größe von 1000-1500 Zeichen mit einer Überlappung von 150-200 Zeichen. 
              Dies bietet eine gute Balance zwischen Kontext und Präzision.
            </Typography>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Paper>
  );
};

export default ProcessingSettings;