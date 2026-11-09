<script setup>
import ConfirmDialog from '../ConfirmDialog.vue'
import BrowserSessionCreateModal from './BrowserSessionCreateModal.vue'
import ComputerImageLibrary from './ComputerImageLibrary.vue'
</script>

<template>
  <!-- Collapsed: icon rail -->
  <div v-if="collapsed" class="flex flex-col items-center h-full w-full py-3 bg-base-100">
    <!-- Brand mark -->
    <div
      class="w-10 h-10 flex-shrink-0 rounded-xl bg-primary/15 text-primary flex items-center justify-center"
      title="Computer sessions"
      aria-hidden="true"
    >
      <i class="fa-solid fa-window-restore"></i>
    </div>

    <!-- Expand toggle -->
    <button
      @click="$emit('toggle-collapse')"
      class="btn btn-xs btn-ghost btn-circle mt-2 text-base-content/50 hover:text-base-content"
      title="Expand sidebar"
      aria-label="Expand sidebar"
      aria-expanded="false"
    >
      <i class="fa-solid fa-chevron-right text-[10px]"></i>
    </button>

    <div class="w-6 border-t border-base-content/10 mt-2 mb-2 flex-shrink-0"></div>

    <!-- Session rail -->
    <div class="flex-1 w-full min-h-0 overflow-y-auto flex flex-col items-center gap-1.5 px-2 pb-2">
      <div v-if="isLoading" class="flex items-center justify-center py-4">
        <div class="loading loading-spinner loading-xs"></div>
      </div>

      <template v-else>
        <button
          v-for="session in sessions"
          :key="session.id"
          @click="handleSelectSession(session.id)"
          class="relative w-10 h-10 flex-shrink-0 rounded-xl flex items-center justify-center text-sm font-semibold uppercase transition-colors duration-150 focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          :class="sessionItemClass(session)"
          :title="sessionTooltip(session)"
          :aria-label="`Select session ${session.name}`"
          :aria-current="selectedSessionId === session.id ? 'true' : 'false'"
        >
          {{ sessionInitial(session) }}
          <span
            v-if="session.status"
            class="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-base-100"
            :class="statusDotClass(session.status)"
            aria-hidden="true"
          ></span>
        </button>

        <div v-if="sessions.length === 0" class="py-3 text-base-content/40" title="No computer sessions yet">
          <i class="fa-solid fa-inbox"></i>
        </div>
      </template>
    </div>

    <div class="w-6 border-t border-base-content/10 mb-2 flex-shrink-0"></div>

    <!-- Bottom actions -->
    <div class="flex flex-col items-center gap-2 flex-shrink-0">
      <button
        @click="handleRailNewSession"
        class="btn btn-sm btn-primary btn-circle"
        title="New session"
        aria-label="New computer session"
      >
        <i class="fa-solid fa-plus"></i>
      </button>
      <button
        @click="browseImageLibrary"
        class="btn btn-sm btn-ghost btn-circle text-base-content/50 hover:text-base-content"
        title="Browse the computer image library"
        aria-label="Browse the computer image library"
      >
        <i class="fa-solid fa-images"></i>
      </button>
      <button
        @click="reloadSessions"
        class="btn btn-sm btn-ghost btn-circle text-base-content/50 hover:text-base-content"
        title="Reload sessions"
        aria-label="Reload computer sessions"
      >
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>
    </div>
  </div>

  <!-- Expanded -->
  <div v-else class="flex flex-col h-full bg-base-100 p-3 pb-4">
    <!-- Header (brand row with collapse toggle) -->
    <div class="flex items-center gap-2.5 px-1 flex-shrink-0">
      <div class="w-10 h-10 flex-shrink-0 rounded-xl bg-primary/15 text-primary flex items-center justify-center">
        <i class="fa-solid fa-window-restore"></i>
      </div>
      <h2 class="text-base font-bold truncate flex-1">Computer sessions</h2>
      <button
        @click="$emit('toggle-collapse')"
        class="btn btn-xs btn-ghost btn-circle flex-shrink-0 text-base-content/50 hover:text-base-content"
        title="Collapse sidebar"
        aria-label="Collapse sidebar"
        aria-expanded="true"
      >
        <i class="fa-solid fa-chevron-left text-[10px]"></i>
      </button>
    </div>

    <div class="border-t border-base-content/10 mt-3 mb-2 flex-shrink-0"></div>

    <!-- Sessions List -->
    <div class="flex-1 min-h-0 overflow-y-auto mt-1 space-y-0.5">
      <div v-if="isLoading" class="flex items-center justify-center py-8">
        <div class="loading loading-spinner loading-sm"></div>
        <span class="ml-2 text-sm">Loading sessions...</span>
      </div>

      <div v-else-if="sessions.length === 0" class="text-center py-8 text-base-content/50">
        <i class="fa-solid fa-inbox text-2xl mb-2 block"></i>
        <p class="text-sm">No computer sessions yet</p>
      </div>

      <template v-else>
        <div
          v-for="session in sessions"
          :key="session.id"
          class="group flex items-center gap-1 pl-0 pr-1 rounded-full transition-colors duration-150"
          :class="sessionRowClass(session)"
        >
          <button
            @click="handleSelectSession(session.id)"
            class="flex-1 min-w-0 flex items-center gap-2.5 pl-3 pr-2 py-2 text-left rounded-full focus:outline-none focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary"
            :aria-label="`Select session ${session.name}`"
            :aria-current="selectedSessionId === session.id ? 'true' : 'false'"
          >
            <span
              class="w-7 h-7 flex-shrink-0 rounded-lg flex items-center justify-center text-[11px] font-semibold uppercase"
              :class="selectedSessionId === session.id ? 'bg-primary/20 text-primary' : 'bg-base-200 text-base-content/70'"
            >
              {{ sessionInitial(session) }}
            </span>
            <span class="flex-1 min-w-0">
              <span
                class="block text-sm truncate"
                :class="selectedSessionId === session.id ? 'font-semibold text-primary' : 'text-base-content/80'"
              >
                {{ session.name }}
              </span>
              <!-- Kind + project mapping of the session (falls back to its URL) -->
              <span
                class="flex items-center gap-1 text-[11px] text-base-content/50"
                :title="sessionTooltip(session)"
              >
                <i :class="kindIcon(session)" class="text-[9px] flex-shrink-0" aria-hidden="true"></i>
                <span class="badge badge-xs badge-ghost px-1">{{ kindLabel(session) }}</span>
                <span class="truncate">{{ sessionSubtitle(session) }}</span>
              </span>
            </span>
            <span
              v-if="session.status"
              class="w-2 h-2 flex-shrink-0 rounded-full"
              :class="statusDotClass(session.status)"
              :title="session.status"
              aria-hidden="true"
            ></span>
          </button>

          <!-- Actions: quiet until hover/focus on desktop, always visible on touch -->
          <div class="flex items-center gap-0.5 flex-shrink-0 opacity-100 md:opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
            <button
              @click="handleRunSession(session.id, $event)"
              class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-success"
              title="Run session"
              :aria-label="`Run session ${session.name}`"
            >
              <i class="fa-solid fa-play text-[10px]"></i>
            </button>
            <button
              @click="handleEditSession(session.id, $event)"
              class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-info"
              title="Edit session"
              :aria-label="`Edit session ${session.name}`"
            >
              <i class="fa-solid fa-gear text-[10px]"></i>
            </button>
            <button
              @click="handleDeleteSession(session.id, $event)"
              class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-error"
              title="Delete session"
              :aria-label="`Delete session ${session.name}`"
            >
              <i class="fa-solid fa-trash text-[10px]"></i>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- Footer actions -->
    <div class="grid grid-cols-2 gap-2 flex-shrink-0 pt-3 mt-2 border-t border-base-content/10">
      <button @click="browseImageLibrary" class="btn btn-sm btn-outline gap-1">
        <i class="fa-solid fa-images"></i>
        Library
      </button>
      <button @click="toggleNewForm" class="btn btn-sm btn-primary gap-1">
        <i class="fa-solid fa-plus"></i>
        New session
      </button>
    </div>
  </div>

  <!-- New session settings (folder mapping + downloads) -->
  <BrowserSessionCreateModal v-if="showCreateModal" />

  <!-- Standalone image library: browse without starting from the form -->
  <Teleport to="body">
    <ComputerImageLibrary
      v-if="showImageLibrary"
      kind="linux"
      @select="onLibraryImageSelected"
      @close="showImageLibrary = false"
    />
  </Teleport>

  <!-- Delete confirmation modal -->
  <ConfirmDialog
    v-if="deleteTarget"
    title="Delete session"
    :message="`Delete computer session '${deleteTarget.name}'?`"
    hint="The session, its profile and its desktop state will be removed. This cannot be undone."
    icon="fa-trash"
    icon-class="text-error"
    confirm-label="Delete"
    confirm-icon="fa-trash"
    confirm-class="btn-error"
    :busy="deleting"
    @confirm="confirmDeleteSession"
    @cancel="deleteTarget = null"
  />
