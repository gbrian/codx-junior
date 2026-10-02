<script setup>
import { CodeEditor, DiffEditor } from 'monaco-editor-vue3'
import { EXTENSION_LANGUAGE_MAP } from '../../store'
</script>

<template>
  <div class="h-full">
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
      :key="diffEditorKey"
      :original="originalCode"
      :value="modelValue"
      :language="resolvedLanguage"
      theme="vs-dark"
      :options="diffEditorOptions"
      @update:value="onDiffChange"
      @editorWillMount="onEditorWillMount"
      @editorDidMount="onEditorDidMount('diff')"
      v-if="diff && isReady"
    />
    <CodeEditor
      v-model:value="code"
      :language="resolvedLanguage"
      theme="vs-dark"
      :options="editorOptions"
      @editorWillMount="onEditorWillMount"
      @editorDidMount="onEditorDidMount('code')"
      v-else-if="!diff && isReady"
    />
    <!-- Loading placeholder while Monaco initializes -->
    <div class="flex-1 min-h-64 flex items-center justify-center bg-base-200" v-else>
      <span class="loading loading-spinner loading-sm"></span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    diff: { type: Boolean, default: false },
    modelValue: { type: String, default: null },
    originalCode: { type: String, default: null },
    language: { type: String, default: null },
    fileName: { type: String, default: null },
    renderSideBySide: { type: Boolean, default: true },
    hideUnchanged: { type: Boolean, default: true },
    ignoreTrimWhitespace: { type: Boolean, default: true },
    renderIndicators: { type: Boolean, default: true },
    enableSplitViewResizing: { type: Boolean, default: true },
  },
  emits: ['update:modelValue', 'save'],
  data() {
    return {
      isReady: false,
      localRenderSideBySide: this.renderSideBySide,
      localHideUnchanged: this.hideUnchanged,
      localIgnoreTrimWhitespace: this.ignoreTrimWhitespace,
      localRenderIndicators: this.renderIndicators,
      localEnableSplitViewResizing: this.enableSplitViewResizing,
      diffEditorKey: 0,
      editorInstance: null,
      editorOptions: {
        fontSize: 14,
        minimap: { enabled: true },
        automaticLayout: true,
        lineNumbers: 'on'
      }
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.isReady = true
    })
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
    // Invoked before Monaco editor initializes
    onEditorWillMount() {
      // Placeholder for future initialization logic
    },

    // Invoked after Monaco editor mounts
    onEditorDidMount(editorType) {
      // Store editor reference for keyboard binding setup
      this.editorInstance = editorType
      this.setupSaveKeybinding()
    },

    // Setup Ctrl+S / Cmd+S to trigger save
    setupSaveKeybinding() {
      // Note: monaco-editor-vue3 doesn't expose editor directly
      // This intercepts the native keyboard event at component level
      this.$el.addEventListener('keydown', this.handleKeydown)
    },

    // Handle keyboard shortcuts
    handleKeydown(event) {
      const isSaveKey = (event.ctrlKey || event.metaKey) && event.key === 's'
      if (isSaveKey) {
        event.preventDefault()
        this.$emit('save')
      }
    },

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