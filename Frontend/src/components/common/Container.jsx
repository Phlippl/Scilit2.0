// src/components/common/Container.jsx
import React from 'react';
import { Box } from '@mui/material';

/**
 * Eine Container-Komponente, die die volle Breite der Seite nutzt
 * 
 * @param {Object} props - Die Komponenten-Props
 * @param {ReactNode} props.children - Die Kinder-Elemente
 * @param {Object} props.sx - Zusätzliche Styling-Props für den Container
 */
const FullWidthContainer = ({ children, sx = {}, ...props }) => {
  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: '100%',
        px: 0, // Kein horizontales Padding
        ...sx
      }}
      {...props}
    >
      {children}
    </Box>
  );
};

export default FullWidthContainer;