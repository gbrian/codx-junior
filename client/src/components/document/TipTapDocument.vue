<script setup>
  import { Editor, EditorContent } from '@tiptap/vue-3'
  import StarterKit from '@tiptap/starter-kit'
</script>
<template>
  <editor-content :editor="editor" />
</template>

<script>
  export default {
    props: ['text'],
    data() {
      return {
        editor: null,
        content: this.text
      }
    },

    mounted() {
      this.editor = new Editor({
        content: this.content,
        extensions: [StarterKit],
      })
    },

    beforeUnmount() {
      this.editor.destroy()
    },
  }
</script>