import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Assuming FastAPI runs on localhost:8000
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/factor': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/actions': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/dashboard': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/analytics': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/orgs': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/audit': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/credits': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/tier': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/order': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/payment': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
      '/kill-switch': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})