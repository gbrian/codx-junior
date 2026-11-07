<template>
  <div class="flex flex-col h-full bg-base-100 overflow-hidden">
    <!-- Header -->
    <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/70 flex-shrink-0">
      <div class="flex items-center gap-2 min-w-0 flex-1">
        <span class="relative flex h-2.5 w-2.5 flex-shrink-0">
          <span
            v-if="isRunning"
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-60"
          ></span>
          <span
            class="relative inline-flex rounded-full h-2.5 w-2.5"
            :class="isRunning ? 'bg-success' : 'bg-base-content/30'"
          ></span>
        </span>
        <h3 class="font-semibold truncate">{{ activeSession?.name || 'Browser session' }}</h3>
        <span class="badge badge-xs" :class="isRunning ? 'badge-success' : 'badge-warning'">
          {{ liveBadge }}
        </span>
        <span class="text-[11px] opacity-50 truncate hidden sm:inline">{{ activeSessionId?.slice(0, 8) }}</span>
      </div>

      <button
        class="btn btn-xs btn-ghost"
        title="Reload live view"
        @click="reloadLiveView"
      >
        <i class="fa-solid fa-rotate"></i>
      </button>
      <button
        class="btn btn-xs btn-ghost"
        title="Open live view in a new tab"
        :disabled="!vncEmbedUrl"
        @click="openLiveView"
      >
        <i class="fa-solid fa-up-right-from-square"></i>
      </button>
      <button
        v-if="isRunning"
        class="btn btn-xs btn-ghost"
        title="Stop browser"
        @click="stopSession"
      >
        <i class="fa-solid fa-stop"></i>
      </button>
      <button
        v-else
        class="btn btn-xs btn-success"
        title="Start browser"
        @click="restartSession"
      >
        <i class="fa-solid fa-play"></i>
      </button>
    </div>

    <!-- Navigation toolbar -->
    <div class="flex items-center gap-1 px-3 py-2 border-b border-base-content/10 flex-shrink-0">
      <button class="btn btn-xs btn-ghost" title="Back" :disabled="!isRunning" @click="runPageAction('back')">
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Forward" :disabled="!isRunning" @click="runPageAction('forward')">
        <i class="fa-solid fa-arrow-right"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Refresh page" :disabled="!isRunning" @click="runPageAction('refresh')">
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>
      <form class="flex-1 flex items-center gap-1 min-w-0" @submit.prevent="goToAddress">
        <input
          v-model="address"
          type="text"
          class="input input-xs input-bordered flex-1 min-w-0"
          placeholder="https://..."
          :disabled="!isRunning"
        />
        <button class="btn btn-xs btn-primary" type="submit" :disabled="!isRunning || navigating">
          <span v-if="navigating" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-solid fa-arrow-right"></i>
        </button>
      </form>
      <button
        class="btn btn-xs btn-ghost"
        title="AI/user screenshot"
        :disabled="!isRunning || screenshotLoading"
        @click="takeScreenshot"
      >
        <span v-if="screenshotLoading" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-camera"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Refresh activity + cost" @click="refreshSessionData()">
        <i class="fa-solid fa-rotate-right"></i>
      </button>
    </div>

    <!-- Live browser: the ONLY surface this component owns.
         No splitter and no chat pane live here. The panel that hosts this
         component (BrowserSessionPanel) owns the [ browser | chat ] split, so
         docking the chat never nests a layout inside the viewer. -->
    <div class="flex-1 min-h-0">
      <div class="drawer drawer-end h-full">
        <input
          :id="drawerId"
          v-model="activityDrawerOpen"
          type="checkbox"
          class="drawer-toggle"
          aria-hidden="true"
        />

        <div class="drawer-content h-full">
          <div class="relative h-full min-h-[240px] bg-black/40">
            <iframe
              v-if="isRunning && vncEmbedUrl"
              :key="iframeKey"
              :src="vncEmbedUrl"
              class="w-full h-full border-0 bg-black"
              allow="clipboard-read; clipboard-write; fullscreen"
              @load="onFrameLoaded"
            ></iframe>
            <div v-else class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-base-content/60">
              <i class="fa-regular fa-compass text-5xl opacity-30"></i>
              <p class="font-semibold">Browser is {{ activeSession?.status || 'not running' }}</p>
              <button v-if="activeSession" class="btn btn-sm btn-success" @click="restartSession">
                <i class="fa-solid fa-play"></i> Start browser
              </button>
            </div>
            <div
              v-if="loadingFrame && isRunning"
              class="absolute inset-0 flex items-center justify-center bg-base-100/70 pointer-events-none"
            >
              <span class="loading loading-spinner loading-lg"></span>
            </div>
          </div>
        </div>

        <!-- Shared activity drawer -->
        <div class="drawer-side h-full z-30">
          <label :for="drawerId" class="drawer-overlay" aria-label="Close shared activity"></label>
          <div
            class="flex flex-col h-full w-80 max-w-[85vw] bg-base-100 border-l border-base-content/10 shadow-xl"
            role="complementary"
            aria-label="Shared activity"
          >
            <!-- Drawer header -->
            <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 flex-shrink-0">
              <i class="fa-solid fa-wave-square text-primary text-sm" aria-hidden="true"></i>
              <h4 class="text-xs font-bold uppercase tracking-wide opacity-70 flex-1">Shared activity</h4>
              <span class="text-[11px] opacity-50">{{ activity.length }} events</span>
              <button
                class="btn btn-xs btn-ghost btn-circle"
                title="Close"
                aria-label="Close shared activity"
                @click="activityDrawerOpen = false"
              >
                <i class="fa-solid fa-times"></i>
              </button>
            </div>

            <!-- Activity list -->
            <div class="flex-1 min-h-0 overflow-y-auto p-3">
              <div v-if="recentActivity.length" class="space-y-1">
                <div
                  v-for="(entry, index) in recentActivity"
                  :key="`${entry.ts}-${index}`"
                  class="flex items-start gap-2 text-xs py-0.5"
                >
                  <span class="badge badge-xs flex-shrink-0" :class="actorClass(entry)">{{ actorLabel(entry) }}</span>
                  <span class="font-mono text-[11px] opacity-50 flex-shrink-0">{{ formatTime(entry.ts) }}</span>
                  <span class="font-medium">{{ entry.action }}</span>
                  <span v-if="entry.url" class="truncate opacity-60 flex-1">{{ entry.url }}</span>
                  <i
                    v-if="entry.success === false"
                    class="fa-solid fa-circle-exclamation text-error text-[10px]"
                    :title="entry.error || 'failed'"
                  ></i>
                </div>
              </div>
              <p v-else class="text-xs opacity-50">No activity yet. Type or click in the live view — it will appear here.</p>
            </div>

            <!-- AI cost -->
            <div class="flex-shrink-0 border-t border-base-content/10 p-3">
              <div class="flex items-center justify-between mb-1">
                <h4 class="text-xs font-bold uppercase tracking-wide opacity-60">AI cost</h4>
                <span class="text-[11px] opacity-50">SmolAgent</span>
              </div>
              <div class="rounded border border-base-content/10 p-2 space-y-1">
                <div class="flex items-center justify-between text-sm font-semibold">
                  <span>Total</span>
                  <span class="text-amber-400">{{ costLabel }} cxj</span>
                </div>
                <div class="grid grid-cols-2 gap-1 text-[11px] opacity-70">
                  <span>Tokens: {{ formatTokens(costInfo?.total_tokens) }}</span>
                  <span>LLM: {{ costInfo?.total_llm_calls || 0 }}</span>
                  <span>Input: {{ formatTokens(costInfo?.total_input_tokens) }}</span>
                  <span>Tools: {{ costInfo?.total_tool_calls || 0 }}</span>
                </div>
                <div v-if="costInfo?.chats?.length" class="pt-1 border-t border-base-content/10 space-y-0.5">
                  <div v-for="chat in costInfo.chats" :key="chat.chat_id" class="flex items-center justify-between text-[11px]">
                    <span class="truncate opacity-70">{{ chat.chat_name || chat.chat_id?.slice(0, 8) }}</span>
                    <span class="font-mono">{{ formatCoins(chat.cost_cxjcoins) }} cxj</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center gap-3 px-3 py-1.5 border-t border-base-content/10 bg-base-200/70 flex-shrink-0 text-[11px] text-base-content/60">
      <span v-if="lastActivityLabel" class="flex items-center gap-1.5">
        <i class="fa-regular fa-clock" aria-hidden="true"></i>
        {{ lastActivityLabel }}
      </span>
      <span class="flex-1"></span>
      <span class="flex items-center gap-1.5 font-mono text-amber-400/90" title="Total AI cost">
        {{ costLabel }} cxj
      </span>
      <button
        class="btn btn-xs btn-ghost gap-1.5"
        :class="activityDrawerOpen ? 'text-primary' : 'text-base-content/60 hover:text-base-content'"
        title="Shared activity"
        aria-label="Toggle shared activity drawer"
        :aria-expanded="activityDrawerOpen ? 'true' : 'false'"
        @click="toggleActivityDrawer"
      >
        <i class="fa-solid fa-wave-square"></i>
        <span class="badge badge-xs" :class="activity.length ? 'badge-primary' : 'badge-ghost'">
          {{ activity.length }}
        </span>
      </button>
    </div>

    <!-- Screenshot modal -->
    <div v-if="showScreenshot" class="modal modal-open" @click.self="showScreenshot = false">
      <div class="modal-box max-w-5xl w-11/12">
        <div class="flex items-center justify-between mb-2">
          <h3 class="font-bold">Screenshot — {{ activeSession?.name }}</h3>
          <button class="btn btn-sm btn-circle btn-ghost" @click="showScreenshot = false">
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
        <img :src="screenshot" alt="Browser screenshot" class="w-full rounded border border-base-content/10" />
      </div>
    </div>
  </div>
