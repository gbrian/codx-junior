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
    },
    // These libraries are now only reachable from lazily-loaded chunks. Listing
    // them keeps the dev-time pre-bundling deterministic instead of relying on
    // the (previously forced) entry-level `import 'highlight.js'`.
    include: [
      'highlight.js/lib/core',
      'markdown-it',
      'markdown-it-emoji',
      'vue-code-highlighter',
      'monaco-editor-vue3',
      '@git-diff-view/vue',
      '@git-diff-view/file'
    ]
  },
  build: {
    outDir: './dist',
    // `minify: false` shipped the unminified bundle: it was the single largest
    // contributor to the multi-MB initial payload measured in production.
    minify: 'esbuild',
    sourcemap: false,
    emptyOutDir: true, // also necessary
    target: "esnext",
    // The editor/highlighting chunks are intentionally large and on-demand.
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // Keep the multi-megabyte libraries in their own long-lived chunks:
        // they change rarely, are loaded on demand and stay cacheable.
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('monaco-editor')) return 'monaco'
          if (id.includes('@mermaid-js') || id.includes('/mermaid/')) return 'mermaid'
          if (id.includes('@git-diff-view') || id.includes('v-code-diff')) return 'diff-view'
          if (id.includes('highlight.js') || id.includes('lowlight') || id.includes('vue-code-highlighter')) return 'syntax-highlight'
        }
      }
    }
  }
})