</template>

<script>
export default {
  name: 'BrowserSessionList',
  components: {
    ConfirmDialog,
    BrowserSessionCreateModal
  },
  props: {
    collapsed: {
      type: Boolean,
      default: false
    }
  },
  emits: ['toggle-collapse'],
  data() {
    return {
      deleteTarget: null,
      deleting: false,
      showImageLibrary: false
    }
  },
  computed: {
    sessions() {
      return this.$storex.browsers.allSessions
    },
    selectedSessionId() {
      return this.$storex.browsers.selectedSessionId
    },
    isLoading() {
      return this.$storex.browsers.isLoading
    },
    // The modal is owned by the store so both the rail and the footer button
    // (and any other entry point) open the very same dialog.
    showCreateModal() {
      return this.$storex.browsers.showNewSessionForm
    }
  },
  methods: {
    sessionInitial(session) {
      const label = (session.name || session.current_url || '?').trim()
      return label.charAt(0)
    },
    kindLabel(session) {
      return session.kind_label || {
        browser: 'Browser',
        linux: 'Linux',
        windows: 'Windows',
        macos: 'macOS',
        remote: 'Remote'
      }[session.kind || 'browser'] || 'Computer'
    },
    kindIcon(session) {
      return {
        browser: 'fa-solid fa-compass',
        linux: 'fa-brands fa-linux',
        windows: 'fa-brands fa-windows',
        macos: 'fa-brands fa-apple',
        remote: 'fa-solid fa-network-wired'
      }[session.kind || 'browser'] || 'fa-solid fa-desktop'
    },
    /**
     * One-line description of what the session can see: the configured folder
     * mapping wins, the page URL is only a fallback.
     */
    sessionSubtitle(session) {
      const folders = session.folders || session.shared_folders || []
      if (folders.length === 1) {
        return folders[0].mount_path || folders[0].host_path || '1 folder'
      }
      if (folders.length > 1) {
        return `${folders.length} folders · ${session.home_path || ''}`.trim()
      }
      if (session.downloads_path) {
        return `Shared · ${session.guest_share_path || session.downloads_mount || session.downloads_path}`
      }
      if (session.kind === 'remote') {
        return `${session.vnc_host || 'remote'}:${session.vnc_port || 5900}`
      }
      return session.current_url || 'No project files'
    },
    /** Full mapping, shown as the row tooltip. */
    sessionTooltip(session) {
      const lines = [session.name || 'Computer session']
      const folders = (session.folders || session.shared_folders || [])
        .map(folder => folder.mount_path || folder.host_path)
        .filter(Boolean)
      lines.push(folders.length ? `Folders: ${folders.join(', ')}` : 'Folders: none')
      if (session.downloads_mount || session.downloads_path) {
        lines.push(`Downloads: ${session.downloads_mount || session.downloads_path}`)
      }
      const resources = []
      if (session.cpu_cores) resources.push(`${session.cpu_cores} vCPU`)
      if (session.ram_size) resources.push(`${session.ram_size} RAM`)
      if (session.disk_size) resources.push(`${session.disk_size} disk`)
      if (resources.length) lines.push(`Resources: ${resources.join(' · ')}`)
      if (session.image) lines.push(`Image: ${session.image}`)
      return lines.join('\n')
    },
    sessionItemClass(session) {
      if (this.selectedSessionId === session.id) {
        return 'bg-primary/10 text-primary'
      }
      return 'text-base-content/60 hover:bg-base-200 hover:text-base-content'
    },
    sessionRowClass(session) {
      if (this.selectedSessionId === session.id) {
        return 'bg-primary/10'
      }
      return 'hover:bg-base-200'
    },
    statusDotClass(status) {
      if (status === 'running') return 'bg-success'
      if (status === 'stopped') return 'bg-warning'
      return 'bg-base-content/30'
    },
    reloadSessions() {
      this.$storex.browsers.loadSessions()
    },
    handleRailNewSession() {
      // The dialog is self contained: it works from the collapsed rail too, so
      // the sidebar no longer has to expand to create a session.
      this.$storex.browsers.toggleNewSessionForm(true)
    },
    handleSelectSession(sessionId) {
      this.$storex.browsers.selectSession(sessionId)
    },
    handleDeleteSession(sessionId, event) {
      event.stopPropagation()
      this.deleteTarget = this.sessions.find(session => session.id === sessionId) || null
    },
    async confirmDeleteSession() {
      if (!this.deleteTarget) return

      this.deleting = true
      try {
        await this.$storex.browsers.deleteSession(this.deleteTarget.id)
        this.deleteTarget = null
      } catch (error) {
        console.error('Failed to delete session:', error)
      } finally {
        this.deleting = false
      }
    },
    async handleRunSession(sessionId, event) {
      event.stopPropagation()
      try {
        await this.$storex.browsers.runSession(sessionId)
      } catch (error) {
        console.error('Failed to run session:', error)
      }
    },
    handleEditSession(sessionId, event) {
      event.stopPropagation()
      this.$storex.browsers.startEditingSession(sessionId)
    },
    toggleNewForm() {
      this.$storex.browsers.toggleNewSessionForm(true)
    },
    browseImageLibrary() {
      this.showImageLibrary = true
    },
    onLibraryImageSelected(image) {
      this.showImageLibrary = false
      this.$storex.browsers.openNewSessionFromLibrary(image)
    }
  },
  inject: ['$storex'],
  mounted() {
    this.$storex.browsers.loadSessions()
  }
}
</script>