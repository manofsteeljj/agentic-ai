import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/upload': 'http://localhost:8000',
      '/chat':   'http://localhost:8000',
      '/reset':  'http://localhost:8000',
    },
  },
})
