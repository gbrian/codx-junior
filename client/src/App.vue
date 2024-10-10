<script setup>
import CodxJuniorVue from './views/CodxJunior.vue'
</script>

<template>
  <div class="w-full h-full flex bg-base-300 dark relative" data-theme="dark">
    <div class="w-2/3 h-full shrink-0 relative" v-if="showCoder">
      <iframe ref="iframe" :src="coderUrl" :class="[
          'h-full w-full border-0 bg-base-300']"
        @load="onCoderLoaded"
        title="coder"
        :style="`width:${iframeLoaded ? '100%': '0px'}`"
        >
      </iframe>
    </div>
    <div class="absolute top-0 left-0 right-0 z-50" v-if="showCoder && !iframeLoaded">
        LOADING CODER...
      </div>

    <CodxJuniorVue class="grow" @toggle-coder="showCoder = !showCoder" />
  </div>
</template>
<script>
export default {
  data () {
    return {
      url: "/coder",
      showCoder: true,
      iframeLoaded: false
    }
  },
  computed: {
    coderUrl () {
      return `${window.location.origin}${this.url}`
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
        setTimeout(() => this.iframeLoaded = true, 1000)
      }
      console.log("IFRAME URL", this.url)
    }
  }
}
</script>