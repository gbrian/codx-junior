<script setup>
import CodeViewer from '../CodeViewer.vue';
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

    <!-- Editor -->
    <div class="grow min-h-0 overflow-hidden" v-else>
      <CodeViewer class="h-full overflow-auto mb-20 p-2"
          :close="true"
          :code="content"
          :file="filePath"
          :diffOption="false"
          :finished="loaded"
          @close="$emit('close')"
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
      error: null
    }
  },
  computed: {
    fileName() {
      return this.filePath?.split('/').reverse()[0] || ''
    },
    isDirty() {
      return this.content !== this.originalContent
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
      try {
        const api = this.chatProject?.$api || this.$storex.api
        const result = await api.files.read(this.filePath)
        // API may return { page_content } or a plain string
        this.content = result?.content ?? ''
        this.originalContent = this.content
      } catch (err) {
        this.error = `Could not load file: ${err?.message || err}`
      } finally {
        this.loaded = true
      }
    },

    onContentChange(value) {
      this.content = value
    },

    async saveFile() {
      if (!this.isDirty) return
      try {
        const api = this.chatProject?.$api || this.$storex.api
        await api.files.write(this.filePath, this.content)
        this.originalContent = this.content
        this.$emit('saved', { file: this.filePath, content: this.content })
        this.$ui?.addNotification?.({ text: `Saved: ${this.fileName}` })
      } catch (err) {
        this.$ui?.addNotification?.({ text: `Error saving: ${err?.message || err}`, type: 'error' })
      }
    }
  }
}
</script>