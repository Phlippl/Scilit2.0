// src/components/pdf/MetadataForm.jsx
import React, { useState } from 'react';
import { 
  TextField, 
  Box, 
  Typography, 
  Divider, 
  Chip,
  Button,
  IconButton,
  Grid,
  Paper,
  List,
  ListItem,
  ListItemText,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DatePicker } from '@mui/x-date-pickers';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import PersonIcon from '@mui/icons-material/Person';

const MetadataForm = ({ metadata, onChange }) => {
  const [authorDialogOpen, setAuthorDialogOpen] = useState(false);
  const [currentAuthor, setCurrentAuthor] = useState({ name: '', orcid: '' });
  const [editingAuthorIndex, setEditingAuthorIndex] = useState(-1);

  // Handle date change
  const handleDateChange = (date) => {
    try {
      // Format the date as YYYY-MM-DD
      const formattedDate = date ? new Date(date).toISOString().split('T')[0] : '';
      onChange('publicationDate', formattedDate);
    } catch (error) {
      console.error('Error formatting date:', error);
      // If there's an error, just pass the raw value
      onChange('publicationDate', date?.toString() || '');
    }
  };

  // Open the author dialog for adding
  const openAddAuthorDialog = () => {
    setCurrentAuthor({ name: '', orcid: '' });
    setEditingAuthorIndex(-1);
    setAuthorDialogOpen(true);
  };

  // Open the author dialog for editing
  const openEditAuthorDialog = (author, index) => {
    setCurrentAuthor({ ...author });
    setEditingAuthorIndex(index);
    setAuthorDialogOpen(true);
  };

  // Handle author dialog close
  const handleAuthorDialogClose = () => {
    setAuthorDialogOpen(false);
  };

  // Save author from dialog
  const saveAuthor = () => {
    if (!currentAuthor.name.trim()) return;

    if (editingAuthorIndex >= 0) {
      // Update existing author
      const updatedAuthors = [...metadata.authors];
      updatedAuthors[editingAuthorIndex] = currentAuthor;
      onChange('authors', updatedAuthors);
    } else {
      // Add new author
      onChange('authors', [...(metadata.authors || []), currentAuthor]);
    }

    setAuthorDialogOpen(false);
  };

  // Remove an author
  const removeAuthor = (index) => {
    const updatedAuthors = [...metadata.authors];
    updatedAuthors.splice(index, 1);
    onChange('authors', updatedAuthors);
  };

  // Update current author in dialog
  const updateCurrentAuthor = (field, value) => {
    setCurrentAuthor(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Format publication date for display
  const formatDate = (dateString) => {
    if (!dateString) return '';
    
    try {
      return new Date(dateString);
    } catch (error) {
      return '';
    }
  };

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <TextField
            required
            fullWidth
            label="Title"
            value={metadata.title || ''}
            onChange={(e) => onChange('title', e.target.value)}
            variant="outlined"
          />
        </Grid>

        <Grid item xs={12}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="subtitle1">Authors</Typography>
              <Button 
                startIcon={<AddIcon />} 
                size="small" 
                onClick={openAddAuthorDialog}
              >
                Add Author
              </Button>
            </Box>
            
            {(!metadata.authors || metadata.authors.length === 0) ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', mb: 1 }}>
                No authors added yet
              </Typography>
            ) : (
              <List dense>
                {metadata.authors.map((author, index) => (
                  <ListItem 
                    key={index}
                    secondaryAction={
                      <Box>
                        <IconButton 
                          edge="end" 
                          aria-label="edit" 
                          onClick={() => openEditAuthorDialog(author, index)}
                          size="small"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton 
                          edge="end" 
                          aria-label="delete" 
                          onClick={() => removeAuthor(index)}
                          size="small"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    }
                  >
                    <ListItemText 
                      primary={author.name} 
                      secondary={author.orcid && `ORCID: ${author.orcid}`} 
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6}>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DatePicker
              label="Publication Date"
              value={formatDate(metadata.publicationDate)}
              onChange={handleDateChange}
              renderInput={(params) => <TextField {...params} fullWidth />}
              format="yyyy-MM-dd"
            />
          </LocalizationProvider>
        </Grid>

        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="Publisher"
            value={metadata.publisher || ''}
            onChange={(e) => onChange('publisher', e.target.value)}
            variant="outlined"
          />
        </Grid>

        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="Journal/Publication"
            value={metadata.journal || ''}
            onChange={(e) => onChange('journal', e.target.value)}
            variant="outlined"
          />
        </Grid>

        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="DOI"
            value={metadata.doi || ''}
            onChange={(e) => onChange('doi', e.target.value)}
            variant="outlined"
            placeholder="10.XXXX/XXXXX"
          />
        </Grid>

        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            label="ISBN"
            value={metadata.isbn || ''}
            onChange={(e) => onChange('isbn', e.target.value)}
            variant="outlined"
            placeholder="e.g., 9780123456789"
          />
        </Grid>

        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Abstract"
            value={metadata.abstract || ''}
            onChange={(e) => onChange('abstract', e.target.value)}
            variant="outlined"
            multiline
            rows={4}
          />
        </Grid>
      </Grid>

      {/* Author Dialog */}
      <Dialog open={authorDialogOpen} onClose={handleAuthorDialogClose} fullWidth maxWidth="sm">
        <DialogTitle>{editingAuthorIndex >= 0 ? 'Edit Author' : 'Add Author'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              autoFocus
              margin="dense"
              label="Author Name"
              fullWidth
              variant="outlined"
              value={currentAuthor.name || ''}
              onChange={(e) => updateCurrentAuthor('name', e.target.value)}
              placeholder="Last Name, First Name"
              helperText="Format: Lastname, Firstname"
            />
            <TextField
              margin="dense"
              label="ORCID (optional)"
              fullWidth
              variant="outlined"
              value={currentAuthor.orcid || ''}
              onChange={(e) => updateCurrentAuthor('orcid', e.target.value)}
              placeholder="0000-0000-0000-0000"
              helperText="If available, enter the author's ORCID identifier"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleAuthorDialogClose}>Cancel</Button>
          <Button onClick={saveAuthor} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MetadataForm;