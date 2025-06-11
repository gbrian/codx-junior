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
} = process.env
const apiUrl = CODX_JUNIOR_API_URL || `http://0.0.0.0:${CODX_JUNIOR_API_PORT}`
const coderUrl = `http://0.0.0.0:${CODX_JUNIOR_CODER_PORT}`
const noVNCUrl = `http://0.0.0.0:${CODX_JUNIOR_NOVNC_PORT}`

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
  '/__vite_dev_proxy__': {
      changeOrigin: true,

      // Just make Vite happy
      target: 'https://example.com',
      rewrite(path: string) {
        const proxyUrl = new URL(path, 'file:'),
          url = new URL(proxyUrl.searchParams.get('url'))
        return url.pathname + url.search
      },
      configure(proxy: any, options: any) {
        proxy.on('proxyReq', (proxyReq, req) => {
          const query = req['_parsedUrl']['query'],
            url = new URL(new URLSearchParams(query).get('url'))

          // Change target here
          options.target = url.origin
        })
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
