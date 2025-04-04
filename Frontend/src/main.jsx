import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import Home from './pages/HomePage.jsx';
import Dashboard from './pages/DashboardPage.jsx';
import Login from './pages/LoginPage.jsx';

const App = React.lazy(() => import('./App.jsx'));

const AppWithErrorHandling = () => (
  <React.Suspense fallback={<div>Loading application...</div>}>
    <App />
  </React.Suspense>
);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);