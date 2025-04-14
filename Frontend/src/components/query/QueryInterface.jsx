// src/components/query/QueryInterface.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
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
  IconButton,
  Chip,
  Tooltip,
  Alert,
  Grid,
  Collapse,
  Fade,
  LinearProgress,
  useTheme
} from '@mui/material';

// Icons
import SearchIcon from '@mui/icons-material/Search';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import BookmarkBorderIcon from '@mui/icons-material/BookmarkBorder';
import HistoryIcon from '@mui/icons-material/History';
import FilterListIcon from '@mui/icons-material/FilterList';
import SettingsIcon from '@mui/icons-material/Settings';
import CloseIcon from '@mui/icons-material/Close';
import TuneIcon from '@mui/icons-material/Tune';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

// Components
import FilterPanel from './FilterPanel';
import Bibliography from './Bibliography';
import Results from './Results';
import QuerySettings from './QuerySettings';

// Hooks
import useQuery from '../../hooks/useQuery';
import { useDocuments } from '../../hooks/useDocuments';

/**
 * Enhanced query interface with improved UX and features
 * 
 * @param {Object} props - Component props
 * @param {string} props.preselectedDocumentId - Optional pre-selected document ID
 */
const QueryInterface = ({ preselectedDocumentId }) => {
  const theme = useTheme();
  const queryInputRef = useRef(null);
  
  // Query state
  const [query, setQuery] = useState('');
  const [documentFilters, setDocumentFilters] = useState(preselectedDocumentId ? [preselectedDocumentId] : []);
  const [citationStyle, setCitationStyle] = useState('apa');
  
  // UI state
  const [showFilters, setShowFilters] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showSavedQueries, setShowSavedQueries] = useState(false);
  const [queryStartTime, setQueryStartTime] = useState(null);
  const [querySettings, setQuerySettings] = useState({
    useDirectQuotes: true,
    maxResults: 5,
    includePageNumbers: true
  });
  
  // Query history state
  const [savedQueries, setSavedQueries] = useState([]);
  
  // Get query hook
  const { 
    queryResults,
    bibliography,
    isLoading, 
    error,
    queryTime,
    citationStyles,
    executeQuery,
    fetchCitationStyles,
    clearResults,
    saveQueryToHistory
  } = useQuery();
  
  // Get documents hook for filtering
  const { documents, isLoading: documentsLoading } = useDocuments();
  
  // Fetch citation styles on mount
  useEffect(() => {
    fetchCitationStyles();
  }, [fetchCitationStyles]);
  
  // Set preselected document as filter
  useEffect(() => {
    if (preselectedDocumentId) {
      setDocumentFilters([preselectedDocumentId]);
    }
  }, [preselectedDocumentId]);
  
  // Auto-focus query input on mount
  useEffect(() => {
    if (queryInputRef.current) {
      queryInputRef.current.focus();
    }
  }, []);
  
  /**
   * Handle query settings change
   */
  const handleSettingsChange = (setting, value) => {
    setQuerySettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };
  
  /**
   * Handle document filter change
   */
  const handleDocumentFilterChange = useCallback((selectedDocuments) => {
    setDocumentFilters(selectedDocuments);
  }, []);
  
  /**
   * Copy results to clipboard
   */
  const copyResultsToClipboard = useCallback(() => {
    try {
      // Format results and bibliography as text
      const resultsText = queryResults
        .map(result => `${result.text}\n(${result.source})`)
        .join('\n\n');
      
      const bibText = bibliography.length > 0 
        ? '\n\nLiteraturverzeichnis\n' + bibliography.join('\n')
        : '';
      
      const fullText = resultsText + bibText;
      
      // Copy to clipboard
      navigator.clipboard.writeText(fullText);
    } catch (error) {
      console.error('Error copying to clipboard:', error);
    }
  }, [queryResults, bibliography]);
  
  /**
   * Save current query and results
   */
  const saveCurrentQuery = useCallback(() => {
    if (!query || queryResults.length === 0) return;
    
    const queryData = {
      query,
      timestamp: new Date().toISOString(),
      results: queryResults,
      bibliography,
      settings: {
        citationStyle,
        documentFilters,
        ...querySettings
      }
    };
    
    saveQueryToHistory(queryData);
    
    // Update local state (normally this would come from the backend)
    setSavedQueries(prev => [queryData, ...prev]);
  }, [query, queryResults, bibliography, citationStyle, documentFilters, querySettings, saveQueryToHistory]);
  
  /**
   * Load a saved query
   */
  const loadSavedQuery = useCallback((savedQuery) => {
    setQuery(savedQuery.query);
    setCitationStyle(savedQuery.settings?.citationStyle || 'apa');
    setDocumentFilters(savedQuery.settings?.documentFilters || []);
    setQuerySettings(prev => ({
      ...prev,
      ...(savedQuery.settings || {})
    }));
    
    // Close saved queries panel
    setShowSavedQueries(false);
    
    // Execute the query (optional)
    // executeQuery({
    //   query: savedQuery.query,
    //   citation_style: savedQuery.settings?.citationStyle || 'apa',
    //   document_ids: savedQuery.settings?.documentFilters,
    //   n_results: savedQuery.settings?.maxResults || 5,
    //   use_direct_quotes: savedQuery.settings?.useDirectQuotes !== false,
    //   include_page_numbers: savedQuery.settings?.includePageNumbers !== false
    // });
  }, []);
  
  /**
   * Handle query submission
   */
  const handleQuerySubmit = async (e) => {
    e?.preventDefault();
    
    if (!query.trim()) return;
    
    // Clear previous results
    clearResults();
    
    // Track start time
    setQueryStartTime(Date.now());
    
    try {
      await executeQuery({
        query: query.trim(),
        citation_style: citationStyle,
        document_ids: documentFilters.length > 0 ? documentFilters : undefined,
        n_results: querySettings.maxResults,
        use_direct_quotes: querySettings.useDirectQuotes,
        include_page_numbers: querySettings.includePageNumbers
      });
    } catch (err) {
      console.error('Query execution error:', err);
    }
  };
  
  // Elapsed time calculation for streaming response
  const [elapsedTime, setElapsedTime] = useState(0);
  
  useEffect(() => {
    let timer;
    if (isLoading && queryStartTime) {
      timer = setInterval(() => {
        setElapsedTime((Date.now() - queryStartTime) / 1000);
      }, 100);
    } else if (!isLoading) {
      setElapsedTime(0);
    }
    
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isLoading, queryStartTime]);
  
  return (
    <Paper elevation={3} sx={{ p: 3, mt: 4, maxWidth: 900, mx: 'auto', overflow: 'hidden' }}>
      <Box sx={{ position: 'relative' }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Literatur abfragen
        </Typography>
        
        {/* Floating action buttons */}
        <Box sx={{ position: 'absolute', top: 0, right: 0, display: 'flex', gap: 1 }}>
          <Tooltip title="Frühere Abfragen anzeigen">
            <IconButton
              color={showSavedQueries ? "primary" : "default"}
              onClick={() => {
                setShowSavedQueries(!showSavedQueries);
                setShowFilters(false);
                setShowSettings(false);
              }}
              size="small"
            >
              <HistoryIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Filtereinstellungen">
            <IconButton
              color={showFilters ? "primary" : "default"}
              onClick={() => {
                setShowFilters(!showFilters);
                setShowSavedQueries(false);
                setShowSettings(false);
              }}
              size="small"
            >
              <FilterListIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Abfrageeinstellungen">
            <IconButton
              color={showSettings ? "primary" : "default"}
              onClick={() => {
                setShowSettings(!showSettings);
                setShowSavedQueries(false);
                setShowFilters(false);
              }}
              size="small"
            >
              <TuneIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>
      
      {/* Query form */}
      <form onSubmit={handleQuerySubmit}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
          <TextField
            inputRef={queryInputRef}
            label="Stelle eine Frage zu deinen Dokumenten"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            placeholder="z.B.: Was sind die wichtigsten Erkenntnisse zu Klimawandelauswirkungen in der Landwirtschaft?"
            InputProps={{
              endAdornment: query && (
                <Tooltip title="Eingabe löschen">
                  <IconButton
                    onClick={() => {
                      setQuery('');
                      if (queryInputRef.current) {
                        queryInputRef.current.focus();
                      }
                    }}
                    edge="end"
                  >
                    <CloseIcon />
                  </IconButton>
                </Tooltip>
              )
            }}
          />
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <Box sx={{ minWidth: 200, flexGrow: 1, display: 'flex', gap: 1 }}>
              <FormControl fullWidth size="small" sx={{ flexGrow: 1 }}>
                <InputLabel id="citation-style-label">Zitationsstil</InputLabel>
                <Select
                  labelId="citation-style-label"
                  value={citationStyle}
                  label="Zitationsstil"
                  onChange={(e) => setCitationStyle(e.target.value)}
                >
                  {citationStyles.map((style) => (
                    <MenuItem key={style.id} value={style.id}>
                      {style.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              {documentFilters.length > 0 && (
                <Tooltip title="Filter zurücksetzen">
                  <IconButton 
                    size="small" 
                    onClick={() => setDocumentFilters([])}
                    sx={{ mt: 0.5 }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
            
            <Box sx={{ display: 'flex', gap: 1 }}>
              {/* Filtered documents count chip */}
              {documentFilters.length > 0 && (
                <Chip 
                  icon={<FilterListIcon />}
                  label={`${documentFilters.length} ${documentFilters.length === 1 ? 'Dokument' : 'Dokumente'}`}
                  color="primary"
                  variant="outlined"
                  onClick={() => setShowFilters(true)}
                  size="medium"
                  sx={{ height: 40 }}
                />
              )}
              
              <Button 
                type="submit" 
                variant="contained" 
                color="primary" 
                startIcon={isLoading ? <CircularProgress size={20} color="inherit" /> : <SearchIcon />}
                disabled={isLoading || !query.trim()}
                sx={{ minWidth: 120 }}
              >
                {isLoading ? 'Suche...' : 'Suchen'}
              </Button>
            </Box>
          </Box>
          
          {/* Settings panels */}
          <Collapse in={showFilters}>
            <Box sx={{ mt: 2, mb: 1 }}>
              <FilterPanel
                documents={documents}
                selectedDocuments={documentFilters}
                onFilterChange={handleDocumentFilterChange}
                onClose={() => setShowFilters(false)}
                isLoading={documentsLoading}
              />
            </Box>
          </Collapse>
          
          <Collapse in={showSettings}>
            <Box sx={{ mt: 2, mb: 1 }}>
              <QuerySettings 
                settings={querySettings}
                onChange={handleSettingsChange}
                onClose={() => setShowSettings(false)}
              />
            </Box>
          </Collapse>
          
          <Collapse in={showSavedQueries}>
            <Box sx={{ mt: 2, mb: 1 }}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle1">
                    Gespeicherte Abfragen
                  </Typography>
                  <IconButton size="small" onClick={() => setShowSavedQueries(false)}>
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
                
                {savedQueries.length === 0 ? (
                  <Typography variant="body2" color="text.secondary" align="center">
                    Keine gespeicherten Abfragen vorhanden
                  </Typography>
                ) : (
                  <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                    {savedQueries.map((savedQuery, index) => (
                      <Box 
                        key={index} 
                        sx={{ 
                          p: 1.5, 
                          mb: 1, 
                          borderRadius: 1, 
                          bgcolor: 'background.subtle',
                          cursor: 'pointer',
                          '&:hover': { bgcolor: 'action.hover' }
                        }}
                        onClick={() => loadSavedQuery(savedQuery)}
                      >
                        <Typography variant="body2" noWrap>
                          {savedQuery.query}
                        </Typography>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(savedQuery.timestamp).toLocaleString()}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {savedQuery.results.length} Ergebnisse
                          </Typography>
                        </Box>
                      </Box>
                    ))}
                  </Box>
                )}
              </Paper>
            </Box>
          </Collapse>
          
          {error && (
            <Alert severity="error" onClose={() => {/* reset error */}}>
              {error}
            </Alert>
          )}
        </Box>
      </form>
      
      {/* Loading progress */}
      {isLoading && (
        <Box sx={{ mb: 3 }}>
          <LinearProgress />
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Suche in Dokumenten... {elapsedTime.toFixed(1)}s
            </Typography>
          </Box>
        </Box>
      )}
      
      {/* Results section */}
      {queryResults.length > 0 && (
        <Fade in timeout={500}>
          <Box sx={{ mt: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                Ergebnisse
                {queryTime && (
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                    ({queryTime.toFixed(2)} Sekunden)
                  </Typography>
                )}
              </Typography>
              
              <Box>
                <Tooltip title="Ergebnisse kopieren">
                  <IconButton onClick={copyResultsToClipboard}>
                    <ContentCopyIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title={savedQueries.some(q => q.query === query) ? "Bereits gespeichert" : "Diese Abfrage speichern"}>
                  <IconButton 
                    onClick={saveCurrentQuery}
                    color={savedQueries.some(q => q.query === query) ? "primary" : "default"}
                  >
                    {savedQueries.some(q => q.query === query) ? <BookmarkIcon /> : <BookmarkBorderIcon />}
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
            
            <Results results={queryResults} />
          </Box>
        </Fade>
      )}
      
      {/* Bibliography section */}
      {bibliography.length > 0 && (
        <Fade in timeout={500}>
          <Box sx={{ mt: 4 }}>
            <Divider sx={{ mb: 2 }} />
            <Bibliography 
              citations={bibliography} 
              title="Literaturverzeichnis"
              onCopyCitation={(citation) => {
                navigator.clipboard.writeText(citation);
              }}
              onCopyAll={() => {
                navigator.clipboard.writeText(bibliography.join('\n\n'));
              }}
            />
          </Box>
        </Fade>
      )}
      
      {/* Empty state */}
      {!isLoading && queryResults.length === 0 && query.trim() && (
        <Box sx={{ mt: 4, textAlign: 'center', p: 3 }}>
          <HelpOutlineIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Keine Ergebnisse gefunden
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Versuche es mit einer anderen Abfrage oder erweitere die Dokumentauswahl.
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default QueryInterface;