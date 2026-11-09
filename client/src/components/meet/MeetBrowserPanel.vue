<template>
  <div class="flex h-full min-h-0 flex-col bg-[#141618] text-white">
    <!-- Header -->
    <div class="flex flex-shrink-0 items-center gap-2 border-b border-white/5 px-3 py-2">
      <i class="fa-solid fa-window-maximize text-primary" aria-hidden="true"></i>
      <div class="min-w-0 flex-1">
        <p class="truncate text-xs font-semibold">Shared browser</p>
        <p class="truncate text-[10px] text-white/40">
          {{ selectedSession ? selectedSession.name : 'Open a co-browsing session for everyone in the call' }}
        </p>
      </div>
      <span
        v-if="viewers.length"
        class="flex items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-white/60"
        :title="viewers.map(viewer => viewer.user?.name || viewer.user?.username).join(', ')"
      >
        <i class="fa-solid fa-users text-[9px]" aria-hidden="true"></i>
        {{ viewers.length }}
      </span>
      <button
        v-if="selectedSession"
        class="btn btn-ghost btn-xs btn-circle text-white/60 hover:text-white"
        title="Change browser session"
        aria-label="Change browser session"
        @click="showPicker = !showPicker"
      >
        <i class="fa-solid fa-arrow-right-arrow-left text-[10px]"></i>
      </button>
      <button
        class="btn btn-ghost btn-xs btn-circle text-white/60 hover:text-white"
        title="Refresh browser sessions"
        aria-label="Refresh browser sessions"
        :disabled="loading"
        @click="loadSessions"
      >
        <span v-if="loading" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-rotate text-[10px]"></i>
      </button>
    </div>

    <!-- Peer shared a session -->
    <div
      v-if="sharedInfo && sharedInfo.sessionId !== selectedId"
      class="flex flex-shrink-0 items-center gap-2 border-b border-primary/20 bg-primary/10 px-3 py-2 text-[11px]"
    >
      <i class="fa-solid fa-users text-primary" aria-hidden="true"></i>
      <span class="min-w-0 flex-1 truncate">
        <strong>{{ sharedInfo.user?.name || sharedInfo.user?.username || 'A participant' }}</strong>
        shared <strong>{{ sharedInfo.sessionName || 'a browser session' }}</strong>
      </span>
      <button class="btn btn-primary btn-xs" @click="openSession(sharedInfo.sessionId)">
        Join
      </button>
    </div>

    <!-- Session picker -->
    <div v-if="showPicker && selectedSession" class="flex-shrink-0 border-b border-white/5 bg-black/20 p-2">
      <select
        :value="selectedId"
        class="select select-bordered select-xs w-full bg-[#1c1e20] text-white"
        aria-label="Browser session"
        @change="openSession($event.target.value)"
      >
        <option v-for="session in sessions" :key="session.id" :value="session.id">
          {{ session.name }} — {{ session.status }}
        </option>
      </select>
    </div>

    <!-- Empty / picker -->
    <div v-if="!selectedSession" class="flex-1 overflow-y-auto p-3">
      <div v-if="loading" class="flex h-full items-center justify-center gap-2 text-xs text-white/50">
        <span class="loading loading-spinner loading-sm"></span>
        Loading sessions…
      </div>
      <div v-else-if="!sessions.length" class="flex h-full flex-col items-center justify-center gap-3 text-center">
        <i class="fa-regular fa-compass text-4xl text-white/20" aria-hidden="true"></i>
        <div>
          <p class="text-sm text-white/60">No browser sessions yet</p>
          <p class="mt-1 text-xs text-white/30">Create one in Computer sessions, then share it here.</p>
        </div>
      </div>
      <div v-else class="space-y-1.5">
        <p class="px-1 text-[10px] font-bold uppercase tracking-wide text-white/40">Open for the call</p>
        <button
          v-for="session in sessions"
          :key="session.id"
          class="flex w-full items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-2 py-2 text-left transition-colors hover:bg-white/10"
          @click="openSession(session.id)"
        >
          <span
            class="h-2 w-2 flex-shrink-0 rounded-full"
            :class="session.status === 'running' ? 'bg-success' : 'bg-white/20'"
          ></span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-xs font-medium">{{ session.name }}</span>
            <span class="block truncate text-[10px] text-white/40">
              {{ session.current_title || session.current_url || session.status }}
            </span>
          </span>
          <i class="fa-solid fa-chevron-right text-[9px] text-white/30" aria-hidden="true"></i>
        </button>
      </div>
    </div>

    <!-- The real co-browsing surface: viewer + chat + annotations -->
    <div v-else class="min-h-0 flex-1">
      <BrowserSessionPanel :meet-id="meetId" />
    </div>
  </div>
</template>

<script>
import BrowserSessionPanel from '@/components/browsers/BrowserSessionPanel.vue'
import { getCollabParticipants, onBrowserCollab } from '@/utils/browserCollab'

export default {
  name: 'MeetBrowserPanel',
  components: { BrowserSessionPanel },
  props: {
    meetId: { type: String, required: true },
    currentUser: { type: Object, default: null },
    // Announcement forwarded by MeetView so it is not missed when this tab is
    // not mounted yet.
    sharedSession: { type: Object, default: null }
  },
  data() {
    return {
      loading: false,
      selectedId: null,
      showPicker: false,
      sharedInfo: null,
      viewers: [],
      collabUnsubscribe: null,
      viewersTimer: null
    }
  },
  computed: {
    sessions() {
      return this.$storex.browsers.allSessions || []
    },
    selectedSession() {
      return this.selectedId ? this.$storex.browsers.sessionById(this.selectedId) : null
    }
  },
  watch: {
    selectedId(value) {
      if (value) this.$storex.browsers.selectSession(value)
    },
    sharedSession: {
      immediate: true,
      handler(value) {
        if (value?.kind === 'browser-session') this.handleSharedSession(value)
      }
    }
  },
  mounted() {
    const stored = this.$storex.browsers.selectedSession
    this.selectedId = stored?.id || null
    this.loadSessions()
    this.collabUnsubscribe = onBrowserCollab((event) => this.onCollabEvent(event))
    this.refreshViewers()
    this.viewersTimer = setInterval(() => this.refreshViewers(), 12000)
  },
  beforeUnmount() {
    if (this.collabUnsubscribe) this.collabUnsubscribe()
    if (this.viewersTimer) clearInterval(this.viewersTimer)
  },
  methods: {
    async loadSessions() {
      if (this.loading) return
      this.loading = true
      try {
        await this.$storex.browsers.loadSessions()
        if (this.selectedId && !this.$storex.browsers.sessionById(this.selectedId)) {
          this.selectedId = null
        }
      } finally {
        this.loading = false
      }
    },
    openSession(sessionId) {
      if (!sessionId) return
      this.selectedId = sessionId
      this.showPicker = false
      const session = this.$storex.browsers.sessionById(sessionId)
      if (session) this.$storex.browsers.selectSession(sessionId)
    },
    onCollabEvent(event) {
      if (!event || event.meetId !== this.meetId) return
      if (event.kind === 'presence') {
        this.refreshViewers()
      }
    },
    handleSharedSession(event) {
      if (!event?.sessionId || event.kind !== 'browser-session') return
      this.sharedInfo = event
      if (!this.selectedId) this.openSession(event.sessionId)
    },
    refreshViewers() {
      if (!this.meetId) return
      this.viewers = getCollabParticipants(this.meetId).filter((entry) => {
        if (!this.selectedId) return true
        return !entry.sessionId || entry.sessionId === this.selectedId
      })
    }
  }
}
</script>