</template>

<script>
/**
 * BrowserViewer — shared AI/user co-browsing surface.
 *
 * The iframe is the LinuxServer/Selkies live view of the session container.
 * Clicking, typing and navigating inside it controls the real browser.  The
 * toolbar uses the same REST action endpoint as the AI tools, and the shared
 * activity drawer (footer icon, slides from the right) proves who did what
 * on the shared page.
 *
 * Layout: ONE surface, the live browser. This component owns no splitter and
 * no chat pane: the [ browser | chat ] split belongs to BrowserSessionPanel,
 * which is the only place a session chat may be docked.
 */
export default {
  name: 'BrowserViewer',
  props: {
    sessionId: { type: String, default: null },
    session: { type: Object, default: null },
    params: { type: Object, default: null },
    compact: { type: Boolean, default: false }
  },
  data() {
    return {
      address: '',
      iframeKey: 0,
      loadingFrame: true,
      navigating: false,
      screenshotLoading: false,
      screenshot: null,
      showScreenshot: false,
      pollTimer: null,
      lastActivityCount: 0,
      activityDrawerOpen: false,
      drawerId: `browser-activity-drawer-${Math.random().toString(36).slice(2, 9)}`,
      escHandler: null
    }
  },
  computed: {
    activeSession() {
      // Prefer the live store copy: a panel opened from a session snapshot
      // must still update when the container starts/stops or the AI navigates.
      const id = this.sessionId ||
        this.params?.sessionId ||
        this.params?.params?.sessionId ||
        this.session?.id
      if (id) {
        const stored = this.$storex.browsers.sessionById(id)
        if (stored) return stored
      }
      return this.session ||
        this.params?.session ||
        this.params?.params?.session ||
        this.$storex.browsers.selectedSession
    },
    activeSessionId() {
      return this.activeSession?.id ||
        this.sessionId ||
        this.params?.sessionId ||
        this.params?.params?.sessionId ||
        null
    },
    isRunning() {
      return this.activeSession?.status === 'running'
    },
    vncEmbedUrl() {
      const session = this.activeSession
      if (!session) return ''
      if (session.vnc_path) return session.vnc_path
      if (!session.vnc_url) return ''
      try {
        const url = new URL(session.vnc_url)
        return url.pathname + url.search + url.hash
      } catch (e) {
        return session.vnc_url
      }
    },
    activity() {
      return this.$storex.browsers.activityFor(this.activeSessionId) || []
    },
    costInfo() {
      return this.$storex.browsers.costFor(this.activeSessionId)
    },
    recentActivity() {
      return this.activity.slice(-this.compact ? 8 : 20).reverse()
    },
    costLabel() {
      const cost = Number(this.costInfo?.total_cost_cxjcoins || 0)
      return this.formatCoins(cost)
    },
    liveBadge() {
      if (!this.activeSession) return 'No session'
      return this.isRunning ? 'Live' : this.activeSession.status
    },
    lastActivityLabel() {
      const last = this.activity[this.activity.length - 1]
      if (!last?.ts) return ''
      try {
        return new Date(last.ts).toLocaleString([], {
          month: 'numeric',
          day: 'numeric',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        })
      } catch (e) {
        return last.ts
      }
    }
  },
  watch: {
    activeSessionId: {
      immediate: true,
      handler() {
        this.restoreAddress()
        this.refreshSessionData()
      }
    },
    'activeSession.current_url'(value) {
      if (value && value !== this.address) this.address = value
    },
    'activeSession.status'(value) {
      if (value === 'running') {
        this.loadingFrame = true
        this.iframeKey += 1
      }
    },
    activityDrawerOpen(open) {
      // Refresh the audit trail when the drawer becomes visible
      if (open) this.refreshSessionData()
    }
  },
  mounted() {
    if (this.activeSessionId && !this.activeSession) {
      this.$storex.browsers.loadSessions()
    }
    this.startPolling()
    this.escHandler = (event) => {
      if (event.key === 'Escape' && this.activityDrawerOpen) {
        this.activityDrawerOpen = false
      }
    }
    window.addEventListener('keydown', this.escHandler)
  },
  beforeUnmount() {
    this.stopPolling()
    if (this.escHandler) {
      window.removeEventListener('keydown', this.escHandler)
      this.escHandler = null
    }
  },
  methods: {
    toggleActivityDrawer() {
      this.activityDrawerOpen = !this.activityDrawerOpen
    },
    restoreAddress() {
      const session = this.activeSession
      const url = session?.current_url || ''
      this.address = url === 'about:blank' ? '' : url
    },
    startPolling() {
      this.stopPolling()
      this.pollTimer = setInterval(() => {
        if (this.isRunning) this.refreshSessionData({ quiet: true })
      }, 7000)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async refreshSessionData({ quiet = false } = {}) {
      const sessionId = this.activeSessionId
      if (!sessionId) return
      const activity = await this.$storex.browsers.loadActivity({ sessionId, limit: 50 })
      // Cost aggregation reads the analytics store, so only refresh it when
      // something actually changed (or on an explicit, non-quiet refresh).
      if (!quiet || activity.length !== this.lastActivityCount) {
        await this.$storex.browsers.loadCost(sessionId)
        this.lastActivityCount = activity.length
      }
    },
    async refreshSession() {
      if (!this.activeSessionId) return
      try {
        await this.$storex.browsers.loadSessions()
        await this.refreshSessionData()
        this.iframeKey += 1
      } catch (error) {
        this.notify('error', error.message || 'Could not refresh session')
      }
    },
    reloadLiveView() {
      this.loadingFrame = true
      this.iframeKey += 1
    },
    onFrameLoaded() {
      this.loadingFrame = false
    },
    openLiveView() {
      if (!this.vncEmbedUrl) return
      window.open(this.vncEmbedUrl, '_blank', 'noopener,noreferrer')
    },
    async goToAddress() {
      const url = (this.address || '').trim()
      if (!url || !this.activeSessionId) return
      const target = /^([a-z]+:)?\/\//i.test(url) ? url : `https://${url}`
      this.navigating = true
      try {
        await this.$storex.browsers.navigate({ sessionId: this.activeSessionId, url: target })
        this.address = this.activeSession?.current_url || target
      } catch (error) {
        this.notify('error', error.message || 'Navigation failed')
      } finally {
        this.navigating = false
      }
    },
    async runPageAction(action, payload = {}) {
      if (!this.activeSessionId) return
      this.navigating = true
      try {
        await this.$storex.browsers.pageAction({
          sessionId: this.activeSessionId,
          action,
          payload
        })
        this.restoreAddress()
      } catch (error) {
        this.notify('error', error.message || `Action "${action}" failed`)
      } finally {
        this.navigating = false
      }
    },
    async takeScreenshot() {
      if (!this.activeSessionId) return
      this.screenshotLoading = true
      try {
        const response = await this.$storex.browsers.screenshot({
          sessionId: this.activeSessionId,
          fullPage: true
        })
        if (response?.success && response.screenshot) {
          this.screenshot = response.screenshot
          this.showScreenshot = true
        } else {
          this.notify('error', response?.error || 'Screenshot failed')
        }
      } catch (error) {
        this.notify('error', error.message || 'Screenshot failed')
      } finally {
        this.screenshotLoading = false
      }
    },
    async restartSession() {
      if (!this.activeSessionId) return
      try {
        await this.$storex.browsers.restartSession(this.activeSessionId)
        this.iframeKey += 1
      } catch (error) {
        this.notify('error', error.message || 'Could not restart session')
      }
    },
    async stopSession() {
      if (!this.activeSessionId) return
      try {
        await this.$storex.browsers.stopSession(this.activeSessionId)
      } catch (error) {
        this.notify('error', error.message || 'Could not stop session')
      }
    },
    notify(type, text) {
      this.$storex.ui.addNotification({ text, type })
    },
    actorClass(entry) {
      if (entry.actor === 'ai') return 'badge-secondary'
      if (entry.actor === 'user') return 'badge-primary'
      return 'badge-ghost'
    },
    actorLabel(entry) {
      if (entry.actor === 'ai') return 'AI'
      if (entry.actor === 'user') return 'User'
      return 'System'
    },
    formatTime(value) {
      if (!value) return ''
      try {
        return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      } catch (e) {
        return value
      }
    },
    formatCoins(value) {
      const number = Number(value || 0)
      if (!number) return '0'
      if (number < 0.001) return number.toExponential(2)
      return number.toFixed(number < 1 ? 4 : 2)
    },
    formatTokens(value) {
      return Number(value || 0).toLocaleString()
    }
  }
}
</script>
