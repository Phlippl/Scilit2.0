// src/components/pdf/upload/SettingsDialog.jsx
import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import ProcessingSettings from '../ProcessingSettings';

/**
 * Dialog component for configuring PDF processing settings
 * 
 * @param {Object} props - Component props
 * @param {boolean} props.open - Dialog open state
 * @param {Object} props.settings - Current settings values
 * @param {Function} props.onClose - Callback when dialog is closed
 * @param {Function} props.onChange - Callback when settings are changed
 */
const SettingsDialog = ({ open, settings, onClose, onChange }) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Verarbeitungseinstellungen</DialogTitle>
      <DialogContent>
        <ProcessingSettings 
          settings={settings}
          onChange={onChange}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Abbrechen</Button>
        <Button onClick={onClose} variant="contained">
          Einstellungen übernehmen
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SettingsDialog;