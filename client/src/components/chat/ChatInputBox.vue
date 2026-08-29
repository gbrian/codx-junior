<script setup>
import ChatInputToolbar from './ChatInputToolbar.vue'
</script>

<template>
  <div class="flex flex-col gap-2 md:px-2 md:py-2 bg-base-100 rounded-md border border-base-300">
    <!-- Editor area -->
    <div class="relative">
      <textarea
        ref="editor"
        class="textarea textarea-bordered w-full min-h-24"
        placeholder="Type your message..."
        @keydown="$emit('keydown', $event)"
        @paste="$emit('paste', $event)"
        @drop="$emit('drop', $event)"
      ></textarea>
    </div>

    <!-- Toolbar with action buttons and selectors -->
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
  methods: {
    getEditorText() {
      return this.$refs.editor?.value || ''
    },
    setEditorText(text) {
      if (this.$refs.editor) {
        this.$refs.editor.value = text
      }
    },
    appendEditorText(text) {
      if (this.$refs.editor) {
        this.$refs.editor.value += text
      }
    },
    focusEditor() {
      this.$refs.editor?.focus()
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