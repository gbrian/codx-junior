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
  USER_PORT_RANGE_START,
  USER_PORT_RANGE_END
} = process.env
const apiUrl = CODX_JUNIOR_API_URL || `http://0.0.0.0:${CODX_JUNIOR_API_PORT}`
const coderUrl = `http://0.0.0.0:${CODX_JUNIOR_CODER_PORT}`
const noVNCUrl = `http://localhost:${CODX_JUNIOR_NOVNC_PORT}`

const userPortStart = parseInt(USER_PORT_RANGE_START, 10)
const userPortEnd = parseInt(USER_PORT_RANGE_END, 10)

const userPortCount = userPortEnd - userPortStart

const userPorts = ...[new Array(userPortCount)].reduce((acc, v) => 
      ({ 
        ...acc, 
          [`/user-${userPortStart + v}`]: {
            target: `http://0.0.0.0:${userPortStart + v}`,
            changeOrigin: true,
            ws: true,
            rewrite: (path) => path.replace(/^\/user-[0-9]+/, ''),
          }
      }) , {})

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
  // User ports
  ...userPorts
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
      noVNCUrl,
      USER_PORT_RANGE_START,
      USER_PORT_RANGE_END
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
