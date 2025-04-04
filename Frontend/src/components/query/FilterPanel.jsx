// src/components/query/FilterPanel.jsx
import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Checkbox,
  FormControlLabel,
  Box,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Collapse,
  TextField,
  InputAdornment,
  IconButton,
  Chip
} from '@mui/material';

// Icons
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ArticleIcon from '@mui/icons-material/Article';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import ClearIcon from '@mui/icons-material/Clear';
import FilterListIcon from '@mui/icons-material/FilterList';

const FilterPanel = ({ 
  documents = [], 
  selectedDocuments = [], 
  onFilterChange,
  onClose
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({
    articles: true,
    books: true
  });
  
  // Toggle category expansion
  const toggleCategory = (category) => {
    setExpandedCategories({
      ...expandedCategories,
      [category]: !expandedCategories[category]
    });
  };
  
  // Filter documents based on search term
  const filteredDocuments = documents.filter(doc => 
    doc.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (doc.authors && doc.authors.some(author => 
      author.name.toLowerCase().includes(searchTerm.toLowerCase())
    ))
  );
  
  // Group documents by type
  const articleDocs = filteredDocuments.filter(doc => doc.type === 'article');
  const bookDocs = filteredDocuments.filter(doc => doc.type === 'book');
  const otherDocs = filteredDocuments.filter(doc => doc.type !== 'article' && doc.type !== 'book');
  
  // Toggle document selection
  const toggleDocument = (docId) => {
    if (selectedDocuments.includes(docId)) {
      onFilterChange(selectedDocuments.filter(id => id !== docId));
    } else {
      onFilterChange([...selectedDocuments, docId]);
    }
  };
  
  // Select all documents
  const selectAll = () => {
    onFilterChange(documents.map(doc => doc.id));
  };
  
  // Clear all selections
  const clearAll = () => {
    onFilterChange([]);
  };
  
  // Document type counts
  const articleCount = articleDocs.length;
  const bookCount = bookDocs.length;
  const otherCount = otherDocs.length;
  
  return (
    <Paper elevation={0} variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle1">
          Filter Documents
          {selectedDocuments.length > 0 && (
            <Chip 
              label={`${selectedDocuments.length} selected`}
              size="small"
              color="primary"
              sx={{ ml: 1 }}
            />
          )}
        </Typography>
        
        <IconButton size="small" onClick={onClose}>
          <ClearIcon fontSize="small" />
        </IconButton>
      </Box>
      
      <TextField
        fullWidth
        size="small"
        placeholder="Search documents..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 2 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
          endAdornment: searchTerm && (
            <InputAdornment position="end">
              <IconButton 
                edge="end" 
                size="small"
                onClick={() => setSearchTerm('')}
              >
                <ClearIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
      
      {documents.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
          No documents available. Upload documents first.
        </Typography>
      ) : (
        <Box sx={{ maxHeight: 300, overflow: 'auto', mb: 2 }}>
          {/* Articles Section */}
          {articleCount > 0 && (
            <>
              <ListItem 
                button 
                onClick={() => toggleCategory('articles')}
                sx={{ 
                  bgcolor: 'grey.100',
                  borderRadius: 1,
                  mb: 0.5
                }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <ArticleIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary={
                    <Typography variant="body2" fontWeight="medium">
                      Articles ({articleCount})
                    </Typography>
                  } 
                />
                {expandedCategories.articles ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </ListItem>
              
              <Collapse in={expandedCategories.articles} timeout="auto">
                <List dense disablePadding>
                  {articleDocs.map(doc => (
                    <ListItem key={doc.id} sx={{ pl: 4 }}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={selectedDocuments.includes(doc.id)}
                            onChange={() => toggleDocument(doc.id)}
                            size="small"
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body2" noWrap sx={{ maxWidth: 280 }}>
                              {doc.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {doc.authors?.map(a => a.name).join(', ')}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            </>
          )}
          
          {/* Books Section */}
          {bookCount > 0 && (
            <>
              <ListItem 
                button 
                onClick={() => toggleCategory('books')}
                sx={{ 
                  bgcolor: 'grey.100',
                  borderRadius: 1,
                  mb: 0.5,
                  mt: articleCount > 0 ? 1 : 0
                }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <MenuBookIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText 
                  primary={
                    <Typography variant="body2" fontWeight="medium">
                      Books ({bookCount})
                    </Typography>
                  } 
                />
                {expandedCategories.books ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </ListItem>
              
              <Collapse in={expandedCategories.books} timeout="auto">
                <List dense disablePadding>
                  {bookDocs.map(doc => (
                    <ListItem key={doc.id} sx={{ pl: 4 }}>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={selectedDocuments.includes(doc.id)}
                            onChange={() => toggleDocument(doc.id)}
                            size="small"
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body2" noWrap sx={{ maxWidth: 280 }}>
                              {doc.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {doc.authors?.map(a => a.name).join(', ')}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            </>
          )}
          
          {/* Other Documents */}
          {otherCount > 0 && (
            <List dense disablePadding sx={{ mt: 1 }}>
              {otherDocs.map(doc => (
                <ListItem key={doc.id}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedDocuments.includes(doc.id)}
                        onChange={() => toggleDocument(doc.id)}
                        size="small"
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 280 }}>
                          {doc.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {doc.type || 'Document'} • {doc.authors?.map(a => a.name).join(', ')}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      )}
      
      <Divider sx={{ my: 1 }} />
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button 
          size="small" 
          onClick={selectAll}
          disabled={documents.length === 0}
        >
          Select All
        </Button>
        <Button 
          size="small" 
          onClick={clearAll}
          disabled={selectedDocuments.length === 0}
        >
          Clear All
        </Button>
      </Box>
    </Paper>
  );
};

export default FilterPanel;