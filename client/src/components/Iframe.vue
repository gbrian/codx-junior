<template>
  <iframe ref="iframe" :src="url" class="h-full w-full bg-base-300" 
    @load="onIframeLoaded"
    title="coder" allow="camera *;microphone *;clipboard-read; clipboard-write;">
  </iframe>
</template>
<script>
export default {
  props: ['url'],
  methods: {
    onIframeLoaded() {
      const { iframe } = this.$refs
      if (!iframe) {
        return setTimeout(() => this.onIframeLoaded, 2000)
      }
      const { pathname, search } = iframe.contentWindow.location
      if (pathname.indexOf(this.url) === -1) {
        const url = `${this.url}${pathname.slice(1)}${search}`
        iframe.attributes.src.value = url
      } else {
        this.$emit('loaded', iframe)
      }
    }
  }
}
</script>