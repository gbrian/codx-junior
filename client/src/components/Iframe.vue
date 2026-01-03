<template>
  <iframe ref="iframe" :src="url" class="bg-base-300" 
    @load="onIframeLoaded"
    title="coder" allow="camera *;microphone *;clipboard-read; clipboard-write;">
  </iframe>
</template>
<script>
export default {
  props: ['url', 'nocheck'],
  methods: {
    onIframeLoaded() {
      const { iframe } = this.$refs
      if (!iframe?.contentWindow) {
        return setTimeout(() => this.onIframeLoaded, 2000)
      }
      if (this.nocheck) {
        return this.$emit('loaded', iframe)
      }
      this.$emit('loaded', iframe)
    }
  }
}
</script>