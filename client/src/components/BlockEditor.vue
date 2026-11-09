<template>
  <!-- Edit mode -->
  <div v-if="isEditing" class="bg-base-200 rounded-lg p-2 md:p-3 border border-base-100">
    <!-- Editor toolbar -->
    <div class="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-base-100">
      <span class="flex items-center gap-2 text-xs font-semibold text-base-content/60 min-w-0">
        <i class="fa-solid fa-pen-to-square text-info"></i>
        <span class="truncate">{{ label }}</span>
      </span>
      <div class="flex items-center gap-1 shrink-0">
        <button
          class="btn btn-xs btn-ghost gap-1"
          title="Cancel (Esc)"
          @click="cancelEdit"
        >
          <i class="fa-solid fa-ban"></i>
          <span class="hidden sm:inline">Cancel</span>
        </button>
        <button
          class="btn btn-xs btn-primary gap-1"
          :disabled="!hasChanges"
          title="Save (Ctrl/Cmd + S)"
          @click="saveEdit"
        >
          <i class="fa-solid fa-check"></i>
          <span class="hidden sm:inline">Save</span>
        </button>
      </div>
    </div>

    <!-- Editor content -->
    <div class="space-y-2">
      <div class="bg-base-300 rounded overflow-hidden border border-base-content/5">
        <textarea
          ref="textarea"
          v-model="editedContent"
          class="block w-full p-3 bg-base-300 text-xs font-mono leading-relaxed text-base-content border-0 resize-y focus:outline-none focus:ring-1 focus:ring-primary/40"
          :class="isCodeBlock ? 'h-[300px]' : 'h-[260px]'"
          :placeholder="placeholder || ('Edit ' + (language || 'block') + '...')"
          spellcheck="false"
          @keydown="onKeydown"
        ></textarea>
      </div>

      <!-- Quick info -->
      <div class="flex flex-wrap items-center justify-between gap-2 text-[10px] text-base-content/40">
        <span v-if="hasChanges" class="text-warning flex items-center gap-1">
          <i class="fa-solid fa-circle-info"></i> Unsaved changes
        </span>
        <span v-else>No changes</span>
        <span class="flex items-center gap-3">
          <span v-if="isCodeBlock">{{ lineCount }} lines</span>
          <span>{{ editedContent.length }} chars</span>
          <span class="hidden sm:inline">Tab indents · Esc cancels · Ctrl/Cmd+S saves</span>
        </span>
      </div>
    </div>
  </div>

  <!-- View mode -->
  <div v-else>
    <slot></slot>
  </div>
</template>

<script>
export default {
  props: {
    originalContent: { type: String, required: true },
    isCodeBlock: { type: Boolean, default: false },
    language: { type: String, default: 'text' },
    label: { type: String, default: 'Editing block' },
    placeholder: { type: String, default: '' }
  },
  emits: ['edit-start', 'edit-cancel', 'edit-save'],
  data() {
    return {
      isEditing: false,
      editedContent: ''
    }
  },
  computed: {
    hasChanges() {
      return this.editedContent !== this.originalContent
    },
    lineCount() {
      return this.editedContent ? this.editedContent.split('\n').length : 0
    }
  },
  watch: {
    // An external update (streaming message, another editor) must not clobber
    // the draft while the user is typing, but when idle the source should stay
    // current.
    originalContent(val) {
      if (!this.isEditing) this.editedContent = val || ''
    }
  },
  methods: {
    startEdit() {
      if (this.isEditing) return
      this.isEditing = true
      this.editedContent = this.originalContent ?? ''
      this.$emit('edit-start')
      this.$nextTick(() => {
        const el = this.$refs.textarea
        if (!el) return
        el.focus()
        el.setSelectionRange(el.value.length, el.value.length)
      })
    },
    cancelEdit() {
      if (!this.isEditing) return
      this.isEditing = false
      this.editedContent = ''
      this.$emit('edit-cancel')
    },
    saveEdit() {
      if (!this.isEditing) return
      if (!this.hasChanges) {
        this.isEditing = false
        this.editedContent = ''
        return
      }
      const newContent = this.editedContent
      this.$emit('edit-save', {
        originalContent: this.originalContent,
        newContent
      })
      this.isEditing = false
      this.editedContent = ''
    },
    onKeydown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopPropagation()
        this.cancelEdit()
        return
      }
      if ((event.ctrlKey || event.metaKey) && (event.key === 's' || event.key === 'Enter')) {
        event.preventDefault()
        event.stopPropagation()
        this.saveEdit()
        return
      }
      if (event.key === 'Tab') {
        event.preventDefault()
        this.insertIndent(event.shiftKey)
      }
    },
    // Keep the caret in place and insert two spaces (Shift+Tab removes up to
    // two leading spaces on the current line).
    insertIndent(remove = false) {
      const el = this.$refs.textarea
      if (!el) return
      const start = el.selectionStart
      const end = el.selectionEnd
      const value = this.editedContent

      if (!remove) {
        this.editedContent = `${value.slice(0, start)}  ${value.slice(end)}`
        this.$nextTick(() => {
          el.setSelectionRange(start + 2, start + 2)
        })
        return
      }

      const lineStart = value.lastIndexOf('\n', start - 1) + 1
      const before = value.slice(lineStart, start)
      const removeCount = before.endsWith('  ') ? 2 : before.endsWith(' ') ? 1 : 0
      if (!removeCount) return
      this.editedContent = value.slice(0, start - removeCount) + value.slice(start)
      this.$nextTick(() => {
        el.setSelectionRange(start - removeCount, start - removeCount)
      })
    }
  }
}
</script>
