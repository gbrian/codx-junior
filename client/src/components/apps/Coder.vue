<script setup>
import Iframe from '../Iframe.vue';
</script>
<template>
  <div class="relative">
    <Iframe ref="iframe" :url="coderUrl" @loaded="onCoderLoaded"
      title="coder"
      :key="iframeKey"
    />
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
      iframeLoaded: false,
    }
  },
  computed: {
    openProject () {
      return this.$projects.allProjects?.find(({ codx_path }) => codx_path === this.$ui.coderProjectCodxPath)
    },
    coderUrl () {
      const { openProject } = this
      if (openProject) {
        const folders = [openProject.project_path].map(f => `folder=${f}`).join("&")
        return `/coder?${folders}`
      }
      return "/coder"
    }
  },
  methods: {
    onCoderLoaded (iframe) {
      if (!iframe?.contentWindow) {
        return
      }
      const { pathname, search } = iframe.contentWindow.location
      if (pathname.indexOf("/coder") === -1) {
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