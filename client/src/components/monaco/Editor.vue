<script setup>
import { CodeEditor } from 'monaco-editor-vue3'
import { DiffEditor } from 'monaco-editor-vue3'
</script>

<template>
  <div class="h-96">
    <DiffEditor
      v-model:value="code"
      :original="originalCode"
      :language="language"
      theme="vs-dark"
      v-if="diff"
    />
    <CodeEditor
      v-model:value="code"
      :language="language"
      theme="vs-dark"
      :options="editorOptions"
      v-else
    />
  </div>
</template>

<script>
export default {
  props: ['diff', 'modelValue', 'language', 'originalCode'],
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
        minimap: { enabled: true },
        automaticLayout: true,
        lineNumbers: "on"
      }
    }
  }
}
</script>