<script setup>
import Iframe from '../components/Iframe.vue'
</script>
<template>
  <Iframe class="w-full h-full" :url="url" 
    @loaded="onLoaded"      
  />
</template>
<script>
export default {
  data() {
    return {
      loaded: false
    }
  },
  computed: {
    url() {
      return "https://docs.codx-junior.com/"
    }
  },
  methods: {
    onLoaded(iframe) {
      const style = document.createElement('style')
      const refElement = document.body
      const { backgroundColor } = getComputedStyle(refElement) 
      style.innerHTML = `
        body, .VPSidebar, .curtain, .content-body, .VPLocalNav, .VPNavBar {
          background-color: ${backgroundColor} !important;
        }
      `
      iframe.contentDocument.body.appendChild(style)
      this.loaded = true
    }
  }
}
</script>