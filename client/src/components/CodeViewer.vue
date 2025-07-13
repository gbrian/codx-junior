<script setup>
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
</script>

<template>
  <div class="flex flex-col gap-2">
  <VueCodeHighlighter :code="code" :lang="language" :title="language" />
  <div class="flex justify-end gap-2">
    <button class="btn btn-sm btn-warning" @click="applyPatch" v-if="isPatch">
      Apply
    </button>
  </div>
</div>
</template>
<script>
export default {
  props: ['code', 'language'],
  computed: {
    isPatch() {
      return this.language === 'diff'
    }
  },
  methods: {
    applyPatch() {
      this.$projects.patch(this.code)
    }
  }
}
</script>

<style scoped>
.pre .code {
  font-size: 8px !important;
}
</style>
