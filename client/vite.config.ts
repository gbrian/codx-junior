import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'

const { API_URL, NOTEBOOKS_URL } = process.env
console.log("API_URL", API_URL)
// https://vitejs.dev/config/
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: API_URL,
        changeOrigin: true,
      },
      '/notebooks': {
        target: NOTEBOOKS_URL,
        changeOrigin: false,
        ws: true,
      },
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
