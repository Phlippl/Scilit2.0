// src/components/common/Navbar.jsx
import React, { useState } from 'react';
import { useNavigate, useLocation, Link as RouterLink } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Avatar,
  Menu,
  MenuItem,
  Tooltip,
  useMediaQuery,
  useTheme
} from '@mui/material';

// Icons
import MenuIcon from '@mui/icons-material/Menu';
import HomeIcon from '@mui/icons-material/Home';
import DashboardIcon from '@mui/icons-material/Dashboard';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import SearchIcon from '@mui/icons-material/Search';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import BookIcon from '@mui/icons-material/Book';

// Hooks
import { useAuth } from '../../hooks/useAuth';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  // State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  
  // Handler
  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };
  
  const handleUserMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleUserMenuClose = () => {
    setAnchorEl(null);
  };
  
  const handleLogout = () => {
    logout();
    handleUserMenuClose();
    setDrawerOpen(false);
    navigate('/login');
  };
  
  const handleNavigation = (path) => {
    navigate(path);
    setDrawerOpen(false);
  };
  
  // Prüfen, ob ein Menüpunkt aktiv ist
  const isActive = (path) => {
    return location.pathname === path;
  };
  
  // Menüeinträge
  const menuItems = [
    { 
      text: 'Home', 
      path: '/', 
      icon: <HomeIcon />, 
      requiredAuth: false 
    },
    { 
      text: 'Dashboard', 
      path: '/dashboard', 
      icon: <DashboardIcon />, 
      requiredAuth: true 
    },
    { 
      text: 'Publikation hochladen', 
      path: '/upload', 
      icon: <UploadFileIcon />, 
      requiredAuth: true 
    },
    { 
      text: 'Literatur abfragen', 
      path: '/query', 
      icon: <SearchIcon />, 
      requiredAuth: true 
    }
  ];
  
  // Drawer-Inhalt
  const drawer = (
    <Box sx={{ width: 250 }} role="presentation">
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <BookIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
        <Typography variant="h6" component="div">
          SciLit2.0
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Wissenschaftliche Literaturverwaltung
        </Typography>
      </Box>
      <Divider />
      <List>
        {menuItems.map((item) => (
          (!item.requiredAuth || isAuthenticated) && (
            <ListItem 
              button 
              key={item.text}
              onClick={() => handleNavigation(item.path)}
              selected={isActive(item.path)}
              sx={{
                '&.Mui-selected': {
                  backgroundColor: 'rgba(25, 118, 210, 0.08)',
                  '&:hover': {
                    backgroundColor: 'rgba(25, 118, 210, 0.12)',
                  },
                },
              }}
            >
              <ListItemIcon>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          )
        ))}
      </List>
      <Divider />
      {isAuthenticated ? (
        <List>
          <ListItem button onClick={handleLogout}>
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="Abmelden" />
          </ListItem>
        </List>
      ) : (
        <List>
          <ListItem button onClick={() => handleNavigation('/login')}>
            <ListItemIcon>
              <AccountCircleIcon />
            </ListItemIcon>
            <ListItemText primary="Anmelden" />
          </ListItem>
          <ListItem button onClick={() => handleNavigation('/register')}>
            <ListItemIcon>
              <AccountCircleIcon />
            </ListItemIcon>
            <ListItemText primary="Registrieren" />
          </ListItem>
        </List>
      )}
    </Box>
  );
  
  return (
    <>
      <AppBar position="sticky">
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="Menü öffnen"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          
          <Typography variant="h6" component={RouterLink} to="/" sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center' }}>
            <BookIcon sx={{ mr: 1 }} />
            SciLit2.0
          </Typography>
          
          {/* Desktop-Navigation */}
          {!isMobile && (
            <Box sx={{ display: 'flex' }}>
              {menuItems.map((item) => (
                (!item.requiredAuth || isAuthenticated) && (
                  <Button 
                    key={item.text}
                    color="inherit" 
                    startIcon={item.icon}
                    component={RouterLink}
                    to={item.path}
                    sx={{ 
                      mx: 0.5,
                      ...(isActive(item.path) && {
                        backgroundColor: 'rgba(255, 255, 255, 0.12)',
                      }),
                    }}
                  >
                    {item.text}
                  </Button>
                )
              ))}
            </Box>
          )}
          
          {/* Benutzer-Menü */}
          {isAuthenticated ? (
            <Box sx={{ ml: 2 }}>
              <Tooltip title="Benutzermenü öffnen">
                <IconButton onClick={handleUserMenuOpen} color="inherit">
                  <Avatar 
                    sx={{ 
                      width: 32, 
                      height: 32, 
                      bgcolor: 'secondary.main',
                      fontSize: '0.875rem',
                    }}
                  >
                    {user?.name?.charAt(0) || 'U'}
                  </Avatar>
                </IconButton>
              </Tooltip>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleUserMenuClose}
                keepMounted
              >
                <MenuItem disabled>
                  <Typography variant="body2">
                    Angemeldet als <strong>{user?.name || 'Benutzer'}</strong>
                  </Typography>
                </MenuItem>
                <Divider />
                <MenuItem onClick={handleLogout}>
                  <ListItemIcon>
                    <LogoutIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText>Abmelden</ListItemText>
                </MenuItem>
              </Menu>
            </Box>
          ) : (
            <Box>
              <Button color="inherit" component={RouterLink} to="/login">Anmelden</Button>
              {!isMobile && (
                <Button color="inherit" component={RouterLink} to="/register">Registrieren</Button>
              )}
            </Box>
          )}
        </Toolbar>
      </AppBar>
      
      {/* Drawer für Mobile Navigation */}
      <Drawer
        variant="temporary"
        open={drawerOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Bessere Performance auf Mobilgeräten
        }}
      >
        {drawer}
      </Drawer>
    </>
  );
};

export default Navbar;