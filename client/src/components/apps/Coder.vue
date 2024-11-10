<template>
  <div class="relative">
    <iframe ref="iframe" :src="coderUrl" class="h-full w-full bg-base-300"
        @load="onCoderLoaded"
        title="coder"
        allow="camera *;microphone *;clipboard-read; clipboard-write;"
        :key="iframeKey"
      >
      </iframe>
      <div class="absolute top-0 left-0 right-0 bottom-0 bg-base-300 flex flex-col items-center justify-center z-50" v-if="!iframeLoaded">
        <div class="flex items-end gap-2">
            LOADING CODER <span class="loading loading-dots loading-sm"></span>
        </div>
      </div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      iframeKey: 0,
      iframeLoaded: false
    }
  },
  computed: {
    coderUrl () {
      return `/coder`
    }
  },
  methods: {
    onCoderLoaded () {
      if (!this.$refs.iframe) {
        return
      }
      const { pathname, search } = this.$refs.iframe.contentWindow.location
      if (pathname.indexOf("/coder") === -1) {
        this.url = `/coder${pathname.slice(1)}${search}`
        this.$refs.iframe.attributes.src.value = this.url
        this.iframeLoaded = false
      } else { 
        setTimeout(() => this.checkCoderLoader(), 1000)
      }
      console.log("IFRAME URL", this.url)
    },
    checkCoderLoader () {
      let checkCount = 30 
      let interval = setInterval(() => {
        if (!this.$refs.iframe) {
          return
        }
        const { contentWindow } = this.$refs.iframe
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