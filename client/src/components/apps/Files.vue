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
          LOADING FILES <span class="loading loading-dots loading-sm"></span>
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
      return `/filebrowser`
    }
  },
  methods: {
    onIframeLoaded (iframe) {
      this.iframeLoaded = true
      const { document } = iframe.contentWindow
      let style = document.createElement("style");
      const classes = "#app > div > div > nav > div:nth-child(3) > button { display: none; }"
      style.appendChild(document.createTextNode(classes));
      document.head.appendChild(style);
    }
  },
}
</script>