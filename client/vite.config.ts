import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import pugPlugin from "vite-plugin-pug"

import tailwindcss from '@tailwindcss/vite';

const {
  DEBUG,
} = process.env

const options = { pretty: true } // FIXME: pug pretty is deprecated!
const locals = { }

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    allowedHosts: true,
    host: '0.0.0.0',
    watch: DEBUG ? { ignored: ["**/.codx/**"] } : null
  },
  plugins: [
    tailwindcss(),
    vue(),
    vueJsx(),
    pugPlugin(options, locals),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'esnext'
    }
  },
  build: {
    outDir: './dist',
    minify: false,
    emptyOutDir: true, // also necessary
    target: "esnext"
  }
})
