import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    https:
      process.env.VITE_USE_HTTPS === 'true'
        ? {
            key: fs.readFileSync(path.resolve(__dirname, 'certs/server.key')),
            cert: fs.readFileSync(path.resolve(__dirname, 'certs/server.crt')),
          }
        : undefined,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        secure: false, // Accept self-signed certificates from backend if using HTTPS
      },
    },
  },
})
