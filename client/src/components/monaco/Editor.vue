<script setup>
import { CodeEditor } from 'monaco-editor-vue3'
</script>

<template>
  <div class="h-400">
    <CodeEditor
      v-model:value="code"
      language="javascript"
      theme="vs-dark"
      :options="editorOptions"
    />
  </div>
</template>

<script>
export default {
  props: ['modelValue'],
  computed: {
    code: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      }
    }
  },
  data() {
    return {
      editorOptions: {
        fontSize: 14,
        minimap: { enabled: false },
        automaticLayout: true,
        lineNumbers: "off"
      }
    }
  }
}
</script>