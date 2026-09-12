import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In docker-compose, this dashboard and the FastAPI server run in separate
// containers, so 127.0.0.1 (this container's own loopback) can't reach it —
// docker-compose.yml sets API_PROXY_TARGET=http://server:8000 for that case.
const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})
