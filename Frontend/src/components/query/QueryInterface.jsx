// src/components/query/QueryInterface.jsx
import React, { useState, useEffect } from 'react';
import { 
  Paper, 
  Typography, 
  TextField, 
  Button, 
  Box, 
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  Card,
  CardContent,
  IconButton,
  Chip,
  Tooltip,
  Alert,
  FormControlLabel,
  Switch,
  Grid,
  ButtonGroup,
  useTheme,
  Checkbox
} from '@mui/material';

// Icons
import SearchIcon from '@mui/icons-material/Search';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import FilterListIcon from '@mui/icons-material/FilterList';

// Komponenten
import FilterPanel from './FilterPanel';
import Bibliography from './Bibliography';
import Results from './Results';

// Services und APIs
import * as queryApi from '../../api/query';
import * as documentsApi from '../../api/documents';

// Hooks
import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

const QueryInterface = () => {
  const theme = useTheme();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // Query-State
  const [query, setQuery] = useState('');
  const [documentFilters, setDocumentFilters] = useState([]);
  const [citationStyle, setCitationStyle] = useState('apa');
  const [availableStyles, setAvailableStyles] = useState([
    { id: 'apa', name: 'APA 7th Edition' },
    { id: 'chicago', name: 'Chicago 18th Edition' },
    { id: 'harvard', name: 'Harvard' }
  ]);
  
  // Ergebnis-State
  const [results, setResults] = useState([]);
  const [bibliography, setBibliography] = useState([]);
  
  // UI-State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [querySettings, setQuerySettings] = useState({
    useDirectQuotes: true,
    maxResults: 5,
    includePageNumbers: true
  });
  const [lastQueryTime, setLastQueryTime] = useState(null);
  
  // Verfügbare Dokumente und Zitationsstile beim Laden der Komponente abrufen
  useEffect(() => {
    // Authentifizierung prüfen
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/query' } });
      return;
    }
    
    // Verfügbare Dokumente abrufen
    const fetchDocuments = async () => {
      try {
        const docs = await documentsApi.getDocuments();
        setAvailableDocuments(docs);
      } catch (error) {
        console.error('Fehler beim Abrufen der Dokumente:', error);
        setError('Dokumente konnten nicht geladen werden. Bitte versuche es später erneut.');
      }
    };
    
    // Verfügbare Zitationsstile abrufen
    const fetchCitationStyles = async () => {
      try {
        const styles = await queryApi.getSupportedCitationStyles();
        if (styles && styles.length > 0) {
          setAvailableStyles(styles);
        }
      } catch (error) {
        console.error('Fehler beim Abrufen der Zitationsstile:', error);
        // Standardstile beibehalten
      }
    };
    
    fetchDocuments();
    fetchCitationStyles();
  }, [isAuthenticated, navigate]);
  
  /**
   * Änderungen der Abfrageeinstellungen behandeln
   */
  const handleSettingsChange = (setting, value) => {
    setQuerySettings({
      ...querySettings,
      [setting]: value
    });
  };
  
  /**
   * Änderungen der Dokumentfilter behandeln
   */
  const handleDocumentFilterChange = (selectedDocuments) => {
    setDocumentFilters(selectedDocuments);
  };
  
  /**
   * Ergebnisse in die Zwischenablage kopieren
   */
  const copyResultsToClipboard = () => {
    try {
      // Ergebnisse und Bibliographie als Text formatieren
      const resultsText = results
        .map(result => `${result.text}\n(${result.source})`)
        .join('\n\n');
      
      const bibText = bibliography.length > 0 
        ? '\n\nLiteraturverzeichnis\n' + bibliography.join('\n')
        : '';
      
      const fullText = resultsText + bibText;
      
      // In die Zwischenablage kopieren
      navigator.clipboard.writeText(fullText);
      
      // Erfolgsmeldung könnte hier hinzugefügt werden
    } catch (error) {
      console.error('Fehler beim Kopieren in die Zwischenablage:', error);
      setError('Ergebnisse konnten nicht in die Zwischenablage kopiert werden');
    }
  };
  
  /**
   * Abfrage und Ergebnisse speichern
   */
  const saveQueryResults = async () => {
    try {
      // Dies würde die Abfrage und Ergebnisse im Backend speichern
      // In diesem Beispiel nicht implementiert
      console.log('Speichere Abfrageergebnisse:', {
        query,
        results,
        bibliography,
        timestamp: new Date().toISOString()
      });
      
      // Erfolgsmeldung anzeigen
    } catch (error) {
      console.error('Fehler beim Speichern der Abfrage:', error);
      setError('Abfrageergebnisse konnten nicht gespeichert werden');
    }
  };
  
  /**
   * Abfrageübermittlung behandeln
   */
  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Bitte gib eine Abfrage ein');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults([]);
    setBibliography([]);
    
    try {
      const startTime = performance.now();
      
      const response = await queryApi.queryDocuments({
        query: query.trim(),
        citation_style: citationStyle,
        document_ids: documentFilters.length > 0 ? documentFilters : undefined,
        n_results: querySettings.maxResults,
        use_direct_quotes: querySettings.useDirectQuotes,
        include_page_numbers: querySettings.includePageNumbers
      });
      
      const endTime = performance.now();
      setLastQueryTime((endTime - startTime) / 1000); // In Sekunden umrechnen
      
      setResults(response.results || []);
      setBibliography(response.bibliography || []);
    } catch (error) {
      console.error('Fehler bei der Dokumentenabfrage:', error);
      setError(error.response?.data?.error || 'Fehler bei der Dokumentenabfrage');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Paper elevation={3} sx={{ p: 3, mt: 4, maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Literatur abfragen
      </Typography>
      
      <form onSubmit={handleQuerySubmit}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
          <TextField
            label="Stelle eine Frage zu deinen Dokumenten"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            placeholder="z.B.: Was sind die wichtigsten Erkenntnisse zu Klimawandelauswirkungen in der Landwirtschaft?"
          />
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <Box sx={{ minWidth: 200, flexGrow: 1 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="citation-style-label">Zitationsstil</InputLabel>
                <Select
                  labelId="citation-style-label"
                  value={citationStyle}
                  label="Zitationsstil"
                  onChange={(e) => setCitationStyle(e.target.value)}
                >
                  {availableStyles.map((style) => (
                    <MenuItem key={style.id} value={style.id}>
                      {style.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
            
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Nach bestimmten Dokumenten filtern">
                <Button
                  variant="outlined"
                  startIcon={<FilterListIcon />}
                  onClick={() => setShowFilters(!showFilters)}
                  color={documentFilters.length > 0 ? "primary" : "inherit"}
                >
                  Filter
                  {documentFilters.length > 0 && (
                    <Chip 
                      label={documentFilters.length} 
                      size="small" 
                      color="primary"
                      sx={{ ml: 1 }}
                    />
                  )}
                </Button>
              </Tooltip>
              
              <Button 
                type="submit" 
                variant="contained" 
                color="primary" 
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
                disabled={loading || !query.trim()}
                sx={{ flexGrow: 1 }}
              >
                {loading ? 'Suche...' : 'Suchen'}
              </Button>
            </Box>
          </Box>
          
          {showFilters && (
            <FilterPanel
              documents={availableDocuments}
              selectedDocuments={documentFilters}
              onFilterChange={handleDocumentFilterChange}
              onClose={() => setShowFilters(false)}
            />
          )}
          
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={querySettings.useDirectQuotes}
                  onChange={(e) => handleSettingsChange('useDirectQuotes', e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ mr: 0.5 }}>Direkte Zitate einbeziehen</Typography>
                  <Tooltip title="Wenn aktiviert, können die Ergebnisse exakte Zitate aus dem Text enthalten. Wenn deaktiviert, werden alle Ergebnisse paraphrasiert.">
                    <HelpOutlineIcon fontSize="small" color="action" />
                  </Tooltip>
                </Box>
              }
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={querySettings.includePageNumbers}
                  onChange={(e) => handleSettingsChange('includePageNumbers', e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ mr: 0.5 }}>Seitenzahlen einbeziehen</Typography>
                  <Tooltip title="Seitenzahlen in Zitaten einbeziehen, wenn verfügbar">
                    <HelpOutlineIcon fontSize="small" color="action" />
                  </Tooltip>
                </Box>
              }
            />
            
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2" sx={{ mr: 1 }}>Ergebnisse:</Typography>
              <ButtonGroup size="small">
                <Button 
                  variant={querySettings.maxResults === 3 ? "contained" : "outlined"}
                  onClick={() => handleSettingsChange('maxResults', 3)}
                >
                  3
                </Button>
                <Button 
                  variant={querySettings.maxResults === 5 ? "contained" : "outlined"}
                  onClick={() => handleSettingsChange('maxResults', 5)}
                >
                  5
                </Button>
                <Button 
                  variant={querySettings.maxResults === 10 ? "contained" : "outlined"}
                  onClick={() => handleSettingsChange('maxResults', 10)}
                >
                  10
                </Button>
              </ButtonGroup>
            </Box>
          </Box>
          
          {error && (
            <Alert severity="error" onClose={() => setError('')}>
              {error}
            </Alert>
          )}
        </Box>
      </form>
      
      {/* Ergebnisbereich */}
      {results.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Ergebnisse
              {lastQueryTime && (
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                  ({lastQueryTime.toFixed(2)} Sekunden)
                </Typography>
              )}
            </Typography>
            
            <Box>
              <Tooltip title="Ergebnisse kopieren">
                <IconButton onClick={copyResultsToClipboard}>
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Diese Abfrage speichern">
                <IconButton onClick={saveQueryResults}>
                  <BookmarkIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          
          <Results results={results} />
        </Box>
      )}
      
      {/* Bibliographiebereich */}
      {bibliography.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Literaturverzeichnis
          </Typography>
          
          <Bibliography citations={bibliography} />
        </Box>
      )}
    </Paper>
  );
};

export default QueryInterface;