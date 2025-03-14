<script setup>
import VueMermaidString from 'vue-mermaid-string'
import mermaid from 'mermaid'
</script>

<template>
  <div class="w-full h-full flex gap-2">
    <pre v-if="error">{{ error }}</pre>
    <vue-mermaid-string class="w-full h-full flex gap-2" :value="diagram" :options="{ theme: 'dark' }" v-else />
  </div>
</template>
<script>
export default {
  props: ['diagram'],
  data() {
    return {
      error: ''
    }
  },
  created() {
    this.validateDiagram()  
  },
  watch: {
    diagram() {
      this.validateDiagram()
    }
  },
  methods: {
    async validateDiagram() {
      try {
        await mermaid.parse(this.diagram)
        this.error = null
      } catch (ex) {
        this.error = ex
      }
    }
  }
}
</script>
