import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import pugPlugin from 'vite-plugin-pug'
import prefixer from 'postcss-prefix-selector'

import tailwindcss from '@tailwindcss/vite'

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
  css: {
    postcss: {
      plugins: [
        // Scope ONLY the woven-canvas stylesheet so its ".menu" (and other
        // generic classes) can't leak globally and break DaisyUI components.
        //
        // Match the WHOLE package, not one exact filename: in dev Vite resolves
        // the file to e.g. `@woven-canvas/vue/dist/style.css` (and may append a
        // `?v=<hash>` query or serve it via `/@fs/`). The previous pattern only
        // matched `@woven-canvas/vue/style.css`, so it silently never fired in dev.
        prefixer({
          includeFiles: [/@woven-canvas[\\/]vue[\\/]/],
          prefix: '.woven-canvas-scope',
          transform(prefix, selector, prefixedSelector) {
            // Never rewrite document-level or keyframe selectors
            if (/^(html|body|\*|:root)$/.test(selector)) return selector
            if (/^(from|to|\d+%|0%)$/.test(selector)) return selector
            return prefixedSelector
          }
        })
      ]
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