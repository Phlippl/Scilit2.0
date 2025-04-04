// 1. Create a debug version of main.jsx to identify errors
// Save this as src/debug-main.jsx

import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

// Simple debug component to test if React is working
const DebugApp = () => {
  return (
    <div style={{ padding: '20px' }}>
      <h1>Debug Mode</h1>
      <p>If you can see this, React is working correctly.</p>
      <p>Check the console for any errors that might be occurring in your actual App component.</p>
    </div>
  )
}

// Try to render the minimal component
try {
  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <DebugApp />
    </React.StrictMode>,
  )
} catch (error) {
  console.error('Error rendering React application:', error)
  
  // Display error on page if React fails to render
  document.getElementById('root').innerHTML = `
    <div style="color: red; padding: 20px;">
      <h1>React Initialization Error</h1>
      <pre>${error.message}</pre>
      <p>Check console for more details</p>
    </div>
  `
}