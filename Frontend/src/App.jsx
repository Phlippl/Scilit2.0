// Frontend/src/App.jsx
import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Container, 
  Box, 
  Button,
  CssBaseline
} from '@mui/material';
import PDFUploader from './components/PDFUploader';
import QueryInterface from './components/QueryInterface';

// Placeholder components for future implementation
const Dashboard = () => (
  <Box sx={{ mt: 4 }}>
    <Typography variant="h4" gutterBottom>Dashboard</Typography>
    <Typography>Here you will see your uploaded documents and saved references.</Typography>
  </Box>
);

const Login = () => (
  <Box sx={{ mt: 4 }}>
    <Typography variant="h4" gutterBottom>Login</Typography>
    <Typography>Login form will be implemented here.</Typography>
  </Box>
);

const Register = () => (
  <Box sx={{ mt: 4 }}>
    <Typography variant="h4" gutterBottom>Register</Typography>
    <Typography>Registration form will be implemented here.</Typography>
  </Box>
);

function App() {
  return (
    <>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Academic Literature Assistant
          </Typography>
          <Button color="inherit" component={Link} to="/">Dashboard</Button>
          <Button color="inherit" component={Link} to="/upload">Upload</Button>
          <Button color="inherit" component={Link} to="/query">Query</Button>
          <Button color="inherit" component={Link} to="/login">Login</Button>
        </Toolbar>
      </AppBar>
      
      <Container maxWidth="lg">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<PDFUploader />} />
          <Route path="/query" element={<QueryInterface />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Routes>
      </Container>
    </>
  );
}

export default App;