<script setup>
import AppIcon from '../apps/AppIcon.vue'
import MicIndicator from '../meet/MicIndicator.vue'
</script>
<template>
  <div
    class="codx-tab flex gap-1 items-center justify-between px-1 py-0.5 border rounded-xl w-40 text-md"
    :draggable="!!chat"
    :class="{ 'cursor-grab active:cursor-grabbing': !!chat }"
    @dragstart="onDragStart"
  >
    <div class="w-4/5 flex gap-1 items-center truncate overflow-hidden">
      <!-- Pass loading state to AppIcon so it shows the ring inside the icon area -->
      <AppIcon :app="app || workspace" :loading="isUpdating" />
      <div class="grow truncate overflow-hidden">{{ tabName }}</div>
      <!-- Live camera indicator: shown on the Meet tab while the camera is on -->
      <i
        v-if="showCameraIcon"
        class="fa-solid fa-video fa-sm text-success shrink-0"
        title="Camera on"
        aria-label="Camera on"
      ></i>
      <!-- Live mic indicator: shown on the Meet tab while the mic is on; it
           pulses (via the shared component) when audio is being detected -->
      <MicIndicator
        v-if="showMicIcon"
        size="sm"
      />
    </div>
    <div class="click hover:text-warning shrink-0 mr-2" @click="onClose">
      <i class="fa-solid fa-xmark fa-sm"></i>
    </div>
  </div>
</template>
<script>

export default {
  props: ['params'],
  data() {
    return {
      project: null,
    }
  },
  async created() {
    this.project = this.$projects.allProjectsById[this.projectId]
  },
  computed: {
    chat() {
      const chatId = this.params?.params?.chat?.id
      return this.$storex.chats.chats[chatId]
    },
    // Read the app from the live store (not the static panel snapshot) so
    // runtime app-info updates — such as the active board name — are reflected
    // in the tab without recreating the panel.
    app() {
      const app = this.params?.params?.app
      return (app?.tabId && this.$storex.ui.openApps[app.tabId]) || app
    },
    // Workspace panels carry the raw workspace (name, path, …) in params under
    // the `workspace` key; fall back to the legacy `app` slot for old payloads.
    workspace() {
      return this.params?.params?.workspace || this.app
    },
    // Name of the board the panel is currently showing. The board view
    // publishes it into the app params when the active board changes.
    boardName() {
      return this.app?.params?.boardName || null
    },
    tabName() {
      // Precedence matters: chats and boards keep their name first, then the
      // workspace object, then the app name/title. Adding `app?.name` lets a
      // workspace opened with a name-only payload (no `workspace` in params)
      // still surface the workspace `name` instead of the generic title.
      return this.chat?.name ||
        this.boardName ||
        this.workspace?.name ||
        this.workspace?.title ||
        this.app?.name ||
        this.app?.title ||
        this.params?.params?.tabName
    },
    api() {
      return this.params.api
    },
    containerApi() {
      return this.params.containerApi
    },
    panel() {
      return this.api.panel
    },
    projectId() {
      return this.params?.params?.project_id
    },
    isUpdating() {
      return this.$storex.chats.isChatUpdating(this.chat?.id)
    },
    // Identify the Meet app panel — the app registry declares it with both an
    // `id`/`key` and a `component` named "meet".
    isMeet() {
      return this.app?.key === 'meet' || this.app?.component === 'meet'
    },
    // The meet this panel is bound to. Prefer the live app params, then the raw
    // panel params for restored/legacy layouts.
    meetId() {
      return this.app?.params?.meetId || this.params?.params?.meetId
    },
    // Whether the local camera is currently on.
    //
    // The global flag is authoritative: the Meet view sets it whenever the
    // camera stream starts/stops, so it also covers the pre-join lobby where no
    // meet exists in `activeMeets` yet (which is why the icon used to be missing
    // on the Meet home page). As a fallback we still inspect the active meet's
    // published local stream for a live video track.
    cameraOn() {
      if (this.$storex.meets.isLocalCameraOn) return true
      const meet = this.meetId && this.$storex.meets.activeMeets?.[this.meetId]
      const stream = meet?.localStream
      return !!(stream && stream.getVideoTracks && stream.getVideoTracks().length)
    },
    // Show the camera indicator only on the Meet tab while the camera is on.
    showCameraIcon() {
      return this.isMeet && this.cameraOn
    },
    // Whether the local microphone is currently capturing. Read straight from the
    // global meets store so it also works in the pre-join lobby.
    micOn() {
      return this.$storex.meets.isLocalMicOn
    },
    // Show the mic indicator only on the Meet tab while the mic is on. The
    // component adds the pulse automatically while audio is detected.
    showMicIcon() {
      return this.isMeet && this.micOn
    }
  },
  methods: {
    onDragStart(event) {
      // Only register a sprint task id when the tab is backed by a chat
      if (!this.chat) return
      event.dataTransfer.setData('sprintTaskId', this.chat.id)
      event.dataTransfer.effectAllowed = 'move'
    },
    onClose() {
      this.containerApi.removePanel(this.panel)
    }
  }
}
</script>