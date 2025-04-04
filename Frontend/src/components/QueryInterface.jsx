// Frontend/src/components/QueryInterface.jsx
import React, { useState } from 'react';
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
  CardContent
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import axios from 'axios';

const QueryInterface = () => {
  const [query, setQuery] = useState('');
  const [citationStyle, setCitationStyle] = useState('apa');
  const [results, setResults] = useState([]);
  const [bibliography, setBibliography] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
    
    try {
      const response = await axios.post('/api/query', {
        query: query.trim(),
        citation_style: citationStyle,
        n_results: 5
      });
      
      setResults(response.data.results || []);
      setBibliography(response.data.bibliography || []);
    } catch (error) {
      console.error('Error querying documents:', error);
      setError(error.response?.data?.error || 'Error querying documents');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, mt: 4, maxWidth: 800, mx: 'auto' }}>
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
            rows={2}
            variant="outlined"
            placeholder="e.g., What are the key findings on climate change impacts?"
          />
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel id="citation-style-label">Citation Style</InputLabel>
              <Select
                labelId="citation-style-label"
                value={citationStyle}
                label="Citation Style"
                onChange={(e) => setCitationStyle(e.target.value)}
              >
                <MenuItem value="apa">APA 7th Edition</MenuItem>
                <MenuItem value="chicago">Chicago 18th Edition</MenuItem>
                <MenuItem value="harvard">Harvard</MenuItem>
              </Select>
            </FormControl>
            
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
          
          {error && (
            <Typography color="error" variant="body2">
              {error}
            </Typography>
          )}
        </Box>
      </form>
      
      {/* Results section */}
      {results.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Results
          </Typography>
          
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