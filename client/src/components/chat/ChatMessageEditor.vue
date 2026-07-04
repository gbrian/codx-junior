<script setup>
import Editor from '@/components/monaco/Editor.vue'
</script>

<template>
  <div class="h-full flex flex-col gap-2 p-4 bg-base-100">
    
    <!-- Message info -->
    <div class="flex gap-4 text-xs text-base-content/60">
      <div class="flex items-center gap-2">
        <span class="font-semibold">Author:</span>
        <span>{{ message.user }}</span>
      </div>
      <div class="flex items-center gap-2">
        <span class="font-semibold">Updated:</span>
        <span>{{ formatDate(message.updated_at) }}</span>
      </div>
    </div>

    <!-- Markdown editor -->
    <div class="flex-1 min-h-0 rounded-md border border-base-300 overflow-hidden">
      <Editor
        v-model="editorContent"
        language="markdown"
        :fileName="message.doc_id + '.md'"
        class="h-full"
      />
    </div>

    <!-- Footer actions -->
    <div class="flex justify-between items-center gap-2">
      <div class="text-xs text-base-content/60">
        <span class="badge badge-sm">{{ characterCount }} characters</span>
      </div>
      <div class="flex gap-2">
        <button 
          class="btn btn-sm btn-outline" 
          @click="onDiscard"
        >
          Cancel
        </button>
        <button 
          class="btn btn-sm btn-primary" 
          @click="onSave"
          :disabled="!hasChanges"
        >
          <i class="fa-solid fa-floppy-disk"></i>
          Save
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import moment from 'moment'

export default {
  props: ['message'],
  emits: ['save', 'discard'],
  data() {
    return {
      editorContent: this.message?.content || '',
      originalContent: this.message?.content || ''
    }
  },
  computed: {
    hasChanges() {
      return this.editorContent !== this.originalContent
    },
    characterCount() {
      return this.editorContent.length
    }
  },
  methods: {
    formatDate(date) {
      return moment(date).format('DD/MMM HH:mm:ss')
    },
    onSave() {
      if (!this.hasChanges) return
      this.$emit('save', {
        doc_id: this.message.doc_id,
        content: this.editorContent
      })
    },
    onDiscard() {
      this.$emit('discard')
    }
  },
  watch: {
    message(newMessage) {
      if (newMessage) {
        this.editorContent = newMessage.content || ''
        this.originalContent = newMessage.content || ''
      }
    }
  }
}
</script>