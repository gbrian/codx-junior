<script setup>
import Iframe from '../Iframe.vue'
</script>

<template>
  <div class="w-full h-full" :class="loaded ? '' : 'opacity-10'">
    <Iframe
      ref="iframe"
      class="w-full h-full"
      :key="theApp.path"
      :url="currentUrl"
      @loaded="onLoaded"
      @navigated="onNavigated"
    />
  </div>
</template>

<script>
export default {
  name: "AppWindow",
  props: ['app', 'params'],
  data() {
    return {
      loaded: false,
      currentUrl: null
    }
  },
  created() {
    const app = this.theApp
    // Restore last navigated URL from params or fall back to app path
    this.currentUrl = this.params?.params?.lastUrl || app?.path
    this.loaded = app?.is_vnc
  },
  computed: {
    theApp() {
      return this.app || this.params?.params?.app || this.params?.app
    },
    tabId() {
      return this.theApp?.tabId
    }
  },
  methods: {
    onLoaded() {
      this.loaded = true
      // Read the actual current URL and title from the iframe after load
      this.readIframeUrl()
    },
    // Read URL and title directly from iframe contentWindow after navigation
    readIframeUrl() {
      try {
        const iframeEl = this.$refs.iframe?.$el || this.$refs.iframe
        const contentWindow = iframeEl?.contentWindow
        const url = contentWindow?.location?.href
        const title = contentWindow?.document?.title
        if (url && url !== 'about:blank') {
          this.onNavigated(url, title)
        }
      } catch (e) {
        // Cross-origin access blocked, silently ignore
      }
    },
    // Track url changes and persist them in the app params via store
    onNavigated(url, title) {
      if (!url || url === this.currentUrl) return
      this.currentUrl = url
      this.persistUrl(url, title)
    },
    // Persist current URL and page title so layout restore can recover them
    persistUrl(url, title) {
      if (!this.tabId) return
      const params = { lastUrl: url }
      // Only store title if it's a non-empty valid string
      if (title && title.trim()) {
        params.title = title.trim()
      }
      this.$storex.ui.updateAppParams({
        tabId: this.tabId,
        params
      })
    }
  }
}
</script>