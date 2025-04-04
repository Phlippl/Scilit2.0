// src/App.jsx - Progressive implementation
import React, { useState, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Container, 
  Button, 
  Box,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  useMediaQuery
} from '@mui/material'

// Icons - Import just what we need first
import MenuIcon from '@mui/icons-material/Menu'
import HomeIcon from '@mui/icons-material/Home'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'

// Create context for authentication
export const AuthContext = React.createContext();

// Simple component placeholders
const Home = () => (
  <Box sx={{ textAlign: 'center', mt: 4 }}>
    <Typography variant="h4" gutterBottom>
      Welcome to Academic Literature Assistant
    </Typography>
    <Typography variant="body1" paragraph>
      Upload academic papers, analyze them, and query your literature database.
    </Typography>
    <Button variant="contained" color="primary" href="/login">
      Get Started
    </Button>
  </Box>
);

const SimplePlaceholder = ({ name }) => (
  <Box sx={{ p: 4, textAlign: 'center' }}>
    <Typography variant="h5">{name} Page</Typography>
    <Typography variant="body1">This is a placeholder for the {name} component.</Typography>
  </Box>
);

// Lazy-loaded components
const LazyLogin = React.lazy(() => import('./components/Login'));
const LazyRegister = React.lazy(() => import('./components/Register'));
// We'll uncomment these as we confirm the app works
// const LazyDashboard = React.lazy(() => import('./components/Dashboard'));
// const LazyPDFUploader = React.lazy(() => import('./components/PDFUploader'));
// const LazyQueryInterface = React.lazy(() => import('./components/QueryInterface'));

function App() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const isMobile = useMediaQuery('(max-width:600px)');

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
    typography: {
      fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    },
  });

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const handleLogin = (userData) => {
    setIsAuthenticated(true);
    setUser(userData);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setUser(null);
  };

  const drawer = (
    <Box sx={{ width: 250 }} role="presentation" onClick={handleDrawerToggle}>
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography variant="h6" component="div">
          Literature Manager
        </Typography>
      </Box>
      <Divider />
      <List>
        <ListItem button component="a" href="/">
          <ListItemIcon>
            <HomeIcon />
          </ListItemIcon>
          <ListItemText primary="Home" />
        </ListItem>
        
        {isAuthenticated ? (
          <>
            <ListItem button component="a" href="/dashboard">
              <ListItemIcon>
                <AccountCircleIcon />
              </ListItemIcon>
              <ListItemText primary="Dashboard" />
            </ListItem>
          </>
        ) : (
          <>
            <ListItem button component="a" href="/login">
              <ListItemIcon>
                <AccountCircleIcon />
              </ListItemIcon>
              <ListItemText primary="Login" />
            </ListItem>
            <ListItem button component="a" href="/register">
              <ListItemIcon>
                <AccountCircleIcon />
              </ListItemIcon>
              <ListItemText primary="Register" />
            </ListItem>
          </>
        )}
      </List>
    </Box>
  );

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, handleLogin, handleLogout }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <AppBar position="sticky">
            <Toolbar>
              <IconButton
                color="inherit"
                aria-label="open drawer"
                edge="start"
                onClick={handleDrawerToggle}
                sx={{ mr: 2 }}
              >
                <MenuIcon />
              </IconButton>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                Academic Literature Assistant
              </Typography>
              {isAuthenticated ? (
                <>
                  <Typography variant="body1" sx={{ mr: 2 }}>
                    {user?.name || 'User'}
                  </Typography>
                  <Button color="inherit" onClick={handleLogout}>Logout</Button>
                </>
              ) : (
                <>
                  <Button color="inherit" href="/login">Login</Button>
                  <Button color="inherit" href="/register">Register</Button>
                </>
              )}
            </Toolbar>
          </AppBar>
          
          <Drawer
            anchor="left"
            open={drawerOpen}
            onClose={handleDrawerToggle}
          >
            {drawer}
          </Drawer>
          
          <Container component="main" sx={{ flexGrow: 1, py: 4 }}>
            <Routes>
              <Route path="/" element={<Home />} />
              
              <Route path="/login" element={
                <Suspense fallback={<SimplePlaceholder name="Login" />}>
                  {isAuthenticated ? <Navigate to="/dashboard" /> : <LazyLogin />}
                </Suspense>
              } />
              
              <Route path="/register" element={
                <Suspense fallback={<SimplePlaceholder name="Register" />}>
                  {isAuthenticated ? <Navigate to="/dashboard" /> : <LazyRegister />}
                </Suspense>
              } />
              
              <Route path="/dashboard" element={
                isAuthenticated ? 
                <SimplePlaceholder name="Dashboard" /> : 
                <Navigate to="/login" />
              } />
              
              <Route path="/upload" element={
                isAuthenticated ? 
                <SimplePlaceholder name="PDF Uploader" /> : 
                <Navigate to="/login" />
              } />
              
              <Route path="/query" element={
                isAuthenticated ? 
                <SimplePlaceholder name="Query Interface" /> : 
                <Navigate to="/login" />
              } />
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