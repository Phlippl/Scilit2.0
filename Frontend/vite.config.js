// Frontend/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  optimizeDeps: {
    exclude: [], // Hier können Sie problematische Abhängigkeiten hinzufügen
  },
  server: {
    open: true,
    // Eventuell Proxy für Backend-Anfragen
    proxy: {
      '/api': {
        target: 'http://localhost:5000', // Ihr Backend-Server
        changeOrigin: true,
      },
    },
  },
});