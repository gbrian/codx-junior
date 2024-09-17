<script setup>
import VueMermaidString from 'vue-mermaid-string'
</script>

<template>
  <vue-mermaid-string class="w-full h-full flex gap-2" :value="diagram" />
</template>
<script>
export default {
  props: ['diagram'],
}
</script>
