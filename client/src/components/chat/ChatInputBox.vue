<script setup>
import ChatInputToolbar from './ChatInputToolbar.vue'
</script>

<template>
  <div
    class="notion-composer flex flex-col transition-all duration-200"
    :class="[
      isDraggingOver
        ? 'bg-primary/10 ring-2 ring-primary rounded-xl'
        : isFocused
          ? 'bg-base-100 ring-1 ring-base-300 shadow-md rounded-xl'
          : 'bg-base-200/60 rounded-xl hover:bg-base-200 hover:ring-1 hover:ring-base-300'
    ]"
    @dragover.prevent="isDraggingOver = true"
    @dragleave.prevent="isDraggingOver = false"
    @drop.prevent="onDrop"        
  >
    <!-- Textarea — ghost style, expands naturally -->
    <div class="relative px-3 pt-3">
      <textarea
        ref="editor"
        rows="3"
        class="w-full bg-transparent resize-none outline-none text-sm text-base-content placeholder:text-base-content/30 leading-relaxed"
        :placeholder="isEditing ? 'Edit your message...' : 'Write something, or @ to mention a file...'"
        @keydown="$emit('keydown', $event)"
        @paste="$emit('paste', $event)"
        @focus="isFocused = true"
        @blur="isFocused = false"
        @input="autoResize"
      ></textarea>
    </div>

    <!-- Divider -->
    <div class="mx-3 border-t border-base-300/50 mt-1"></div>

    <!-- Toolbar -->
    <ChatInputToolbar
      :waiting="waiting"
      :is-editing="isEditing"
      :is-voice-session="isVoiceSession"
      :searching="searching"
      :read-only="readOnly"
      :selected-model="selectedModel"
      :ai-models="aiModels"
      :images="images"
      :profiles="profiles"
      :selected-profiles="selectedProfiles"
      :voice-language-label="voiceLanguageLabel"
      @send="$emit('send')"
      @add-message="$emit('add-message')"
      @search-message="$emit('search-message')"
      @cancel-edit="$emit('cancel-edit')"
      @model-changed="$emit('model-changed', $event)"
      @toggle-search="$emit('toggle-search')"
      @hide-all="$emit('hide-all')"
      @attach-files="$emit('attach-files')"
      @test-project="$emit('test-project')"
      @toggle-voice="$emit('toggle-voice')"
      @remove-image="$emit('remove-image', $event)"
      @preview-image="$emit('preview-image', $event)"
      @profiles-selected="$emit('profiles-selected', $event)"
    />
  </div>
</template>

<script>
export default {
  props: {
    waiting: Boolean,
    isEditing: Boolean,
    isVoiceSession: Boolean,
    searching: Boolean,
    readOnly: Boolean,
    selectedModel: String,
    aiModels: { type: Array, default: () => [] },
    images: { type: Array, default: () => [] },
    voiceLanguageLabel: String,
    profiles: { type: Array, default: () => [] },
    selectedProfiles: { type: Array, default: () => [] }
  },
  emits: [
    'send', 'add-message', 'search-message', 'cancel-edit', 'model-changed',
    'toggle-search', 'hide-all', 'attach-files', 'test-project',
    'toggle-voice', 'remove-image', 'preview-image', 'keydown', 'paste',
    'drop', 'profiles-selected'
  ],
  data() {
    return {
      isFocused: false,
      isDraggingOver: false
    }
  },
  methods: {
    onDrop(event) {
      this.isDraggingOver = false
      this.$emit('drop', event)
    },
    getEditorText() {
      return this.$refs.editor?.value || ''
    },
    setEditorText(text) {
      if (this.$refs.editor) {
        this.$refs.editor.value = text
        this.autoResize()
      }
    },
    appendEditorText(text) {
      if (this.$refs.editor) {
        this.$refs.editor.value += text
        this.autoResize()
      }
    },
    focusEditor() {
      this.$refs.editor?.focus()
    },
    autoResize() {
      const el = this.$refs.editor
      if (!el) return
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 320) + 'px'
    },
    getCaretWordInfo() {
      const textarea = this.$refs.editor
      if (!textarea) return {}
      const caretIndex = textarea.selectionStart
      const text = textarea.value
      let wordStart = caretIndex
      while (wordStart > 0 && /\S/.test(text[wordStart - 1])) {
        wordStart--
      }
      return {
        word: text.slice(wordStart, caretIndex),
        caretIndex
      }
    }
  },
  expose: [
    'getEditorText',
    'setEditorText',
    'appendEditorText',
    'focusEditor',
    'getCaretWordInfo'
  ]
}
</script>