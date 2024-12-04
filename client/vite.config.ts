import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'

const {
  API_PORT,
  NOTEBOOKS_URL,
  CODER_PORT,
  NOVNC_PORT,
  FILEBROWSER_PORT
} = process.env
const apiUrl = `http://0.0.0.0:${API_PORT}`
const coderUrl = `http://0.0.0.0:${CODER_PORT}`
const noVNCUrl = `http://0.0.0.0:${NOVNC_PORT}`
const filebrowserUrl = `http://0.0.0.0:${FILEBROWSER_PORT}/filebrowser`

console.log("filebrowserUrl", filebrowserUrl)
// https://vitejs.dev/config/
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: apiUrl,
        changeOrigin: true,
      },
      '/socket.io': {
        target: apiUrl,
        changeOrigin: true,
        ws: true,
      },
      '/filebrowser': {
        target: filebrowserUrl,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/filebrowser/, ''),
      },
      '/coder': {
        target: coderUrl,
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/coder/, ''),
      },
      '/novnc': {
        target: noVNCUrl,
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/novnc/, ''),
      },
      '^/stable.*': {
        target: coderUrl,
        changeOrigin: true,
        ws: true,
      },
      '/notebooks': {
        target: NOTEBOOKS_URL,
        changeOrigin: false,
        ws: true,
      }
    }
  },
  plugins: [
    vue(),
    vueJsx(),
    
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
