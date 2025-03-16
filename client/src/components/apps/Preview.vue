<script setup>
import Iframe from '../Iframe.vue';
</script>
<template>
  <div class="relative">
    <Iframe ref="iframe" :url="previewUrl" @loaded="onLoaded"
      title="preview"
      :key="iframeKey"
    />
    <div class="absolute top-0 left-0 right-0 bottom-0 bg-base-300 flex flex-col items-center justify-center z-50" v-if="!iframeLoaded">
      <div class="flex items-end gap-2">
          LOADING PREVIEW <span class="loading loading-dots loading-sm"></span>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      iframeKey: 0,
      iframeLoaded: false,
    }
  },
  computed: {
    previewUrl () {
      return "/novnc/vnc.html?autoconnect=true&resize=scale"
    }
  },
  methods: {
    onLoaded (iframe) {
      const { pathname, search } = iframe.contentWindow.location
      if (pathname.indexOf("/novnc") === -1) {
        this.url = `/coder${pathname.slice(1)}${search}`
        iframe.attributes.src.value = this.url
        this.iframeLoaded = false
      } else { 
        setTimeout(() => this.checkCoderLoader(iframe), 1000)
      }
      console.log("IFRAME URL", this.url)
    },
    checkCoderLoader (iframe) {
      let checkCount = 30 
      let interval = setInterval(() => {
        if (!iframe?.contentWindow) {
          return
        }
        const { contentWindow } = iframe
        if (!checkCount) {
          this.iframeKey = this.iframeKey + 1
        } else {
          const div = contentWindow.document.querySelector("body div")
          if (div) {
            this.iframeLoaded = true
            contentWindow.addEventListener('beforeunload', () => this.iframeLoaded = false)
          }
        }
        if (this.iframeLoaded || !checkCount) {
          clearInterval(interval)
        }
        checkCount--
      }, 1000)
    }
  },
}
</script>