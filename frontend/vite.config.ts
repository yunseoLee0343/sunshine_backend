import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Strip /api/v1 prefix — backend routes are at root (e.g. /plants, /home)
        rewrite: (path) => path.replace(/^\/api\/v1/, ''),
      },
    },
  },
})
