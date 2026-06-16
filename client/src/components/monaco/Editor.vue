<script setup>
import { CodeEditor } from 'monaco-editor-vue3'
import { DiffEditor } from 'monaco-editor-vue3'
</script>

<template>
  <div class="flex flex-col h-96">
    <!-- Diff settings header -->
    <div class="flex gap-2 items-center p-1 bg-base-300 rounded-t" v-if="diff">
      <div class="tooltip" data-tip="Side by side">
        <button
          class="btn btn-xs"
          :class="localRenderSideBySide ? 'btn-info' : 'btn-ghost'"
          @click="setSideBySide(true)"
        >
          <i class="fa-solid fa-table-columns"></i>
        </button>
      </div>
      <div class="tooltip" data-tip="Inline">
        <button
          class="btn btn-xs"
          :class="!localRenderSideBySide ? 'btn-info' : 'btn-ghost'"
          @click="setSideBySide(false)"
        >
          <i class="fa-solid fa-bars"></i>
        </button>
      </div>
      <div class="tooltip" data-tip="Collapse unchanged">
        <button
          class="btn btn-xs"
          :class="localHideUnchanged ? 'btn-info' : 'btn-ghost'"
          @click="toggleHideUnchanged"
        >
          <i class="fa-solid fa-compress"></i>
        </button>
      </div>
      <div class="tooltip" data-tip="Ignore whitespace">
        <button
          class="btn btn-xs"
          :class="localIgnoreTrimWhitespace ? 'btn-info' : 'btn-ghost'"
          @click="toggleIgnoreWhitespace"
        >
          <i class="fa-solid fa-paragraph"></i>
        </button>
      </div>
      <div class="tooltip" data-tip="Show indicators">
        <button
          class="btn btn-xs"
          :class="localRenderIndicators ? 'btn-info' : 'btn-ghost'"
          @click="toggleRenderIndicators"
        >
          <i class="fa-solid fa-list-ol"></i>
        </button>
      </div>
      <div class="tooltip" data-tip="Resizable split">
        <button
          class="btn btn-xs"
          :class="localEnableSplitViewResizing ? 'btn-info' : 'btn-ghost'"
          @click="toggleSplitViewResizing"
        >
          <i class="fa-solid fa-left-right"></i>
        </button>
      </div>
    </div>

    <!-- Diff editor: re-rendered via key when options change -->
    <DiffEditor
      class="flex-1"
      :key="diffEditorKey"
      :original="originalCode"
      :value="modelValue"
      :language="resolvedLanguage"
      theme="vs-dark"
      :options="diffEditorOptions"
      @update:value="onDiffChange"
      v-if="diff"
    />
    <CodeEditor
      class="flex-1"
      v-model:value="code"
      :language="resolvedLanguage"
      theme="vs-dark"
      :options="editorOptions"
      v-else
    />
  </div>
</template>

<script>
// Map of file extensions to Monaco language identifiers
const EXTENSION_LANGUAGE_MAP = {
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  py: 'python',
  rb: 'ruby',
  java: 'java',
  kt: 'kotlin',
  kts: 'kotlin',
  cs: 'csharp',
  cpp: 'cpp',
  cc: 'cpp',
  cxx: 'cpp',
  c: 'c',
  h: 'c',
  hpp: 'cpp',
  go: 'go',
  rs: 'rust',
  php: 'php',
  swift: 'swift',
  scala: 'scala',
  r: 'r',
  dart: 'dart',
  lua: 'lua',
  pl: 'perl',
  pm: 'perl',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  ps1: 'powershell',
  psm1: 'powershell',
  html: 'html',
  htm: 'html',
  xml: 'xml',
  svg: 'xml',
  css: 'css',
  scss: 'scss',
  sass: 'scss',
  less: 'less',
  json: 'json',
  jsonc: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'ini',
  ini: 'ini',
  env: 'ini',
  md: 'markdown',
  mdx: 'markdown',
  sql: 'sql',
  graphql: 'graphql',
  gql: 'graphql',
  proto: 'proto',
  tf: 'hcl',
  hcl: 'hcl',
  vue: 'html',
  svelte: 'html',
  dockerfile: 'dockerfile',
  makefile: 'makefile',
  gradle: 'groovy',
  groovy: 'groovy',
  ex: 'elixir',
  exs: 'elixir',
  erl: 'erlang',
  hrl: 'erlang',
  clj: 'clojure',
  cljs: 'clojure',
  fs: 'fsharp',
  fsx: 'fsharp',
  vb: 'vb',
  asm: 'asm',
  s: 'asm',
}

export default {
  props: {
    diff: { type: Boolean, default: false },
    modelValue: { type: String, default: null },
    originalCode: { type: String, default: null },
    // Explicit Monaco language id (takes priority over fileName detection)
    language: { type: String, default: null },
    // File name or path used to auto-detect language from extension
    fileName: { type: String, default: null },
    renderSideBySide: { type: Boolean, default: true },
    hideUnchanged: { type: Boolean, default: false },
    ignoreTrimWhitespace: { type: Boolean, default: true },
    renderIndicators: { type: Boolean, default: true },
    enableSplitViewResizing: { type: Boolean, default: true },
  },
  emits: ['update:modelValue'],
  data() {
    return {
      localRenderSideBySide: this.renderSideBySide,
      localHideUnchanged: this.hideUnchanged,
      localIgnoreTrimWhitespace: this.ignoreTrimWhitespace,
      localRenderIndicators: this.renderIndicators,
      localEnableSplitViewResizing: this.enableSplitViewResizing,
      diffEditorKey: 0,
      editorOptions: {
        fontSize: 14,
        minimap: { enabled: true },
        automaticLayout: true,
        lineNumbers: 'on'
      }
    }
  },
  computed: {
    code: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    },

    // Resolve language: explicit prop > detected from fileName extension > plaintext
    resolvedLanguage() {
      if (this.language) return this.language
      if (this.fileName) {
        const ext = this.fileName.split('.').pop()?.toLowerCase()
        return EXTENSION_LANGUAGE_MAP[ext] || 'plaintext'
      }
      return 'plaintext'
    },

    diffEditorOptions() {
      return {
        fontSize: 14,
        automaticLayout: true,
        readOnly: false,
        renderSideBySide: this.localRenderSideBySide,
        ignoreTrimWhitespace: this.localIgnoreTrimWhitespace,
        renderIndicators: this.localRenderIndicators,
        enableSplitViewResizing: this.localEnableSplitViewResizing,
        hideUnchangedRegions: {
          enabled: this.localHideUnchanged,
          revealLineCount: 3,
          minimumLineCount: 3,
          contextLineCount: 3,
        },
        minimap: { enabled: false }
      }
    }
  },
  methods: {
    // Force re-render of DiffEditor by bumping its key
    refreshDiffEditor() {
      this.diffEditorKey++
    },

    setSideBySide(value) {
      this.localRenderSideBySide = value
      this.refreshDiffEditor()
    },

    toggleHideUnchanged() {
      this.localHideUnchanged = !this.localHideUnchanged
      this.refreshDiffEditor()
    },

    toggleIgnoreWhitespace() {
      this.localIgnoreTrimWhitespace = !this.localIgnoreTrimWhitespace
      this.refreshDiffEditor()
    },

    toggleRenderIndicators() {
      this.localRenderIndicators = !this.localRenderIndicators
      this.refreshDiffEditor()
    },

    toggleSplitViewResizing() {
      this.localEnableSplitViewResizing = !this.localEnableSplitViewResizing
      this.refreshDiffEditor()
    },

    onDiffChange(value) {
      this.$emit('update:modelValue', value)
    }
  }
}
</script>