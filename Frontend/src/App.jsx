// Frontend/src/App.jsx
import React, { useState } from 'react'
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

// Icons
import MenuIcon from '@mui/icons-material/Menu'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import SearchIcon from '@mui/icons-material/Search'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import HomeIcon from '@mui/icons-material/Home'
import LogoutIcon from '@mui/icons-material/Logout'

// Components
import PDFUploader from './components/PDFUploader'
import QueryInterface from './components/QueryInterface'
import Login from './components/Login'
import Register from './components/Register'
import Dashboard from './components/Dashboard'

// Create context for authentication
export const AuthContext = React.createContext();

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
            <ListItem button component="a" href="/upload">
              <ListItemIcon>
                <UploadFileIcon />
              </ListItemIcon>
              <ListItemText primary="Upload Paper" />
            </ListItem>
            <ListItem button component="a" href="/query">
              <ListItemIcon>
                <SearchIcon />
              </ListItemIcon>
              <ListItemText primary="Query Literature" />
            </ListItem>
            <ListItem button onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon />
              </ListItemIcon>
              <ListItemText primary="Logout" />
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
              <Route path="/" element={
                <Box sx={{ textAlign: 'center', mt: 4 }}>
                  <Typography variant="h4" gutterBottom>
                    Welcome to Academic Literature Assistant
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Upload academic papers, analyze them, and query your literature database.
                  </Typography>
                  {isAuthenticated ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 4 }}>
                      <Button variant="contained" href="/upload" startIcon={<UploadFileIcon />}>
                        Upload Paper
                      </Button>
                      <Button variant="outlined" href="/query" startIcon={<SearchIcon />}>
                        Query Literature
                      </Button>
                    </Box>
                  ) : (
                    <Button variant="contained" href="/login" sx={{ mt: 2 }}>
                      Get Started
                    </Button>
                  )}
                </Box>
              } />
              
              <Route path="/login" element={
                isAuthenticated ? <Navigate to="/dashboard" /> : <Login />
              } />
              
              <Route path="/register" element={
                isAuthenticated ? <Navigate to="/dashboard" /> : <Register />
              } />
              
              <Route path="/dashboard" element={
                isAuthenticated ? <Dashboard /> : <Navigate to="/login" />
              } />
              
              <Route path="/upload" element={
                isAuthenticated ? <PDFUploader /> : <Navigate to="/login" />
              } />
              
              <Route path="/query" element={
                isAuthenticated ? <QueryInterface /> : <Navigate to="/login" />
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