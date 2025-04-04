// src/App.jsx - Simplified version for debugging
import React, { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Container, 
  Button, 
  Box,
} from '@mui/material'

// Create context for authentication
export const AuthContext = React.createContext({
  isAuthenticated: false,
  user: null,
  handleLogin: () => {},
  handleLogout: () => {},
});

// Simple home component 
const Home = () => (
  <Box sx={{ textAlign: 'center', mt: 4 }}>
    <Typography variant="h4" gutterBottom>
      Welcome to Academic Literature Assistant
    </Typography>
    <Typography variant="body1" paragraph>
      Upload academic papers, analyze them, and query your literature database.
    </Typography>
    <Button variant="contained" color="primary">
      Get Started
    </Button>
  </Box>
);

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  const theme = createTheme({
    palette: {
      mode: 'light',
      primary: {
        main: '#1976d2',
      },
      secondary: {
        main: '#dc004e',
      },
    },
  });

  const handleLogin = (userData) => {
    setIsAuthenticated(true);
    setUser(userData);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setUser(null);
  };

  const authContextValue = {
    isAuthenticated,
    user,
    handleLogin,
    handleLogout
  };

  return (
    <AuthContext.Provider value={authContextValue}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <AppBar position="sticky">
            <Toolbar>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                Academic Literature Assistant
              </Typography>
              <Button color="inherit">Login</Button>
            </Toolbar>
          </AppBar>
          
          <Container component="main" sx={{ flexGrow: 1, py: 4 }}>
            <Routes>
              <Route path="/" element={<Home />} />
              {/* Add more routes as you confirm each component works */}
            </Routes>
          </Container>
          
          <Box component="footer" sx={{ p: 2, mt: 'auto', backgroundColor: 'rgba(0, 0, 0, 0.05)' }}>
            <Typography variant="body2" color="text.secondary" align="center">
              © {new Date().getFullYear()} Academic Literature Assistant
            </Typography>
          </Box>
        </Box>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}

export default App;