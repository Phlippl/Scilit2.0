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
  useTheme,
  Grid,
  Radio,
  RadioGroup,
  ButtonGroup
} from '@mui/material';

// Icons
import SearchIcon from '@mui/icons-material/Search';
import SaveIcon from '@mui/icons-material/Save';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import BookmarkIcon from '@mui/icons-material/Bookmark';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import FilterListIcon from '@mui/icons-material/FilterList';
import FormatQuoteIcon from '@mui/icons-material/FormatQuote';

// Services
import * as queryApi from '../../api/query';
import * as documentsApi from '../../api/documents';

// Components
import QueryResults from './QueryResults';
import Bibliography from './Bibliography';
import FilterPanel from './FilterPanel';

// Hooks
import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

const QueryInterface = () => {
  const theme = useTheme();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  
  // Query state
  const [query, setQuery] = useState('');
  const [documentFilters, setDocumentFilters] = useState([]);
  const [citationStyle, setCitationStyle] = useState('apa');
  const [availableStyles, setAvailableStyles] = useState([
    { id: 'apa', name: 'APA 7th Edition' },
    { id: 'chicago', name: 'Chicago 18th Edition' },
    { id: 'harvard', name: 'Harvard' }
  ]);
  
  // Results state
  const [results, setResults] = useState([]);
  const [bibliography, setBibliography] = useState([]);
  
  // UI state
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
  
  // Get available documents and citation styles on component mount
  useEffect(() => {
    // Check authentication
    if (!isAuthenticated) {
      navigate('/login', { state: { from: '/query' } });
      return;
    }
    
    // Fetch available documents
    const fetchDocuments = async () => {
      try {
        const docs = await documentsApi.getDocuments();
        setAvailableDocuments(docs);
      } catch (error) {
        console.error('Error fetching documents:', error);
        setError('Could not load your documents. Please try again later.');
      }
    };
    
    // Fetch available citation styles
    const fetchCitationStyles = async () => {
      try {
        const styles = await queryApi.getSupportedCitationStyles();
        if (styles && styles.length > 0) {
          setAvailableStyles(styles);
        }
      } catch (error) {
        console.error('Error fetching citation styles:', error);
        // Keep default styles
      }
    };
    
    fetchDocuments();
    fetchCitationStyles();
  }, [isAuthenticated, navigate]);
  
  /**
   * Handle query settings change
   */
  const handleSettingsChange = (setting, value) => {
    setQuerySettings({
      ...querySettings,
      [setting]: value
    });
  };
  
  /**
   * Handle document filter changes
   */
  const handleDocumentFilterChange = (selectedDocuments) => {
    setDocumentFilters(selectedDocuments);
  };
  
  /**
   * Copy results to clipboard
   */
  const copyResultsToClipboard = () => {
    try {
      // Format results and bibliography as text
      const resultsText = results
        .map(result => `${result.text}\n(${result.source})`)
        .join('\n\n');
      
      const bibText = bibliography.length > 0 
        ? '\n\nReferences\n' + bibliography.join('\n')
        : '';
      
      const fullText = resultsText + bibText;
      
      // Copy to clipboard
      navigator.clipboard.writeText(fullText);
      
      // Could add a success message here
    } catch (error) {
      console.error('Error copying to clipboard:', error);
      setError('Failed to copy results to clipboard');
    }
  };
  
  /**
   * Save query and results
   */
  const saveQueryResults = async () => {
    try {
      // This would save the query and results to the backend
      // Not implemented in this example
      console.log('Saving query results:', {
        query,
        results,
        bibliography,
        timestamp: new Date().toISOString()
      });
      
      // Show success message
    } catch (error) {
      console.error('Error saving query:', error);
      setError('Failed to save query results');
    }
  };
  
  /**
   * Handle query submission
   */
  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Please enter a query');
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
      setLastQueryTime((endTime - startTime) / 1000); // Convert to seconds
      
      setResults(response.results || []);
      setBibliography(response.bibliography || []);
    } catch (error) {
      console.error('Error querying documents:', error);
      setError(error.response?.data?.error || 'Error querying documents');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Paper elevation={3} sx={{ p: 3, mt: 4, maxWidth: 900, mx: 'auto' }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Query Your Literature
      </Typography>
      
      <form onSubmit={handleQuerySubmit}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
          <TextField
            label="Ask a question about your documents"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            fullWidth
            multiline
            rows={3}
            variant="outlined"
            placeholder="e.g., What are the key findings on climate change impacts in agriculture?"
          />
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <Box sx={{ minWidth: 200, flexGrow: 1 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="citation-style-label">Citation Style</InputLabel>
                <Select
                  labelId="citation-style-label"
                  value={citationStyle}
                  label="Citation Style"
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
              <Tooltip title="Filter by specific documents">
                <Button
                  variant="outlined"
                  startIcon={<FilterListIcon />}
                  onClick={() => setShowFilters(!showFilters)}
                  color={documentFilters.length > 0 ? "primary" : "inherit"}
                >
                  Filters
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
                {loading ? 'Searching...' : 'Search'}
              </Button>
            </Box>
          </Box>
          
          {showFilters && (
            <Paper variant="outlined" sx={{ p: 2, mt: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Filter Documents
              </Typography>
              
              {availableDocuments.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No documents available. Upload documents first.
                </Typography>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={documentFilters.length === 0}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setDocumentFilters([]);
                            }
                          }}
                        />
                      }
                      label="Search all documents"
                    />
                  </Grid>
                  
                  {availableDocuments.map((doc) => (
                    <Grid item xs={12} sm={6} key={doc.id}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={documentFilters.includes(doc.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setDocumentFilters([...documentFilters, doc.id]);
                              } else {
                                setDocumentFilters(documentFilters.filter(id => id !== doc.id));
                              }
                            }}
                          />
                        }
                        label={doc.title}
                      />
                    </Grid>
                  ))}
                </Grid>
              )}
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                <Button 
                  size="small" 
                  onClick={() => setDocumentFilters(availableDocuments.map(doc => doc.id))}
                >
                  Select All
                </Button>
                <Button 
                  size="small" 
                  onClick={() => setDocumentFilters([])}
                >
                  Clear All
                </Button>
              </Box>
            </Paper>
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
                  <Typography variant="body2" sx={{ mr: 0.5 }}>Include direct quotes</Typography>
                  <Tooltip title="When enabled, results may include exact quotes from the text. When disabled, all results will be paraphrased.">
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
                  <Typography variant="body2" sx={{ mr: 0.5 }}>Include page numbers</Typography>
                  <Tooltip title="Include page numbers in citations when available">
                    <HelpOutlineIcon fontSize="small" color="action" />
                  </Tooltip>
                </Box>
              }
            />
            
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2" sx={{ mr: 1 }}>Results:</Typography>
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
      
      {/* Results section */}
      {results.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Results
              {lastQueryTime && (
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                  ({lastQueryTime.toFixed(2)} seconds)
                </Typography>
              )}
            </Typography>
            
            <Box>
              <Tooltip title="Copy results">
                <IconButton onClick={copyResultsToClipboard}>
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Save this query">
                <IconButton onClick={saveQueryResults}>
                  <BookmarkIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          
          {results.map((result, index) => (
            <Card key={index} sx={{ mb: 2, backgroundColor: '#f9f9f9' }}>
              <CardContent>
                <Typography variant="body1" paragraph>
                  {result.text}
                </Typography>
                <Typography variant="body2" color="text.secondary" align="right">
                  {result.source}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
      
      {/* Bibliography section */}
      {bibliography.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            References
          </Typography>
          
          <Box component="ol" sx={{ pl: 2 }}>
            {bibliography.map((citation, index) => (
              <Typography 
                component="li" 
                key={index} 
                variant="body2" 
                paragraph
                sx={{ 
                  textIndent: '-1.5em', 
                  paddingLeft: '1.5em',
                  mb: 1.5 
                }}
              >
                {citation}
              </Typography>
            ))}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default QueryInterface;