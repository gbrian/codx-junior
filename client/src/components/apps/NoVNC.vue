<template>
  <div class="relative">
    <iframe ref="iframe" :src="appUrl" class="h-full w-full border-0 bg-base-300"
        @load="onAppLoaded"
        title="coder"
        allow="camera *;microphone *;clipboard-read; clipboard-write;"
        :key="iframeKey"
      >
      </iframe>
      <div class="absolute top-0 left-0 right-0 bottom-0 bg-base-300 flex flex-col items-center justify-center z-50" v-if="!iframeLoaded">
        <div class="flex items-end gap-2">
            LOADING VNC <span class="loading loading-dots loading-sm"></span>
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
    appUrl () {
      return "/novcn/vnc.html"
    }
  },
  methods: {
    onAppLoaded () {
      if (!this.$refs.iframe) {
        return
      }
      setTimeout(() => this.checkCoderLoader(), 1000)
    },
    checkCoderLoader () {
      let checkCount = 30 
      let interval = setInterval(() => {
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