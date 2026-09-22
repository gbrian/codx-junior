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
          ? 'bg-base-100 ring-1 ring-base-300 shadow-md rounded-lg md:rounded-xl'
          : 'bg-base-200/60 rounded-lg md:rounded-xl hover:bg-base-200 hover:ring-1 hover:ring-base-300'
    ]"
    @dragover.prevent="isDraggingOver = true"
    @dragleave.prevent="isDraggingOver = false"
    @drop.prevent="onDrop"        
  >
    <!-- ── Mobile collapsed pill ── -->
    <div
      v-if="isMobile && isMobileCollapsed"
      class="flex items-center gap-3 px-4 py-3 cursor-pointer"
      @click="expandMobile"
    >
      <i class="fa-solid fa-pen text-base-content/40 text-sm shrink-0"></i>
      <span class="text-base-content/40 text-sm flex-1 truncate">Write a message...</span>
      <i class="fa-solid fa-chevron-up text-base-content/30 text-xs"></i>
    </div>

    <!-- ── Full input (desktop always visible; mobile only when expanded) ── -->
    <template v-if="!isMobile || !isMobileCollapsed">
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
        class="px-2 md:px-3 py-2 md:py-2 border-b border-base-300/50"
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
      <div class="mx-2 md:mx-3 border-t border-base-300/50 mt-1"></div>

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
    cursorWord: { type: Object, default: () => ({}) }
  },
  emits: [
    'send', 'add-message', 'cancel-edit', 'model-changed',
    'toggle-voice', 'remove-image', 'preview-image', 'keydown', 'paste',
    'drop', 'profiles-selected', 'focus', 'blur'
  ],
  data() {
    return {
      isFocused: false,
      isDraggingOver: false,
      isMobileCollapsed: true,
      showFindReplace: false
    }
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    }
  },
  watch: {
    isMobile(val) {
      if (!val) this.isMobileCollapsed = false
    },
    waiting(val) {
      if (!val && this.isMobile) {
        this.isMobileCollapsed = true
      }
    }
  },
  methods: {
    expandMobile() {
      this.isMobileCollapsed = false
      this.$nextTick(() => this.$refs.editor?.focus())
    },
    collapseMobile() {
      this.isMobileCollapsed = true
      this.$refs.editor?.blur()
    },
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
        if (this.isMobile) {
          this.collapseMobile()
        }
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
      if (this.isMobile) {
        this.$nextTick(() => this.collapseMobile())
      }
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
      if (this.isMobile && this.isMobileCollapsed) {
        this.expandMobile()
        return
      }
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
    'getCaretWordInfo',
    'collapseMobile',
    'expandMobile',
    'showFindReplace'
  ]
}
</script>