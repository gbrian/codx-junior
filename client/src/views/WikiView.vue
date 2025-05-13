<script setup>
import Iframe from '../components/Iframe.vue'
</script>
<template>
  <Iframe class="flex flex-col gap-2 h-full mb-4" :url="url" 
    @loaded="onLoaded"
  />
</template>
<script>
export default {
  computed: {
    url() {
      return `/wiki/${this.$project.project_name}/index.html`
    }
  },
  methods: {
    onLoaded(iframe) {
      const style = document.createElement('style')
      const refElement = document.body
      const { backgroundColor } = getComputedStyle(refElement) 
      style.innerHTML = `
        body, .VPSidebar, .curtain, .content-body, .VPLocalNav {
          background-color: ${backgroundColor} !important;
        }
      `
      iframe.contentDocument.body.appendChild(style)
    }
  }
}
</script>