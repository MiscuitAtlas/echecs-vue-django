import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// En développement, Vite sert l'interface et transmet l'API et les WebSockets à Django (port 8000).
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0,
  },
  test: {
    environment: 'jsdom',
  },
})
