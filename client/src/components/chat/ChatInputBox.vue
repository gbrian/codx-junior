<script setup>
import ChatInputToolbar from './ChatInputToolbar.vue'
import EmojiPicker from './EmojiPicker.vue'
import FindReplaceBox from './FindReplaceBox.vue'
</script>

<template>
  <div
    ref="inputContainer"
    class="notion-composer flex flex-col transition-all duration-200 text-sm md:text-base"
    :class="[
      isDraggingOver
        ? 'bg-primary/10 ring-2 ring-primary rounded-lg md:rounded-xl'
        : isFocused
          ? 'ring-1 ring-base-300 shadow-md rounded-lg md:rounded-xl'
          : 'border border-base-content/50 rounded-lg md:rounded-xl hover:bg-base-200 hover:ring-1 hover:ring-base-300'
    ]"
    @dragover.prevent="isDraggingOver = true"
    @dragleave.prevent="isDraggingOver = false"
    @drop.prevent="onDrop"        
  >
    <!-- ── Mobile collapsed pill ── -->
    <!-- .stop: the pill owns its own toggle, the document listener must not duplicate it -->
    <div
      v-if="isMobile && collapsed"
      class="flex items-center gap-3 px-4 py-3 cursor-pointer"
      @click.stop="$emit('toggle-collapsed')"
    >
      <i class="fa-solid fa-pen text-base-content/40 text-sm shrink-0"></i>
      <span class="text-base-content/40 text-sm flex-1 truncate">Write a message...</span>
      <!-- Pending attachments / files indicator (previews are hidden while collapsed) -->
      <span
        v-if="attachmentCount || fileCount"
        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/20 text-primary text-xs font-medium shrink-0"
      >
        <i class="fa-solid fa-paperclip text-[10px]"></i>
        {{ (attachmentCount || 0) + (fileCount || 0) }}
      </span>
      <i class="fa-solid fa-chevron-up text-base-content/30 text-xs"></i>
    </div>

    <!-- ── Full input (desktop always visible; mobile only when not collapsed) ── -->
    <template v-if="!isMobile || !collapsed">
      <!-- Slot: extra content above the textarea (e.g. project selector) -->
      <div v-if="$slots['before-textarea']" class="px-2 md:px-3 pt-2 md:pt-3 pb-1">
        <slot name="before-textarea" />
      </div>

      <!-- Find/Replace Box -->
      <FindReplaceBox
        v-if="showFindReplace"
        :editor-text="getEditorText()"
        @close="showFindReplace = false"
        @find-replace="onFindReplace"
      />

      <!-- Emoji Picker Popup -->
      <EmojiPicker
        v-if="cursorWord.word?.startsWith(':')"
        class="px-2 md:px-3 py-2 md:py-2 border-b border-base-100/50"
        :emoji-name="cursorWord.word"
        @emoji="onEmojiSelected"
      />

      <!-- Textarea — ghost style, expands naturally -->
      <div class="relative px-2 md:px-3 pt-2 md:pt-3">
        <textarea
          ref="editor"
          rows="3"
          class="w-full bg-transparent resize-none outline-none text-sm md:text-base text-base-content placeholder:text-base-content/30 leading-relaxed"
          :placeholder="isEditing ? 'Edit your message...' : 'Write something, or @ to mention a file...'"
          @keydown="onKeyDown"
          @paste="$emit('paste', $event)"
          @focus="onFocus"
          @blur="onBlur"
          @input="onInput"
        ></textarea>
      </div>

      <!-- Divider -->
      <div class="mx-2 md:mx-3 border-t border-base-100/50 mt-1"></div>

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
        @send="onSend"
        @cancel-edit="$emit('cancel-edit')"
        @model-changed="$emit('model-changed', $event)"
        @toggle-voice="$emit('toggle-voice')"
        @remove-image="$emit('remove-image', $event)"
        @preview-image="$emit('preview-image', $event)"
        @profiles-selected="$emit('profiles-selected', $event)"
        @upload-files="$emit('upload-files', $event)"
      />
    </template>
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
    selectedProfiles: { type: Array, default: () => [] },
    cursorWord: { type: Object, default: () => ({}) },
    collapsed: { type: Boolean, default: false },
    // Counters shown on the collapsed pill (previews are hidden while collapsed)
    attachmentCount: { type: Number, default: 0 },
    fileCount: { type: Number, default: 0 }
  },
  emits: [
    'send', 'add-message', 'cancel-edit', 'model-changed',
    'toggle-voice', 'remove-image', 'preview-image', 'keydown', 'paste',
    'drop', 'profiles-selected', 'upload-files', 'focus', 'blur', 'toggle-collapsed', 'update:cursor-word'
  ],
  data() {
    return {
      isFocused: false,
      isDraggingOver: false,
      showFindReplace: false,
      // Draft kept in memory while the composer is collapsed on mobile
      collapsedDraft: ''
    }
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    }
  },
  watch: {
    collapsed(collapsed) {
      if (collapsed) {
        // The editor is unmounted while collapsed, keep the draft in memory
        this.collapsedDraft = this.$refs.editor?.value || ''
      } else {
        // Put the draft back as soon as the editor is mounted again
        this.$nextTick(() => this.restoreCollapsedDraft())
      }
    }
  },
  mounted() {
    // Mobile: toggle the composer when the user taps inside (expand) or outside (collapse)
    document.addEventListener('click', this.onDocumentClick)
  },
  unmounted() {
    document.removeEventListener('click', this.onDocumentClick)
  },
  methods: {
    // ── Mobile collapse ─────────────────────────────────────

    // Single authority for the inside/outside transitions.
    // The pill handles its own toggle with `.stop`, so a pill tap never reaches here.
    onDocumentClick(event) {
      if (!this.isMobile || this.isEditing) return
      const insideComposer = this.isInsideComposer(event.target)
      if (this.collapsed) {
        // Tapping the composer area (pill, attachment or files preview) expands it
        if (insideComposer) this.$emit('toggle-collapsed')
      } else if (!insideComposer) {
        // Tapping outside while reading the messages collapses it
        this.$emit('toggle-collapsed')
      }
    },
    isInsideComposer(target) {
      const container = this.$refs.inputContainer
      if (!container || !target) return false
      // The composer also hosts parent rendered items (attachments, message files,
      // intellisense) inside the wrapper marked with data-chat-composer
      const composer = container.closest('[data-chat-composer]') || container
      return composer.contains(target)
    },
    restoreCollapsedDraft() {
      const editor = this.$refs.editor
      if (!editor) return
      editor.value = this.collapsedDraft
      this.autoResize()
    },

    // ── Focus handling ──────────────────────────────────────

    onFocus() {
      this.isFocused = true
      this.$emit('focus')
    },
    onBlur(event) {
      const relatedTarget = event.relatedTarget
      const inputContainer = this.$refs.inputContainer

      if (!relatedTarget || !inputContainer?.contains(relatedTarget)) {
        this.isFocused = false
        this.$emit('blur')
      }
    },
    onKeyDown(event) {
      // Check for Ctrl+H to toggle find/replace
      if (event.key === 'h' && (event.ctrlKey || event.metaKey) && !event.shiftKey) {
        event.preventDefault()
        this.showFindReplace = !this.showFindReplace
        if (this.showFindReplace) {
          this.$nextTick(() => this.$refs.findReplace?.focusFindInput())
        }
        return
      }

      // Check for Ctrl+Shift+Enter to add message without sending to AI
      if (event.key === 'Enter' && event.ctrlKey && event.shiftKey) {
        event.preventDefault()
        event.stopPropagation()
        this.$emit('add-message')
        return
      }

      // Pass other keydown events to parent
      this.$emit('keydown', event)
    },
    onSend() {
      this.$emit('send')
    },
    onDrop(event) {
      this.isDraggingOver = false
      this.$emit('drop', event)
    },
    onInput() {
      this.autoResize()
      this.updateCursorWord()
    },
    getEditorText() {
      // While collapsed on mobile the editor is unmounted, return the kept draft
      if (!this.$refs.editor) return this.collapsedDraft
      return this.$refs.editor.value || ''
    },
    setEditorText(text) {
      if (this.$refs.editor) {
        this.$refs.editor.value = text
        this.autoResize()
        return
      }
      // Composer is collapsed: keep the text so it is restored when expanded
      this.collapsedDraft = text || ''
    },
    appendEditorText(text) {
      if (!this.$refs.editor) {
        // Composer is collapsed: keep the text so it is restored when expanded
        this.collapsedDraft += text || ''
        return
      }
      this.$refs.editor.value += text
      this.autoResize()
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
    },
    updateCursorWord() {
      const wordInfo = this.getCaretWordInfo()
      this.$emit('update:cursor-word', wordInfo)
    },
    onEmojiSelected({ emoji }) {
      const textarea = this.$refs.editor
      if (!textarea) return

      const text = textarea.value
      const caretIndex = textarea.selectionStart
      
      let emojiStart = caretIndex
      while (emojiStart > 0 && /\S/.test(text[emojiStart - 1])) {
        emojiStart--
      }
      
      const newText = text.slice(0, emojiStart) + emoji + text.slice(caretIndex)
      textarea.value = newText
      
      const newCursorPos = emojiStart + emoji.length
      textarea.selectionStart = newCursorPos
      textarea.selectionEnd = newCursorPos
      
      this.autoResize()
      this.updateCursorWord()
      textarea.focus()
    },
    onFindReplace(payload) {
      const textarea = this.$refs.editor
      if (!textarea) return

      const { type, match, replaceText, findText } = payload

      if (type === 'replace-one' && match) {
        const text = textarea.value
        const newText = text.slice(0, match.index) + replaceText + text.slice(match.index + match.length)
        textarea.value = newText
        textarea.selectionStart = match.index
        textarea.selectionEnd = match.index + replaceText.length
        this.autoResize()
      } else if (type === 'replace-all') {
        const text = textarea.value
        const regex = new RegExp(this.escapeRegex(findText), 'g')
        const newText = text.replace(regex, replaceText)
        textarea.value = newText
        this.autoResize()
      } else if (type === 'scroll' && payload.index !== undefined) {
        textarea.selectionStart = payload.index
        textarea.selectionEnd = payload.index + payload.length
        textarea.focus()
      }
    },
    escapeRegex(str) {
      return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
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