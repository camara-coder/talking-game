import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8008',
        changeOrigin: true,
        // Don't rewrite - backend expects /api prefix
      },
      '/ws': {
        target: 'ws://127.0.0.1:8008',
        ws: true,
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8008',
        changeOrigin: true,
      }
    }
  }
})
