<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
</script>

<template>
  <VueCodeHighlighter :code="code" :lang="language" :title="language" />
</template>
<script>
export default {
  props: ['code', 'language']
}
</script>