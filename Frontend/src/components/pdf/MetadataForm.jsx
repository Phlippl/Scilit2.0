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
  FormHelperText
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import PersonIcon from '@mui/icons-material/Person';

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
  const documentType = metadata.type || 'other';
  
  /**
   * Konfigurationsobjekt für die dynamischen Felder basierend auf dem Dokumenttyp
   */
  const typeConfigs = {
    article: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'journal', label: 'Zeitschrift', gridWidth: 6 },
      { id: 'volume', label: 'Jahrgang', gridWidth: 3 },
      { id: 'issue', label: 'Heftnummer', gridWidth: 3 },
      { id: 'pages', label: 'Seiten von-bis', gridWidth: 3 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 3 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'publisher', label: 'Verlag', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    book: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'publisher', label: 'Verlag', gridWidth: 6 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 3 },
      { id: 'publisherLocation', label: 'Verlagsort', gridWidth: 3 },
      { id: 'edition', label: 'Auflage', gridWidth: 3 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'series', label: 'Reihentitel', gridWidth: 6 },
      { id: 'seriesNumber', label: 'Bandnr. der Reihe', gridWidth: 3 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    edited_book: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'publisher', label: 'Verlag', gridWidth: 6 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 3 },
      { id: 'publisherLocation', label: 'Verlagsort', gridWidth: 3 },
      { id: 'edition', label: 'Auflage', gridWidth: 3 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'series', label: 'Reihentitel', gridWidth: 6 },
      { id: 'seriesNumber', label: 'Bandnr. der Reihe', gridWidth: 3 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    conference: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'conference', label: 'Tagungsname', gridWidth: 6 },
      { id: 'conferenceLocation', label: 'Tagungsort', gridWidth: 6 },
      { id: 'conferenceDate', label: 'Veranstaltungsdatum', gridWidth: 6 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 3 },
      { id: 'publisherLocation', label: 'Verlagsort', gridWidth: 3 },
      { id: 'publisher', label: 'Verlag', gridWidth: 6 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    thesis: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'thesisType', label: 'Art der Schrift', gridWidth: 6 },
      { id: 'publicationDate', label: 'Datum / Jahr', type: 'date', gridWidth: 6 },
      { id: 'university', label: 'Hochschule', gridWidth: 6 },
      { id: 'department', label: 'Institut', gridWidth: 6 },
      { id: 'location', label: 'Hochschulort', gridWidth: 6 },
      { id: 'advisor', label: 'Betreuer', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    report: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'institution', label: 'Institution', gridWidth: 6 },
      { id: 'publicationDate', label: 'Datum / Jahr', type: 'date', gridWidth: 3 },
      { id: 'location', label: 'Erscheinungsort', gridWidth: 3 },
      { id: 'reportNumber', label: 'Nummer', gridWidth: 3 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    newspaper: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'newspaper', label: 'Zeitung', gridWidth: 6 },
      { id: 'publicationDate', label: 'Datum', type: 'date', gridWidth: 3 },
      { id: 'location', label: 'Ort', gridWidth: 3 },
      { id: 'edition', label: 'Ausgabe', gridWidth: 3 },
      { id: 'pages', label: 'Seiten von-bis', gridWidth: 3 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    website: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'url', label: 'Online-Adresse', gridWidth: 12 },
      { id: 'institution', label: 'Institution', gridWidth: 6 },
      { id: 'publicationDate', label: 'Jahr', type: 'date', gridWidth: 3 },
      { id: 'lastUpdated', label: 'Letzte Aktualisierung', type: 'date', gridWidth: 3 },
      { id: 'accessDate', label: 'Zuletzt geprüft am', type: 'date', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ],
    
    interview: [
      { id: 'title', label: 'Titel / Thema', required: true, gridWidth: 12 },
      { id: 'interviewer', label: 'Interviewer', gridWidth: 6 },
      { id: 'interviewee', label: 'Interviewte Person', gridWidth: 6 },
      { id: 'date', label: 'Datum', type: 'date', gridWidth: 3 },
      { id: 'duration', label: 'Länge', gridWidth: 3 },
      { id: 'location', label: 'Ort', gridWidth: 6 },
      { id: 'medium', label: 'Medium', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 }
    ],
    
    press: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'institution', label: 'Institution', gridWidth: 6 },
      { id: 'contactPerson', label: 'Kontaktperson', gridWidth: 6 },
      { id: 'contactAddress', label: 'Kontaktadresse', gridWidth: 6 },
      { id: 'date', label: 'Datum', type: 'date', gridWidth: 3 },
      { id: 'location', label: 'Ort', gridWidth: 3 },
      { id: 'embargo', label: 'Sperrfrist', gridWidth: 3 },
      { id: 'url', label: 'Online-Adresse', gridWidth: 6 },
      { id: 'accessDate', label: 'Zuletzt geprüft am', type: 'date', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 }
    ],
    
    // Fallback für unbekannte Dokumenttypen
    other: [
      { id: 'title', label: 'Titel', required: true, gridWidth: 12 },
      { id: 'subtitle', label: 'Untertitel', gridWidth: 12 },
      { id: 'publisher', label: 'Verlag', gridWidth: 6 },
      { id: 'journal', label: 'Zeitschrift', gridWidth: 6 },
      { id: 'publicationDate', label: 'Jahr/Datum', type: 'date', gridWidth: 3 },
      { id: 'edition', label: 'Auflage', gridWidth: 3 },
      { id: 'pages', label: 'Seiten von-bis', gridWidth: 3 },
      { id: 'isbn', label: 'ISBN', gridWidth: 6 },
      { id: 'doi', label: 'DOI', gridWidth: 6 },
      { id: 'url', label: 'Online-Adresse', gridWidth: 6 },
      { id: 'accessDate', label: 'Zuletzt geprüft am', type: 'date', gridWidth: 6 },
      { id: 'abstract', label: 'Abstract', multiline: true, rows: 4, gridWidth: 12 }
    ]
  };
  
  // Aktive Konfiguration für den aktuellen Dokumenttyp
  const activeConfig = typeConfigs[documentType] || typeConfigs.other;

  // Bei Änderungen der Metadaten alle Felder aktualisieren
  useEffect(() => {
    // Sammle alle Felder aus den Metadaten
    const fields = { ...metadata };
    setAllFields(fields);
  }, [metadata]);

  // Typ des Dokuments ändern
  const handleTypeChange = (event) => {
    // Statt nur den Typ zu ändern, behalten wir alle vorhandenen Metadaten
    onChange('type', event.target.value);
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
    <Box>
      <Grid container spacing={3}>
        {/* Dokumenttyp-Auswahl */}
        <Grid item xs={12}>
          <FormControl fullWidth>
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
        <Grid item xs={12}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="subtitle1">
                {documentType === 'edited_book' || documentType === 'conference' ? 'Herausgeber' : 'Autoren'}
              </Typography>
              <Button 
                startIcon={<AddIcon />} 
                size="small" 
                onClick={openAddAuthorDialog}
              >
                {documentType === 'edited_book' || documentType === 'conference' ? 'Herausgeber hinzufügen' : 'Autor hinzufügen'}
              </Button>
            </Box>
            
            {(!metadata.authors || metadata.authors.length === 0) ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', mb: 1 }}>
                {documentType === 'edited_book' || documentType === 'conference' 
                  ? 'Noch keine Herausgeber hinzugefügt' 
                  : 'Noch keine Autoren hinzugefügt'}
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

        {/* Dynamische Felder basierend auf dem Dokumenttyp */}
        {activeConfig.map((field) => (
          <Grid item xs={12} sm={field.gridWidth} key={field.id}>
            <TextField
              fullWidth
              label={field.label}
              type={field.type || 'text'}
              required={field.required}
              multiline={field.multiline}
              rows={field.rows}
              value={metadata[field.id] || ''}
              onChange={(e) => onChange(field.id, e.target.value)}
              variant="outlined"
              InputLabelProps={field.type === 'date' ? {
                shrink: true,
              } : undefined}
            />
          </Grid>
        ))}
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