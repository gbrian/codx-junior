<script setup>
import CodxJuniorVue from './views/CodxJunior.vue'
</script>

<template>
  <div class="w-full h-full flex bg-base-300 relative" data-theme="dark">
    <div :class="['h-full relative grow']" v-if="showCoder">
      <iframe ref="iframe" :src="coderUrl" :class="[
          'h-full w-full border-0 bg-base-300']"
        @load="onCoderLoaded"
        title="coder"
        allow="camera *;microphone *;clipboard-read; clipboard-write;"
        :key="iframeKey"
        >
      </iframe>
      <div class="absolute top-0 left-0 right-0 bottom-0 bg-base-300 flex flex-col items-center justify-center z-50" v-if="showCoder && !iframeLoaded">
        <div class="flex items-end gap-2">
          LOADING CODER <span class="loading loading-dots loading-sm"></span>
        </div>
      </div>
    </div>

    <div :class="['flex', showCoder ? `${codxJuniorWidth} shrink-0`: 'grow']" v-if="showCodxJunior">
      <div class="w-fit h-full flex flex-col justify-between bg-base-100" v-if="showCoder">
        <div class="text-xs py-2 px-1 click" @click="increaseSplit">
          <i class="fa-solid fa-chevron-left"></i>
        </div>
        <div class="text-xs py-2 px-1 click" @click="decreaseSplit">
          <i class="fa-solid fa-chevron-right"></i>
        </div>
      </div>
      <CodxJuniorVue class="grow"
        @toggle-coder="toggleCoder"
        @toggle-codx-junior="showCodxJunior = !showCodxJunior"
        v-if="showCodxJunior"
      />
    </div>
    <div class="bg-base-300 w-10 h-full p-2" v-else>
      <div class="btn btn-xs" @click="showCodxJunior = true">
        <i class="fa-solid fa-chevron-left"></i>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      url: "/coder",
      showCoder: true,
      showCodxJunior: true,
      iframeLoaded: false,
      codxJuniorPanelWidth: 2,
      maxcodxJuniorPanelWidth: 6,
      iframeKey: 0
    }
  },
  computed: {
    coderUrl () {
      return `${window.location.origin}${this.url}`
    },
    codxJuniorWidth () {
      const {
        showCoder,
        codxJuniorPanelWidth,
        maxcodxJuniorPanelWidth
      } = this
      if (!showCoder) {
        return "grow"
      }
      return `w-${codxJuniorPanelWidth}/${maxcodxJuniorPanelWidth}`
    }
  },
  methods: {
    onCoderLoaded () {
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
    increaseSplit () {
      this.codxJuniorPanelWidth = this.codxJuniorPanelWidth + 1
      if (!this.showCodxJunior) {
        this.showCodxJunior = true
      }
      if (this.codxJuniorPanelWidth >= this.maxcodxJuniorPanelWidth) {
        this.codxJuniorPanelWidth = 2
        this.showCoder = false
      }
    },
    decreaseSplit () {
      this.codxJuniorPanelWidth = this.codxJuniorPanelWidth - 1
      if (this.codxJuniorPanelWidth < 1) {
        this.showCodxJunior = false
        this.codxJuniorPanelWidth = 2
      }
    },
    toggleCoder() {
      this.showCoder = !this.showCoder
      if (this.showCoder) {
        this.iframeLoaded = false
      }
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
  }
}
</script>