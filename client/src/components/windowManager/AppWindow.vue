<script setup>
import Iframe from '../Iframe.vue'
</script>

<template>
  <div class="w-full h-full" :class="loaded ? '' : 'opacity-0'">
    <Iframe
      ref="iframe"
      class="w-full h-full"
      :key="iframeKey"
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
      // Prefer the explicit prop, then the workspace payload (name + path +
      // metadata), then the app definition and the legacy params slot.
      return this.app ||
        this.params?.params?.workspace ||
        this.params?.params?.app ||
        this.params?.app
    },
    tabId() {
      // The explicit prop wins, then the app stored in the panel params (also
      // covers `workspace` panels, whose app lives under `params.app`).
      return this.app?.tabId ||
        this.params?.params?.app?.tabId ||
        this.theApp?.tabId ||
        this.params?.app?.tabId
    },
    // Live app from the store: runtime param updates (e.g. a URL typed in the
    // app menu navigator) are reactive here, unlike the panel params snapshot.
    liveApp() {
      return this.tabId ? this.$storex.ui.openApps[this.tabId] : null
    },
    // Identity of the iframe. Includes the navigator token so a "home" click
    // always remounts the iframe — even when the URL string doesn't change
    // (already at the base URL, or `lastUrl` was never persisted because the
    // iframe content is cross-origin) — which forces a real reload.
    iframeKey() {
      const base = this.theApp?.path || ''
      const token = this.liveApp?.params?.navToken || 0
      return `${base}#${token}`
    }
  },
  watch: {
    // Navigate the iframe when the app URL is changed from outside (the
    // navigator control in the app menu). Ignore echoes of our own navigation.
    'liveApp.params.lastUrl'(url) {
      if (url && url !== this.currentUrl) {
        this.currentUrl = url
      }
    }
  },
  methods: {
    onLoaded() {
      this.loaded = true
      // Read the actual current URL and title from the iframe after load
      this.readIframeUrl()
      this.$emit('loaded')
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