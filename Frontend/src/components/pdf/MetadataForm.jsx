// src/components/pdf/MetadataForm.jsx
import React, { useState, useEffect } from 'react';
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
  DialogActions,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  FormHelperText,
  InputAdornment,
  Tooltip
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import PersonIcon from '@mui/icons-material/Person';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

import { formatToISODate, formatFromISODate } from '../../utils/dateFormatter';

/**
 * Dynamisches Metadatenformular, das sich basierend auf dem Dokumenttyp anpasst
 * 
 * @param {Object} props - Komponenten-Props
 * @param {Object} props.metadata - Metadaten des Dokuments
 * @param {Function} props.onChange - Callback für Änderungen (field, value)
 */
const MetadataForm = ({ metadata, onChange }) => {
  const [authorDialogOpen, setAuthorDialogOpen] = useState(false);
  const [currentAuthor, setCurrentAuthor] = useState({ name: '', orcid: '' });
  const [editingAuthorIndex, setEditingAuthorIndex] = useState(-1);
  const [allFields, setAllFields] = useState({});
  
  // Verfügbare Dokumenttypen
  const documentTypes = [
    { id: 'article', label: 'Zeitschriftenaufsatz' },
    { id: 'book', label: 'Buch (Monographie)' },
    { id: 'edited_book', label: 'Buch (Sammelwerk)' },
    { id: 'conference', label: 'Tagungsband' },
    { id: 'thesis', label: 'Hochschulschrift' },
    { id: 'report', label: 'Graue Literatur / Bericht / Report' },
    { id: 'newspaper', label: 'Zeitungsartikel' },
    { id: 'website', label: 'Internetdokument' },
    { id: 'interview', label: 'Interviewmaterial' },
    { id: 'press', label: 'Pressemitteilung' },
    { id: 'other', label: 'Unklarer Dokumententyp' }
  ];
  
  // Dokumenttyp mit Fallback
  const documentType = metadata?.type || 'other';
  
  // Prüfen und korrigieren des Dokumenttyps
  useEffect(() => {
    // Map CrossRef document types to our application's types
    const crossRefTypeMapping = {
      'journal-article': 'article',
      'book-chapter': 'book',
      'monograph': 'book',
      'edited-book': 'edited_book',
      'proceedings-article': 'conference',
      'proceedings': 'conference',
      'conference-paper': 'conference',
      'dissertation': 'thesis'
    };

    // Sanitize document type if needed
    if (metadata?.type) {
      const validTypes = documentTypes.map(type => type.id);
      if (!validTypes.includes(metadata.type)) {
        // Try to map the type
        let newType = crossRefTypeMapping[metadata.type] || 'article';
        console.log(`Sanitizing document type from ${metadata.type} to ${newType}`);
        
        // Update the type
        onChange('type', newType);
      }
    }
  }, [metadata?.type, onChange, documentTypes]);
  
  /**
   * Konfigurationsobjekt für die dynamischen Felder basierend auf dem Dokumenttyp
   */
  const typeConfigs = {
    article: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12, multiline: true, rows: 3 },    
      { id: 'journal', label: 'Zeitschrift', gridWidth: 8, multiline: true, rows: 2 },
      { id: 'volume', label: 'Jahrgang', gridWidth: 2 },
      { id: 'issue', label: 'Heftnummer', gridWidth: 2 },
      { id: 'pages', label: 'Seiten von-bis', gridWidth: 2.2 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 2.8 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'publisher', label: 'Verlag', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    book: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'publisher', label: 'Verlag', gridWidth: 8 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 4 },
      { id: 'publisherLocation', label: 'Verlagsort', gridWidth: 6 },
      { id: 'edition', label: 'Auflage', gridWidth: 3 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'series', label: 'Reihentitel', gridWidth: 6 },
      { id: 'seriesNumber', label: 'Bandnr. der Reihe', gridWidth: 3 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    edited_book: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'publisher', label: 'Verlag', gridWidth: 8 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 4 },
      { id: 'publisherLocation', label: 'Verlagsort', gridWidth: 6 },
      { id: 'edition', label: 'Auflage', gridWidth: 3 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'series', label: 'Reihentitel', gridWidth: 6 },
      { id: 'seriesNumber', label: 'Bandnr. der Reihe', gridWidth: 3 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    conference: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'conference', label: 'Tagungsname', gridWidth: 6 },
      { id: 'conferenceLocation', label: 'Tagungsort', gridWidth: 6 },
      { id: 'conferenceDate', label: 'Tagungsdatum', gridWidth: 3 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 3 },
      { id: 'publisherLocation', label: 'Verlagsort', gridWidth: 4 },
      { id: 'publisher', label: 'Verlag', gridWidth: 8 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    thesis: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'thesisType', label: 'Art der Schrift', gridWidth: 6 },
      { id: 'publicationDate', label: 'Datum / Jahr', type: 'date', gridWidth: 6 },
      { id: 'university', label: 'Hochschule', gridWidth: 8 },
      { id: 'department', label: 'Institut', gridWidth: 6 },
      { id: 'location', label: 'Hochschulort', gridWidth: 6 },
      { id: 'advisor', label: 'Betreuer', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    report: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'institution', label: 'Institution', gridWidth: 8 },
      { id: 'publicationDate', label: 'Datum / Jahr', type: 'date', gridWidth: 4 },
      { id: 'location', label: 'Erscheinungsort', gridWidth: 6 },
      { id: 'reportNumber', label: 'Nummer', gridWidth: 3 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    newspaper: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'newspaper', label: 'Zeitung', gridWidth: 8 },
      { id: 'publicationDate', label: 'Datum', type: 'date', gridWidth: 4 },
      { id: 'location', label: 'Ort', gridWidth: 6 },
      { id: 'edition', label: 'Ausgabe', gridWidth: 3 },
      { id: 'pages', label: 'Seiten von-bis', gridWidth: 4 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    website: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'url', label: 'Online-Adresse', gridWidth: 12 },
      { id: 'institution', label: 'Institution', gridWidth: 8 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 4 },
      { id: 'lastUpdated', label: 'Letzte Aktualisierung', type: 'date', gridWidth: 6 },
      { id: 'accessDate', label: 'Zuletzt geprüft am', type: 'date', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    interview: [
      { id: 'title', label: 'Titel / Thema', required: true, gridWidth: 12 },
      { id: 'interviewer', label: 'Interviewer', gridWidth: 6 },
      { id: 'interviewee', label: 'Interviewte Person', gridWidth: 6 },
      { id: 'date', label: 'Datum', type: 'date', gridWidth: 4 },
      { id: 'duration', label: 'Länge', gridWidth: 4 },
      { id: 'location', label: 'Ort', gridWidth: 6 },
      { id: 'medium', label: 'Medium', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 }
    ],
    
    press: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'institution', label: 'Institution', gridWidth: 8 },
      { id: 'contactPerson', label: 'Kontaktperson', gridWidth: 6 },
      { id: 'contactAddress', label: 'Kontaktadresse', gridWidth: 6 },
      { id: 'date', label: 'Datum', type: 'date', gridWidth: 4 },
      { id: 'location', label: 'Ort', gridWidth: 6 },
      { id: 'embargo', label: 'Sperrfrist', gridWidth: 3 },
      { id: 'url', label: 'Online-Adresse', gridWidth: 8 },
      { id: 'accessDate', label: 'Zuletzt geprüft am', type: 'date', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 }
    ],
    
    // Fallback für unbekannte Dokumenttypen
    other: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'publisher', label: 'Verlag', gridWidth: 8 },
      { id: 'journal', label: 'Zeitschrift', gridWidth: 8 },
      { id: 'publicationDate', label: 'Jahr/Datum', type: 'date', gridWidth: 4 },
      { id: 'edition', label: 'Auflage', gridWidth: 3 },
      { id: 'pages', label: 'Seiten von-bis', gridWidth: 4 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'url', label: 'Online-Adresse', gridWidth: 8 },
      { id: 'accessDate', label: 'Zuletzt geprüft am', type: 'date', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ]
  };
  
  // Aktive Konfiguration für den aktuellen Dokumenttyp
  const activeConfig = typeConfigs[documentType] || typeConfigs.other;

  // Bei Änderungen der Metadaten alle Felder aktualisieren
  useEffect(() => {
    if (!metadata) return;
    
    // Sammle alle Felder aus den Metadaten
    const fields = { ...metadata };
    
    // Stellen Sie sicher, dass der Dokumenttyp gültig ist
    if (fields.type) {
      const validTypes = documentTypes.map(t => t.id);
      if (!validTypes.includes(fields.type)) {
        // Mapping für CrossRef-Typen
        const typeMapping = {
          'journal-article': 'article',
          'book-chapter': 'book',
          'monograph': 'book',
          'edited-book': 'edited_book',
          'proceedings-article': 'conference',
          'proceedings': 'conference',
          'conference-paper': 'conference',
          'dissertation': 'thesis'
        };
        
        // Korrigieren des Typs
        if (fields.type in typeMapping) {
          fields.type = typeMapping[fields.type];
          console.log(`Corrected document type from ${metadata.type} to ${fields.type}`);
          
          // Update the metadata
          onChange('type', fields.type);
        } else {
          // Fallback auf 'article'
          fields.type = 'article';
          console.log(`Unknown document type ${metadata.type}, defaulting to 'article'`);
          
          // Update the metadata
          onChange('type', 'article');
        }
      }
    }
    
    setAllFields(fields);
  }, [metadata, onChange, documentTypes]);

  // Typ des Dokuments ändern
  const handleTypeChange = (event) => {
    // Map any invalid types to valid ones
    let newType = event.target.value;
    
    // Handle special values that may come from CrossRef
    if (newType === 'journal-article') {
      newType = 'article';
    } else if (newType.includes('book') && newType !== 'book' && newType !== 'edited_book') {
      newType = 'book';
    } else if (newType.includes('conference') && newType !== 'conference') {
      newType = 'conference';
    }
    
    // Check if newType is in the valid options
    const validTypes = ['article', 'book', 'edited_book', 'conference', 'thesis', 
                       'report', 'newspaper', 'website', 'interview', 'press', 'other'];
    
    if (!validTypes.includes(newType)) {
      console.warn(`Invalid type detected: ${newType}, defaulting to 'article'`);
      newType = 'article';
    }
    
    // Now use the sanitized type
    onChange('type', newType);
  };
  
  // Hilfsfunktion für die Datumsformatierung
  const formatDateForDisplay = (dateString) => {
    if (!dateString) return '';
    
    // Wenn im ISO-Format, zeige es formatiert an
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
      return formatFromISODate(dateString);
    }
    
    // Ansonsten zeige es unverändert an
    return dateString;
  };
  
  // Autor-Dialog öffnen für Hinzufügen
  const openAddAuthorDialog = () => {
    setCurrentAuthor({ name: '', orcid: '' });
    setEditingAuthorIndex(-1);
    setAuthorDialogOpen(true);
  };

  // Autor-Dialog öffnen für Bearbeiten
  const openEditAuthorDialog = (author, index) => {
    setCurrentAuthor({ ...author });
    setEditingAuthorIndex(index);
    setAuthorDialogOpen(true);
  };

  // Autor-Dialog schließen
  const handleAuthorDialogClose = () => {
    setAuthorDialogOpen(false);
  };

  // Autor aus Dialog speichern
  const saveAuthor = () => {
    if (!currentAuthor.name.trim()) return;

    if (editingAuthorIndex >= 0) {
      // Vorhandenen Autor aktualisieren
      const updatedAuthors = [...(metadata.authors || [])];
      updatedAuthors[editingAuthorIndex] = currentAuthor;
      onChange('authors', updatedAuthors);
    } else {
      // Neuen Autor hinzufügen
      onChange('authors', [...(metadata.authors || []), currentAuthor]);
    }

    setAuthorDialogOpen(false);
  };

  // Autor entfernen
  const removeAuthor = (index) => {
    const updatedAuthors = [...(metadata.authors || [])];
    updatedAuthors.splice(index, 1);
    onChange('authors', updatedAuthors);
  };

  // Aktuellen Autor im Dialog aktualisieren
  const updateCurrentAuthor = (field, value) => {
    setCurrentAuthor(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Grid container spacing={1} sx={{ width: '100%' }}>
        {/* Dokumenttyp-Auswahl */}
        <Grid item xs={12} sx={{ mb: 1 }}>
          <FormControl fullWidth size="small">
            <InputLabel id="document-type-label">Dokumententyp</InputLabel>
            <Select
              labelId="document-type-label"
              id="document-type"
              value={documentType}
              label="Dokumententyp"
              onChange={handleTypeChange}
            >
              {documentTypes.map((type) => (
                <MenuItem key={type.id} value={type.id}>
                  {type.label}
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>
              Wähle den passenden Dokumenttyp für die entsprechenden Metadatenfelder
            </FormHelperText>
          </FormControl>
        </Grid>

        {/* Autorensektion */}
        <Grid item xs={12} sx={{ my: 0 }}>
          <Paper variant="outlined" sx={{ p: 1 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle2">
                {documentType === 'edited_book' || documentType === 'conference' ? 'Herausgeber' : 'Autoren'}
              </Typography>
              <Button 
                startIcon={<AddIcon />} 
                size="small" 
                onClick={openAddAuthorDialog}
                variant="text"
                color="primary"
                sx={{ py: 0, minWidth: 'auto' }}
              >
                {documentType === 'edited_book' || documentType === 'conference' ? 'Hinzufügen' : 'Hinzufügen'}
              </Button>
            </Box>

            {(!metadata.authors || metadata.authors.length === 0) ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', fontSize: '0.8rem' }}>
                {documentType === 'edited_book' || documentType === 'conference' 
                  ? 'Noch keine Herausgeber' 
                  : 'Noch keine Autoren'}
              </Typography>
            ) : (
              <List dense sx={{ py: 0 }}>
                {metadata.authors.map((author, index) => (
                  <ListItem 
                    key={index}
                    secondaryAction={
                      <Box sx={{ display: 'flex' }}>
                        <IconButton 
                          edge="end" 
                          aria-label="edit" 
                          onClick={() => openEditAuthorDialog(author, index)}
                          size="small"
                          sx={{ p: 0.5 }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton 
                          edge="end" 
                          aria-label="delete" 
                          onClick={() => removeAuthor(index)}
                          size="small"
                          sx={{ p: 0.5 }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    }
                    sx={{ py: 0 }}
                  >
                    <ListItemText 
                      primary={author.name} 
                      secondary={author.orcid && `ORCID: ${author.orcid}`}
                      primaryTypographyProps={{ fontSize: '0.9rem' }}
                      secondaryTypographyProps={{ fontSize: '0.75rem' }}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Dynamische Felder basierend auf dem Dokumenttyp */}
        {activeConfig.map((field) => {
          // Berechnen der Grid-Breite basierend auf der Bildschirmgröße
          const fieldWidth = field.gridWidth || 12;
          return (
            <Grid item xs={12} sm={fieldWidth} md={fieldWidth} key={field.id} sx={{ px: 1 }}>
              <TextField
                fullWidth
                label={field.label}
                // Wir behandeln Datumsfelder als Textfelder für mehr Flexibilität
                type={field.type === 'date' ? 'text' : (field.type || 'text')}
                required={field.required}
                multiline={field.multiline}
                rows={field.rows}
                value={metadata[field.id] || ''}
                onChange={(e) => {
                  // Bei Datumsfeldern versuchen wir gleich zu formatieren
                  if (field.type === 'date') {
                    const formattedDate = formatToISODate(e.target.value);
                    onChange(field.id, formattedDate);
                  } else {
                    onChange(field.id, e.target.value);
                  }
                }}
                variant="outlined"
                InputLabelProps={field.type === 'date' ? {
                  shrink: true,
                } : undefined}
                // Für Datumsfelder ein Hilfsmuster anzeigen und Icon
                helperText={field.type === 'date' ? 'Format: JJJJ-MM-TT' : undefined}
                InputProps={field.type === 'date' ? {
                  endAdornment: (
                    <InputAdornment position="end">
                      <Tooltip title="Gültiges Datumsformat: JJJJ-MM-TT">
                        <CalendarTodayIcon color="action" fontSize="small" />
                      </Tooltip>
                    </InputAdornment>
                  ),
                } : undefined}
                // Größe der Felder
                size="small"
                sx={{ 
                  my: 0.5,
                }}
              />
            </Grid>
          );
        })}
      </Grid>

      {/* Autor-Dialog */}
      <Dialog open={authorDialogOpen} onClose={handleAuthorDialogClose} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingAuthorIndex >= 0 
            ? (documentType === 'edited_book' || documentType === 'conference' ? 'Herausgeber bearbeiten' : 'Autor bearbeiten') 
            : (documentType === 'edited_book' || documentType === 'conference' ? 'Herausgeber hinzufügen' : 'Autor hinzufügen')}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              autoFocus
              margin="dense"
              label="Name"
              fullWidth
              variant="outlined"
              value={currentAuthor.name || ''}
              onChange={(e) => updateCurrentAuthor('name', e.target.value)}
              placeholder="Nachname, Vorname"
              helperText="Format: Nachname, Vorname"
            />
            <TextField
              margin="dense"
              label="ORCID (optional)"
              fullWidth
              variant="outlined"
              value={currentAuthor.orcid || ''}
              onChange={(e) => updateCurrentAuthor('orcid', e.target.value)}
              placeholder="0000-0000-0000-0000"
              helperText="Falls vorhanden, gib die ORCID-ID des Autors ein"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleAuthorDialogClose}>Abbrechen</Button>
          <Button onClick={saveAuthor} variant="contained">Speichern</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

/**
 * Extrahiert den wahrscheinlichen Dokumenttyp aus Metadaten
 * 
 * @param {Object} metadata - Die abgefragten Metadaten
 * @returns {string} - Der vermutete Dokumenttyp
 */
export const detectDocumentType = (metadata) => {
  if (!metadata) return 'other';
  
  // DOI vorhanden und beginnt mit 10.
  if (metadata.doi && metadata.doi.startsWith('10.')) {
    // Zeitschriftenartikel prüfen
    if (metadata.journal || metadata.issn) {
      return 'article';
    }
    
    // Konferenzbeitrag prüfen
    if (metadata.conference || (metadata.publisher && metadata.title && metadata.title.toLowerCase().includes('proceedings'))) {
      return 'conference';
    }
  }
  
  // ISBN prüfen für Bücher
  if (metadata.isbn) {
    // Herausgegebenes Buch vs. Monographie
    if (metadata.editors && metadata.editors.length > 0) {
      return 'edited_book';
    } else {
      return 'book';
    }
  }
  
  // Hochschulschrift prüfen
  if (metadata.thesisType || (metadata.title && 
      (metadata.title.toLowerCase().includes('dissertation') || 
       metadata.title.toLowerCase().includes('thesis') ||
       metadata.title.toLowerCase().includes('masterarbeit') ||
       metadata.title.toLowerCase().includes('bachelorarbeit')))) {
    return 'thesis';
  }
  
  // Zeitungsartikel prüfen
  if (metadata.newspaper || (metadata.publisher && 
      (metadata.publisher.toLowerCase().includes('zeitung') || 
       metadata.publisher.toLowerCase().includes('news')))) {
    return 'newspaper';
  }
  
  // Fallback: Wenn Journal vorhanden, dann Artikel
  if (metadata.journal) {
    return 'article';
  }
  
  // Fallback: Wenn Verlag vorhanden, dann Buch
  if (metadata.publisher) {
    return 'book';
  }
  
  return 'other';
};

export default MetadataForm;