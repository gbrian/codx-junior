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
function isKeyWord(word) {
  return /^[@#]/.test(word)
}

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
    },
    isAutoCompleteMode(newVal) {
      if (!newVal) {
        this.highlightKeywords()
      }
    }
  },
  methods: {
    highlightKeywords() {
      const editor = this.$refs.editor
      const content = editor.innerHTML
      const regex = /([@#]\w+)/g
      const tempDiv = document.createElement('div')
      tempDiv.innerHTML = content

      const walker = document.createTreeWalker(tempDiv, NodeFilter.SHOW_TEXT, null, false)
      let node
      let lastSpan // Remember the last span created
      let index = 0 // Index for creating unique ids
      while (node = walker.nextNode()) {
        let match
        while (match = regex.exec(node.nodeValue)) {
          const keyword = match[0]
          const span = document.createElement('span')
          span.className = 'keyword text-info'
          span.id = `keyword-${index++}` // Unique id with index
          span.textContent = keyword
          span.contentEditable = false

          const index = match.index
          const textBefore = node.nodeValue.slice(0, index)
          const textAfter = node.nodeValue.slice(index + keyword.length)

          const parent = node.parentNode
          parent.insertBefore(document.createTextNode(textBefore), node)
          parent.insertBefore(span, node)
          node.nodeValue = textAfter

          regex.lastIndex = 0
          lastSpan = span // Remember the last span created
        }
      }

      editor.innerHTML = tempDiv.innerHTML
      // Set cursor after the last span created
      if (lastSpan) {
        const range = document.createRange()
        range.setStartAfter(lastSpan)
        range.collapse(true)
        const selection = window.getSelection()
        selection.removeAllRanges()
        selection.addRange(range)
      }
    },
    onContentChange() {
      const content = this.$refs.editor.innerText
      if (content !== this.editorContent) {
        this.editorContent = content
        this.$emit('update:modelValue', this.editorContent) // Emit an event to update parent v-model
      }
    },
    onKeyPress(event) {
      const char = String.fromCharCode(event.which || event.keyCode)
      if (this.isAutoCompleteMode && (event.key === 'Tab' || event.key === 'Enter')) {
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