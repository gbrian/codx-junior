<script setup>
import { DiffEditor } from 'monaco-editor-vue3'
</script>

<template>
  <div class="h-100">
    <DiffEditor
      v-model:value="modifiedCode"
      :original="originalCode"
      language="javascript"
      theme="vs"
    />
  </div>
</template>

<script>
export default {
  data() {
    return {
      originalCode: 'const x = 1',
      modifiedCode: 'const x = 2'
    }
  }
}
</script>