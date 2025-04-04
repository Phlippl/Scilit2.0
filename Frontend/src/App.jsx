import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Container } from '@mui/material';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import Upload from './pages/Upload';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import PDFUploader from './components/PDFUploader';
import './App.css';

// MUI Theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#1565c0', // Deep blue
    },
    secondary: {
      main: '#673ab7', // Deep purple
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: 'Roboto, "Helvetica Neue", Arial, sans-serif',
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <div className="app-container">
          <Navbar />
          <main className="main-content">
            <Container maxWidth="lg" sx={{ mt: 4, pb: 8 }}>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/uploader" element={<PDFUploader />} />
              </Routes>
            </Container>
          </main>
          <Footer />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
