import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8800',
        changeOrigin: true,
      },
      // ACS API endpoints /{stack}/adminconfig/v2/*
      '^/[^/]+/adminconfig': {
        target: 'http://localhost:8800',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8800',
        changeOrigin: true,
      },
      '/docs': {
        target: 'http://localhost:8800',
        changeOrigin: true,
      },
      '/openapi.json': {
        target: 'http://localhost:8800',
        changeOrigin: true,
      },
    },
  },
})
