<script>
import NoVNC from '../NoVNC.vue'
import SaveComputerModal from './SaveComputerModal.vue'

/**
 * Live view + action bar for desktop computer sessions.
 *
 * Three viewing modes, all sharing the same machine with the AI:
 *  - `vnc`: Windows/macOS/remote sessions use the built-in noVNC viewer through
 *    a one-time WebSocket ticket (the AI drives the same RFB framebuffer).
 *  - `selkies`: Linux desktop containers expose the LinuxServer/Selkies web
 *    desktop under /computer/<id>/, embedded as an iframe.
 *  - `screenshot`: fallback for hosts where the live transport is unavailable;
 *    the image is clickable and refreshes on demand.
 *
 * The action bar sends the exact same actions the AI uses, so a click here and
 * a click from `computer_action` are indistinguishable to the machine.
 */
export default {
  name: 'DesktopViewer',
  components: { NoVNC, SaveComputerModal },
  props: {
    session: { type: Object, default: null },
    sessionId: { type: String, default: null },
    meetId: { type: String, default: null }
  },
  emits: ['ask-ai'],
  data() {
    return {
      screenshot: null,
      screenshotData: null,
      loadingShot: false,
      actionLoading: false,
      error: null,
      vncPath: null,
      vncPassword: '',
      viewerUser: '',
      viewerPassword: '',
      kasmPathBackup: null,
      kasmPathApplied: false,
      vncTicketError: null,
      pollFallback: false,
      typedText: '',
      command: '',
      showOcr: false,
      showKeys: false,
      showSaveModal: false,
      lastAction: null,
      pollTimer: null,
      desktopWidth: 1920,
      desktopHeight: 1080
    }
  },
  computed: {
    activeSession() {
      const id = this.sessionId || this.session?.id
      if (id) {
        const stored = this.$storex.browsers.sessionById(id)
        if (stored) return stored
      }
      return this.session
    },
    activeSessionId() {
      return this.activeSession?.id || null
    },
    kind() {
      return this.activeSession?.kind || 'linux'
    },
    kindLabel() {
      return this.activeSession?.kind_label || {
        linux: 'Linux', windows: 'Windows', macos: 'macOS', remote: 'Remote', browser: 'Browser'
      }[this.kind] || 'Computer'
    },
    kindIcon() {
      return {
        linux: 'fa-brands fa-linux',
        windows: 'fa-brands fa-windows',
        macos: 'fa-brands fa-apple',
        remote: 'fa-solid fa-network-wired',
        browser: 'fa-solid fa-compass'
      }[this.kind] || 'fa-solid fa-desktop'
    },
    isRunning() {
      return this.activeSession?.status === 'running'
    },
    isVnc() {
      return ['windows', 'macos', 'remote'].includes(this.kind) && !!this.activeSession?.vnc_host
    },
    isLinux() {
      return this.kind === 'linux'
    },
    isKasm() {
      return this.activeSession?.live_view === 'kasmvnc'
    },
    vncEmbedUrl() {
      const session = this.activeSession
      if (!session) return ''
      if (session.vnc_path) return session.vnc_path
      if (!session.vnc_url) return ''
      try {
        return new URL(session.vnc_url, window.location.origin).pathname
      } catch (error) {
        return session.vnc_url
      }
    },
    control() {
      return this.activeSession?.controller || 'ai'
    },
    userActive() {
      const until = this.activeSession?.user_active_until
      return !!until && new Date(until).getTime() > Date.now()
    },
    controllerLabel() {
      if (this.control === 'user') return 'You drive'
      if (this.userActive) return 'You active'
      if (this.control === 'none') return 'Paused'
      return 'AI drives'
    },
    hasShell() {
      return (this.activeSession?.capabilities || []).includes('shell')
    },
    canUseVnc() {
      return this.isVnc && this.isRunning
    },
    needsPolling() {
      return this.isRunning && (this.pollFallback || (!this.isVnc && !this.vncEmbedUrl))
    },
    statusText() {
      if (!this.activeSession) return 'No session'
      if (this.error) return this.error
      return `${this.desktopWidth}×${this.desktopHeight}`
    }
  },
  watch: {
    activeSessionId: {
      immediate: true,
      handler() {
        this.resetForSession()
      }
    },
    'activeSession.status': {
      handler() {
        this.resetForSession()
      }
    }
  },
  beforeUnmount() {
    this.stopPolling()
    this.restoreKasmPath()
  },
  methods: {
    resetForSession() {
      this.stopPolling()
      this.vncPath = null
      this.vncPassword = ''
      this.viewerUser = ''
      this.viewerPassword = ''
      this.vncTicketError = null
      this.pollFallback = false
      this.screenshot = null
      this.screenshotData = null
      this.error = null
      if (!this.activeSession) return
      this.desktopWidth = this.activeSession.desktop_width || 1920
      this.desktopHeight = this.activeSession.desktop_height || 1080
      if (this.isKasm) {
        this.applyKasmPath()
        this.loadViewerCredentials()
      } else {
        this.restoreKasmPath()
      }
      if (this.canUseVnc) {
        this.loadVncTicket()
      } else if (this.needsPolling) {
        this.takeScreenshot()
        this.startPolling()
      }
    },
    startPolling() {
      this.stopPolling()
      this.pollTimer = window.setInterval(() => {
        if (!this.actionLoading && this.needsPolling) this.takeScreenshot()
      }, 3500)
    },
    stopPolling() {
      if (this.pollTimer) {
        window.clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    applyKasmPath() {
      // KasmVNC derives its websocket URL from localStorage key "path" plus
      // the page host/port.  The page is served under /computer/<id>/, but the
      // default path is root /websockify; point it at the session's stripped
      // route so the browser and AI share the same page.
      if (!this.activeSessionId || this.kasmPathApplied) return
      try {
        this.kasmPathBackup = window.localStorage.getItem('path')
        this.kasmPathApplied = true
        window.localStorage.setItem(
          'path',
          `computer/${this.activeSessionId}/websockify`
        )
      } catch (error) {
        // localStorage can be unavailable in private/embedded contexts.
      }
    },
    restoreKasmPath() {
      if (!this.kasmPathApplied) return
      try {
        if (this.kasmPathBackup === null) window.localStorage.removeItem('path')
        else window.localStorage.setItem('path', this.kasmPathBackup)
      } catch (error) {
        // ignore
      }
      this.kasmPathBackup = null
      this.kasmPathApplied = false
    },
    async loadViewerCredentials() {
      if (!this.activeSessionId) return
      try {
        const response = await this.$storex.api.computers.viewerCredentials(this.activeSessionId)
        this.viewerUser = response?.user || 'kasm_user'
        this.viewerPassword = response?.password || ''
      } catch (error) {
        // KasmVNC may be configured without a password; the live view is
        // still usable and the error should not block it.
        this.viewerUser = ''
        this.viewerPassword = ''
      }
    },
    async copyViewerCredentials() {
      if (!this.viewerPassword) return
      try {
        await navigator.clipboard.writeText(`${this.viewerUser}:${this.viewerPassword}`)
        this.$storex.ui.addNotification({ text: 'KasmVNC credentials copied', type: 'success' })
      } catch (error) {
        this.$storex.ui.addNotification({ text: 'Could not copy credentials', type: 'error' })
      }
    },
    async loadVncTicket() {
      if (!this.activeSessionId) return
      this.vncTicketError = null
      try {
        const ticket = await this.$storex.api.computers.vncTicket(this.activeSessionId)
        this.vncPath = ticket?.socket_path || null
        this.vncPassword = ticket?.password || ''
      } catch (error) {
        this.vncTicketError = error?.response?.data?.detail || error.message || 'Could not open the live view'
        // Fall back to screenshot polling: the machine is still controllable
        // through the API even when the live transport is unavailable.
        this.pollFallback = true
        this.takeScreenshot()
        this.startPolling()
      }
    },
    async request(action, payload = {}) {
      if (!this.activeSessionId || !this.isRunning) return null
      this.actionLoading = true
      this.error = null
      try {
        const result = await this.$storex.api.computers.action(this.activeSessionId, {
          action,
          ...payload
        })
        this.lastAction = { action, at: new Date().toISOString() }
        if (result?.data?.image) {
          this.screenshot = result.data.image
          this.screenshotData = result.data
        }
        if (!this.isVnc && !this.vncEmbedUrl) {
          await this.takeScreenshot(true)
        }
        return result
      } catch (error) {
        this.error = error?.response?.data?.detail || error.message || `${action} failed`
        return null
      } finally {
        this.actionLoading = false
      }
    },
    async takeScreenshot(silent = false) {
      if (!this.activeSessionId || !this.isRunning) return
      if (!silent) this.loadingShot = true
      try {
        const result = await this.$storex.api.computers.screenshot(this.activeSessionId, {
          // Polling only needs the pixels; OCR is for manual/assistant reads.
          include_text: !silent,
          max_width: 1600
        })
        if (result?.screenshot) {
          this.screenshot = result.screenshot
          this.screenshotData = result.data || null
          if (result.data?.width) this.desktopWidth = result.data.width
          if (result.data?.height) this.desktopHeight = result.data.height
          this.error = null
        } else if (result?.error) {
          this.error = result.error
        }
      } catch (error) {
        this.error = error?.response?.data?.detail || error.message || 'Screenshot failed'
      } finally {
        this.loadingShot = false
      }
    },
    imageCoords(event) {
      const image = event.currentTarget
      const rect = image.getBoundingClientRect()
      const naturalWidth = image.naturalWidth || rect.width
      const naturalHeight = image.naturalHeight || rect.height
      if (!rect.width || !rect.height || !naturalWidth || !naturalHeight) return { x: 0, y: 0 }
      // object-contain letterboxes the image inside its box: map through the
      // actually rendered rectangle, not the element bounds.
      const scale = Math.min(rect.width / naturalWidth, rect.height / naturalHeight)
      const renderedWidth = naturalWidth * scale
      const renderedHeight = naturalHeight * scale
      const offsetX = (rect.width - renderedWidth) / 2
      const offsetY = (rect.height - renderedHeight) / 2
      const relativeX = (event.clientX - rect.left - offsetX) / renderedWidth
      const relativeY = (event.clientY - rect.top - offsetY) / renderedHeight
      const x = Math.round(relativeX * this.desktopWidth)
      const y = Math.round(relativeY * this.desktopHeight)
      return {
        x: Math.max(0, Math.min(this.desktopWidth - 1, x)),
        y: Math.max(0, Math.min(this.desktopHeight - 1, y))
      }
    },
    onImageClick(event) {
      if (!this.screenshot) return
      const { x, y } = this.imageCoords(event)
      this.request('click', { x, y })
    },
    onImageDoubleClick(event) {
      if (!this.screenshot) return
      const { x, y } = this.imageCoords(event)
      this.request('click', { x, y, clicks: 2 })
    },
    onImageRightClick(event) {
      if (!this.screenshot) return
      const { x, y } = this.imageCoords(event)
      this.request('click', { x, y, button: 'right' })
    },
    onImageWheel(event) {
      if (!this.screenshot) return
      const { x, y } = this.imageCoords(event)
      const direction = event.deltaY < 0 ? 'up' : 'down'
      this.request('scroll', { x, y, direction, amount: Math.max(1, Math.min(6, Math.round(Math.abs(event.deltaY) / 100) || 1)) })
    },
    async sendType() {
      const text = this.typedText
      if (!text) return
      const result = await this.request('type', { text })
      if (result) this.typedText = ''
    },
    sendKey(key) {
      this.request('key', { key })
    },
    sendKeyCombo(combo) {
      this.request('key', { key: combo })
    },
    async runCommand() {
      const command = this.command.trim()
      if (!command) return
      const result = await this.request('run_command', { command, timeout: 120 })
      if (result) this.command = ''
    },
    async takeControl() {
      await this.$storex.browsers.takeControl(this.activeSessionId)
    },
    async giveBack() {
      await this.$storex.browsers.giveBackControl(this.activeSessionId)
    },
    askAi() {
      this.$emit('ask-ai')
    },
    openExternal() {
      if (this.activeSession?.vnc_public_url) {
        window.open(this.activeSession.vnc_public_url, '_blank', 'noopener')
      } else if (this.isLinux && this.vncEmbedUrl) {
        window.open(this.vncEmbedUrl, '_blank', 'noopener')
      }
    }
  }
}
</script>

<template>
  <div class="flex flex-col h-full bg-base-100 overflow-hidden">
    <!-- Header -->
    <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 bg-base-200/70 flex-shrink-0">
      <div class="flex items-center gap-2 min-w-0 flex-1">
        <span class="relative flex h-2.5 w-2.5 flex-shrink-0">
          <span v-if="isRunning" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-60"></span>
          <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="isRunning ? 'bg-success' : 'bg-base-content/30'"></span>
        </span>
        <i :class="kindIcon" class="text-base-content/60" aria-hidden="true"></i>
        <h3 class="font-semibold truncate">{{ activeSession?.name || 'Computer session' }}</h3>
        <span class="badge badge-xs badge-outline">{{ kindLabel }}</span>
        <span class="badge badge-xs" :class="isRunning ? 'badge-success' : 'badge-warning'">
          {{ isRunning ? 'running' : (activeSession?.status || 'stopped') }}
        </span>
        <span class="badge badge-xs gap-1" :class="control === 'user' || userActive ? 'badge-warning' : 'badge-info badge-outline'">
          <i :class="control === 'user' ? 'fa-solid fa-hand' : 'fa-solid fa-robot'"></i>
          {{ controllerLabel }}
        </span>
        <span class="text-[11px] opacity-50 truncate hidden sm:inline">{{ statusText }}</span>
      </div>

      <button v-if="control === 'user'" class="btn btn-xs btn-primary" @click="giveBack">
        <i class="fa-solid fa-robot"></i><span class="hidden sm:inline">Give back</span>
      </button>
      <button v-else class="btn btn-xs btn-outline" :disabled="!isRunning" @click="takeControl">
        <i class="fa-solid fa-hand"></i><span class="hidden sm:inline">Take control</span>
      </button>
      <button
        v-if="isLinux && isRunning"
        class="btn btn-xs btn-ghost"
        title="Save this computer to the library"
        @click="showSaveModal = true"
      >
        <i class="fa-solid fa-floppy-disk"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Screenshot" :disabled="!isRunning || loadingShot" @click="takeScreenshot()">
        <span v-if="loadingShot" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-camera"></i>
      </button>
      <button v-if="activeSession?.vnc_public_url || (isLinux && vncEmbedUrl)" class="btn btn-xs btn-ghost" title="Open live view in a new tab" @click="openExternal">
        <i class="fa-solid fa-up-right-from-square"></i>
      </button>
    </div>

    <!-- Handoff banner -->
    <div v-if="activeSession?.handoff_reason" class="flex items-center gap-2 px-3 py-2 border-b border-warning/30 bg-warning/10 text-xs flex-shrink-0">
      <i class="fa-solid fa-hand text-warning"></i>
      <span class="flex-1 min-w-0"><strong>The AI needs you:</strong> <span class="opacity-80">{{ activeSession.handoff_reason }}</span></span>
      <button class="btn btn-xs btn-warning" @click="giveBack">I'm done — give back to AI</button>
    </div>

    <div
      v-if="isKasm"
      class="flex flex-wrap items-center gap-2 px-3 py-1.5 border-b border-base-content/10 bg-base-200/50 text-[11px] flex-shrink-0"
    >
      <i class="fa-solid fa-key text-base-content/40"></i>
      <span class="text-base-content/60">KasmVNC login</span>
      <code class="font-mono">{{ viewerUser || 'kasm_user' }}</code>
      <span class="text-base-content/30">/</span>
      <code class="font-mono">{{ viewerPassword || '…' }}</code>
      <button class="btn btn-ghost btn-xs" :disabled="!viewerPassword" @click="copyViewerCredentials">
        <i class="fa-regular fa-copy"></i> Copy
      </button>
      <span class="ml-auto text-base-content/40">Injected automatically for this session</span>
    </div>

    <!-- Live view -->
    <div class="flex-1 min-h-0 relative bg-black/90">
      <NoVNC
        v-if="canUseVnc && vncPath"
        :path="vncPath"
        :password="vncPassword || 'password'"
        :key="vncPath"
        class="w-full h-full"
      />
      <iframe
        v-else-if="isLinux && vncEmbedUrl && isRunning"
        :src="vncEmbedUrl"
        class="w-full h-full border-0 bg-black"
        title="Linux desktop live view"
        allow="clipboard-read; clipboard-write; fullscreen"
      ></iframe>
      <div v-else-if="screenshot" class="w-full h-full overflow-hidden flex items-center justify-center">
        <img
          :src="screenshot"
          class="max-w-full max-h-full object-contain cursor-crosshair select-none"
          alt="Computer screen"
          @click="onImageClick"
          @dblclick="onImageDoubleClick"
          @contextmenu.prevent="onImageRightClick"
          @wheel.prevent="onImageWheel"
        />
      </div>
      <div v-else class="absolute inset-0 flex flex-col items-center justify-center gap-2 text-base-content/60 text-sm">
        <span v-if="vncTicketError" class="text-error">{{ vncTicketError }}</span>
        <template v-else>
          <span class="loading loading-spinner loading-md"></span>
          <span>{{ isRunning ? 'Connecting to the desktop…' : 'Session is stopped' }}</span>
        </template>
      </div>
      <div v-if="actionLoading" class="absolute top-2 right-2 badge badge-primary badge-sm gap-1">
        <span class="loading loading-spinner loading-xs"></span> working…
      </div>
      <p v-if="error" class="absolute bottom-2 left-2 right-2 rounded bg-error/90 text-error-content text-[11px] px-2 py-1">
        {{ error }}
      </p>
    </div>

    <!-- Action bar -->
    <div class="border-t border-base-content/10 bg-base-200/60 flex-shrink-0">
      <div class="flex items-center gap-1.5 px-2 py-1.5 flex-wrap">
        <div class="flex items-center gap-1">
          <button class="btn btn-xs btn-ghost" title="Click the screen to click the desktop" @click="showKeys = !showKeys">
            <i class="fa-regular fa-keyboard"></i>
          </button>
          <button class="btn btn-xs btn-ghost" :class="showOcr && 'btn-active'" title="Show OCR text" @click="showOcr = !showOcr">
            <i class="fa-solid fa-font"></i>
          </button>
          <button class="btn btn-xs btn-ghost" title="Ask the AI about this screen" @click="askAi">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
          </button>
        </div>

        <div class="flex items-center gap-1 flex-1 min-w-[14rem]">
          <input
            v-model="typedText"
            type="text"
            class="input input-xs input-bordered flex-1 min-w-0"
            placeholder="Type text on the computer…"
            :disabled="!isRunning"
            @keyup.enter="sendType"
          />
          <button class="btn btn-xs btn-primary" :disabled="!isRunning || !typedText" @click="sendType">Type</button>
        </div>

        <div v-if="hasShell" class="flex items-center gap-1 flex-1 min-w-[16rem]">
          <input
            v-model="command"
            type="text"
            class="input input-xs input-bordered flex-1 min-w-0 font-mono"
            placeholder="Run a shell command…"
            :disabled="!isRunning"
            @keyup.enter="runCommand"
          />
          <button class="btn btn-xs" :disabled="!isRunning || !command.trim()" @click="runCommand">
            <i class="fa-solid fa-terminal"></i>
          </button>
        </div>
      </div>

      <div v-if="showKeys" class="flex items-center gap-1 px-2 pb-1.5 flex-wrap">
        <button v-for="key in ['Return', 'Tab', 'Escape', 'BackSpace', 'Delete', 'Up', 'Down', 'Left', 'Right']"
          :key="key" class="btn btn-xs btn-outline font-mono" :disabled="!isRunning" @click="sendKey(key)">
          {{ key }}
        </button>
        <span class="mx-1 text-base-content/30">|</span>
        <button v-for="combo in ['ctrl+c', 'ctrl+v', 'ctrl+z', 'ctrl+shift+t', 'alt+Tab', 'super', 'super+space']"
          :key="combo" class="btn btn-xs btn-outline font-mono" :disabled="!isRunning" @click="sendKeyCombo(combo)">
          {{ combo }}
        </button>
      </div>

      <div v-if="showOcr" class="max-h-32 overflow-auto border-t border-base-content/10 px-2 py-1.5">
        <pre class="whitespace-pre-wrap text-[11px] leading-snug text-base-content/70">{{ screenshotData?.text || '(no text detected — click the camera or press the AI button)' }}</pre>
      </div>
    </div>

    <Teleport to="body">
      <SaveComputerModal
        v-if="showSaveModal && activeSession"
        :key="activeSessionId"
        :session="activeSession"
        @close="showSaveModal = false"
        @saved="showSaveModal = false"
      />
    </Teleport>
  </div>
</template>
