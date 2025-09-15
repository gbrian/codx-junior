<script setup>
import Iframe from '../Iframe.vue'
</script>
<template>
  <div class="relative">
    <Iframe ref="iframe" :url="filesUrl" @loaded="onIframeLoaded"
      title="files"
      :key="iframeKey"
    />
    <div class="absolute top-0 left-0 right-0 bottom-0 bg-base-300 flex flex-col items-center justify-center z-50"
      v-if="!iframeLoaded">
      <div class="flex items-end gap-2">
          LOADING STUDIO <span class="loading loading-dots loading-sm"></span>
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
    filesUrl () {
      return `/autogenstudio/`
    }
  },
  methods: {
    onIframeLoaded (iframe) {
      this.iframeLoaded = true
    }
  },
}
</script>