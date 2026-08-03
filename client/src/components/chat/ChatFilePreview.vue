<script setup>
import CodeViewer from '../CodeViewer.vue'
</script>

<template>
  <div class="h-full flex flex-col min-h-0 bg-base-200 rounded border border-base-300">
    <!-- Loading state -->
    <div class="flex items-center justify-center grow" v-if="!loaded">
      <span class="loading loading-spinner loading-sm text-accent"></span>
      <span class="ml-2 text-xs opacity-60">Loading...</span>
    </div>

    <!-- Error state -->
    <div class="flex items-center justify-center grow" v-else-if="error">
      <div class="text-center text-error text-xs p-4">
        <i class="fa-solid fa-triangle-exclamation text-lg mb-2 block"></i>
        {{ error }}
      </div>
    </div>

    <!-- File editor -->
    <div class="grow min-h-0 overflow-hidden" v-else>
      <CodeViewer 
        class="h-full overflow-auto"
        :close="true"
        :code="content"
        :file="filePath"
        :language="fileLanguage"
        :diff-option="true"
        :finished="loaded"
        :show-code-opened="true"
        @close="$emit('close')"
        @save-file="onSaveFile"
        @message-change="onMessageChange"
      />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    filePath: { type: String, default: null },
    chatProject: { type: Object, default: null }
  },
  emits: ['close', 'saved'],
  data() {
    return {
      content: '',
      originalContent: '',
      loaded: false,
      error: null,
      isSaving: false
    }
  },
  computed: {
    fileName() {
      return this.filePath?.split('/').reverse()[0] || ''
    },
    fileLanguage() {
      const ext = this.filePath?.split('.').reverse()[0]
      return ext || 'markdown'
    },
    isDirty() {
      return this.content !== this.originalContent
    },
    api() {
      return this.chatProject?.$api || this.$storex.api
    }
  },
  watch: {
    filePath: {
      immediate: true,
      handler(val) {
        if (val) this.loadFile()
      }
    }
  },
  methods: {
    async loadFile() {
      if (!this.filePath) return
      this.error = null
      this.loaded = false
      try {
        const result = await this.api.files.read(this.filePath)
        this.content = result?.content ?? ''
        this.originalContent = this.content
      } catch (err) {
        this.error = `Could not load file: ${err?.message || 'Unknown error'}`
        console.error('Error loading file:', err)
      } finally {
        this.loaded = true
      }
    },

    async onSaveFile({ file, content }) {
      if (!file || !content) return
      await this.saveFile(content)
    },

    async saveFile(newContent) {
      if (this.isSaving) return
      this.isSaving = true
      try {
        await this.api.files.write(this.filePath, newContent)
        this.originalContent = newContent
        this.content = newContent
        this.$emit('saved', { file: this.filePath, content: newContent })
        this.$ui?.addNotification?.({ 
          text: `Saved: ${this.fileName}`,
          type: 'success'
        })
      } catch (err) {
        this.error = `Error saving: ${err?.message || 'Unknown error'}`
        this.$ui?.addNotification?.({ 
          text: `Error saving: ${err?.message || 'Unknown error'}`,
          type: 'error'
        })
        console.error('Error saving file:', err)
      } finally {
        this.isSaving = false
      }
    },

    onMessageChange({ orgContent, newContent }) {
      this.content = newContent
    }
  }
}
</script>