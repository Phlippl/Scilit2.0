// vite.config.js
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
  // Add specific exclusions for problematic dependencies
  optimizeDeps: {
    esbuildOptions: {
      // Node.js global to browser globalThis
      define: {
        global: 'globalThis',
      },
    },
  },
  server: {
    open: true,
    // Helpful for debugging
    hmr: {
      overlay: true,
    },
    // Enable proxy for API requests - fixed URL
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
        // Fix double /api prefix issue by removing one
        rewrite: (path) => {
          return path.replace(/^\/api/, '');
        }
      },
    },
  },
  // Add specific build options that can help with debugging
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          mui: ['@mui/material', '@mui/icons-material'],
        }
      }
    }
  }
});