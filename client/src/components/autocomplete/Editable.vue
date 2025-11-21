<script setup>
</script>

<template>
  <div ref="editor"
    class="editor w-full h-full flex gap-2"
    :class="isAutoCompleteMode && 'text-warning'"
    contenteditable
    @keydown="onKeyPress"
    @input="onContentChange"  
  >
    <!-- Editor content -->
  </div>
</template>

<script>
export default {
  props: ['suggestCallback', 'modelValue'],
  data() {
    return {
      syncInterval: null,
      editorContent: this.modelValue
    }
  },
  mounted() {
    this.syncInterval = setInterval(() => this.onContentChange(), 200)
  },
  beforeUnmount() {
    clearInterval(this.syncInterval)
  },
  computed: {
    isAutoCompleteMode() {
      return /[@#](\w*)$/.exec(this.editorContent)
    }, 
    currentInput() {
      return (this.isAutoCompleteMode || [])[1]
    }
  },
  watch: {
    modelValue(newVal) {
      if (newVal !== this.editorContent) {
        this.editorContent = newVal
        this.$refs.editor.innerText = this.editorContent
      }
    }
  },
  methods: {
    onContentChange() {
      const content = this.$refs.editor.innerText
      if (content !== this.editorContent) {
        this.editorContent = content
        this.$emit('update:modelValue', this.editorContent) // Emit an event to update parent v-model
      }
    },
    onKeyPress(event) {
      const char = String.fromCharCode(event.which || event.keyCode)
      if (this.isAutoCompleteMode &&  (event.key === 'Tab' || event.key === 'Enter')) {
        event.preventDefault()
        this.confirmAutoComplete()
        return false
      } else if (this.isAutoCompleteMode && /\w/.test(char)) {
        requestAnimationFrame(() => this.suggestWord())
      }
    },
    suggestWord() {
      if (this.suggestCallback) {
        const suggestion = this.suggestCallback(this.currentInput)
        if (suggestion) {
          this.completeWord(suggestion)
        }
      }
    },
    completeWord(matchWord) {
      if (!matchWord) {
        return
      }
      const selection = window.getSelection()
      const selectedText = selection.toString()
      const sliceCount = this.currentInput.length - selectedText.length
      const suggestion = matchWord.slice(sliceCount)
      if (suggestion) {
        const range = selection.getRangeAt(0)
        range.deleteContents()
        range.insertNode(document.createTextNode(suggestion))
        selection.removeAllRanges()
        selection.addRange(range)
      }
    },
    confirmAutoComplete() {
      const selection = window.getSelection()
      if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        range.collapse(false) // Collapse the range to the end
        const spaceNode = document.createTextNode("\xA0")
        range.insertNode(spaceNode) // Insert a space
        selection.removeAllRanges()
        range.setStartAfter(spaceNode)
        selection.addRange(range) // Move the caret after the space
      }
    }
  }
}
</script>