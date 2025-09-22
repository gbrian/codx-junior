import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import pugPlugin from "vite-plugin-pug"

const {
  CODX_JUNIOR_API_PORT,
  NOTEBOOKS_URL,
  CODX_JUNIOR_CODER_PORT,
  CODX_JUNIOR_NOVNC_PORT,
  CODX_JUNIOR_API_URL,
  CODX_JUNIOR_AUTOGEN_STUDIO_PORT,
  CODX_JUNIOR_AUTOGEN_PREFIX_PATH_VALUE
} = process.env
const apiUrl = CODX_JUNIOR_API_URL || `http://0.0.0.0:${CODX_JUNIOR_API_PORT}`
const coderUrl = `http://0.0.0.0:${CODX_JUNIOR_CODER_PORT}`
const noVNCUrl = `http://localhost:${CODX_JUNIOR_NOVNC_PORT}`
const autogenStudio = `http://0.0.0.0:${CODX_JUNIOR_AUTOGEN_STUDIO_PORT}`

const proxy = {
  '/api': {
    target: apiUrl,
    changeOrigin: true,
  },
  '/api/socket.io': {
    target: apiUrl,
    changeOrigin: true,
    ws: true,
  },
  '/coder': {
    target: coderUrl,
    changeOrigin: true,
    ws: true,
    rewrite: (path) => path.replace(/^\/coder/, ''),
  },
  ['/' + CODX_JUNIOR_AUTOGEN_PREFIX_PATH_VALUE]: {
    target: autogenStudio,
    changeOrigin: true,
    ws: true,
  },
  '/novnc': {
    target: noVNCUrl,
    changeOrigin: true,
    ws: true,
    rewrite: (path) => path.replace(/^\/novnc/, ''),
  },
  '/vnc': {
    target: noVNCUrl,
    changeOrigin: true,
    ws: true,
  },
  '/websockify': {
    target: noVNCUrl,
    changeOrigin: true,
    ws: true,
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
  },
  '^/codx-workspace': {
      changeOrigin: true,
      // Just make Vite happy
      target: (req) => {
        const port = req.path.split("/").reverse()[0]
        const target = `http://0.0.0.0:${port}`
        console.log("codx-workspace", req.path, target)
        return target
      },
      rewrite(path: string) {
        const parts = path.split("/")
        return parts.slice(2).join("/")
      },
    },
}

console.log("proxy settings", proxy, process.env)

const options = { pretty: true } // FIXME: pug pretty is deprecated!
const locals = { }

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    allowedHosts: true,
    proxy,
    watch: {
      ignored: ["**/.codx/**"],
    }
  },
  define: {
    'process.env': {
      coderUrl,
      noVNCUrl
    }
  },
  plugins: [
    vue(),
    vueJsx(),
    pugPlugin(options, locals)
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
