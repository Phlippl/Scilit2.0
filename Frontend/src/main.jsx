// Frontend/src/App.jsx
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { CssBaseline, Container, Box, Typography } from '@mui/material'
import PDFUploader from './components/PDFUploader'
import QueryInterface from './components/QueryInterface'

function App() {
  return (
    <>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom align="center">
            Scientific Literature Assistant
          </Typography>
          
          <Routes>
            <Route path="/" element={<PDFUploader />} />
            <Route path="/query" element={<QueryInterface />} />
          </Routes>
        </Box>
      </Container>
    </>
  )
}

export default App