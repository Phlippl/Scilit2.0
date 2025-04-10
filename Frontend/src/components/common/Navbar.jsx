// src/components/common/Navbar.jsx
import React, { useState } from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Button, 
  IconButton, 
  Box, 
  Menu, 
  MenuItem, 
  Divider,
  Avatar,
  ListItemIcon,
  useMediaQuery,
  useTheme,
  Drawer,
  List,
  ListItem,
  ListItemText,
  Container
} from '@mui/material';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

// Icons
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import DashboardIcon from '@mui/icons-material/Dashboard';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import SearchIcon from '@mui/icons-material/Search';
import LogoutIcon from '@mui/icons-material/Logout';
import ArticleIcon from '@mui/icons-material/Article';

/**
 * Main navigation component
 */
const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  // State for user menu
  const [anchorEl, setAnchorEl] = useState(null);
  const menuOpen = Boolean(anchorEl);
  
  // State for mobile drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  
  // Handle user menu open
  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  // Handle user menu close
  const handleMenuClose = () => {
    setAnchorEl(null);
  };
  
  // Handle logout action
  const handleLogout = async () => {
    handleMenuClose();
    await logout();
    navigate('/');
  };
  
  // Handle mobile drawer toggle
  const toggleDrawer = (open) => (event) => {
    if (event.type === 'keydown' && (event.key === 'Tab' || event.key === 'Shift')) {
      return;
    }
    setDrawerOpen(open);
  };
  
  // Mobile navigation drawer content
  const drawerContent = (
    <Box
      sx={{ width: 250 }}
      role="presentation"
      onClick={toggleDrawer(false)}
      onKeyDown={toggleDrawer(false)}
    >
      <List>
        <ListItem 
          component={Link} 
          to="/"
          selected={location.pathname === '/'}
        >
          <ListItemIcon>
            <ArticleIcon />
          </ListItemIcon>
          <ListItemText primary="Home" />
        </ListItem>
        
        {isAuthenticated ? (
          <>
            <ListItem 
              component={Link} 
              to="/dashboard"
              selected={location.pathname === '/dashboard'}
            >
              <ListItemIcon>
                <DashboardIcon />
              </ListItemIcon>
              <ListItemText primary="Dashboard" />
            </ListItem>
            
            <ListItem 
              component={Link} 
              to="/upload"
              selected={location.pathname === '/upload'}
            >
              <ListItemIcon>
                <UploadFileIcon />
              </ListItemIcon>
              <ListItemText primary="Upload Document" />
            </ListItem>
            
            <ListItem 
              component={Link} 
              to="/query"
              selected={location.pathname === '/query'}
            >
              <ListItemIcon>
                <SearchIcon />
              </ListItemIcon>
              <ListItemText primary="Query Literature" />
            </ListItem>
            
            <Divider />
            
            <ListItem button onClick={handleLogout}>
              <ListItemIcon>
                <LogoutIcon />
              </ListItemIcon>
              <ListItemText primary="Logout" />
            </ListItem>
          </>
        ) : (
          <>
            <ListItem 
              component={Link} 
              to="/login"
              selected={location.pathname === '/login'}
            >
              <ListItemIcon>
                <AccountCircleIcon />
              </ListItemIcon>
              <ListItemText primary="Login" />
            </ListItem>
            
            <ListItem 
              component={Link} 
              to="/register"
              selected={location.pathname === '/register'}
            >
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
    <AppBar position="sticky" color="default" elevation={1}>
      <Container maxWidth="xl">
        <Toolbar disableGutters>
          {/* Mobile menu icon */}
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={toggleDrawer(true)}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}
          
          {/* App logo/title */}
          <Typography
            variant="h6"
            component={Link}
            to="/"
            sx={{
              mr: 2,
              fontWeight: 700,
              color: 'inherit',
              textDecoration: 'none',
              flexGrow: isMobile ? 1 : 0
            }}
          >
            SciLit2.0
          </Typography>
          
          {/* Desktop navigation links */}
          {!isMobile && (
            <Box sx={{ flexGrow: 1, display: 'flex' }}>
              {isAuthenticated && (
                <>
                  <Button
                    component={Link}
                    to="/dashboard"
                    color="inherit"
                    startIcon={<DashboardIcon />}
                    sx={{ mx: 1 }}
                  >
                    Dashboard
                  </Button>
                  
                  <Button
                    component={Link}
                    to="/upload"
                    color="inherit"
                    startIcon={<UploadFileIcon />}
                    sx={{ mx: 1 }}
                  >
                    Upload
                  </Button>
                  
                  <Button
                    component={Link}
                    to="/query"
                    color="inherit"
                    startIcon={<SearchIcon />}
                    sx={{ mx: 1 }}
                  >
                    Query
                  </Button>
                </>
              )}
            </Box>
          )}
          
          {/* Authentication buttons */}
          <Box sx={{ flexGrow: 0 }}>
            {isAuthenticated ? (
              <>
                <Button
                  onClick={handleMenuClick}
                  color="inherit"
                  endIcon={<AccountCircleIcon />}
                >
                  {user?.name || 'Account'}
                </Button>
                <Menu
                  anchorEl={anchorEl}
                  open={menuOpen}
                  onClose={handleMenuClose}
                  onClick={handleMenuClose}
                  transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                  anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                >
                  <MenuItem component={Link} to="/dashboard">
                    <ListItemIcon>
                      <DashboardIcon fontSize="small" />
                    </ListItemIcon>
                    Dashboard
                  </MenuItem>
                  <Divider />
                  <MenuItem onClick={handleLogout}>
                    <ListItemIcon>
                      <LogoutIcon fontSize="small" />
                    </ListItemIcon>
                    Logout
                  </MenuItem>
                </Menu>
              </>
            ) : (
              !isMobile && (
                <Box>
                  <Button 
                    color="inherit" 
                    component={Link} 
                    to="/login"
                    sx={{ mx: 1 }}
                  >
                    Login
                  </Button>
                  <Button 
                    variant="contained" 
                    color="primary" 
                    component={Link} 
                    to="/register"
                    sx={{ mx: 1 }}
                  >
                    Register
                  </Button>
                </Box>
              )
            )}
          </Box>
        </Toolbar>
      </Container>
      
      {/* Mobile navigation drawer */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={toggleDrawer(false)}
      >
        {drawerContent}
      </Drawer>
    </AppBar>
  );
};

export default Navbar;