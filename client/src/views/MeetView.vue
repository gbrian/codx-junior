<script setup>
import MeetHeader from '@/components/meet/MeetHeader.vue'
import MeetControls from '@/components/meet/MeetControls.vue'
import MeetParticipants from '@/components/meet/MeetParticipants.vue'
import MeetInviteModal from '@/components/meet/MeetInviteModal.vue'
import MeetSettingsPanel from '@/components/meet/MeetSettingsPanel.vue'
import MeetSettingsModal from '@/components/meet/MeetSettingsModal.vue'
import ChatView from '@/views/ChatView.vue'
</script>

<template>
  <div class="flex h-full overflow-hidden bg-[#1c1e20]">
    <!-- Main Meet Area -->
    <div class="flex-1 flex flex-col min-w-0">

      <!-- Header (always shown) -->
      <MeetHeader
        :meet="currentMeet"
        :meetId="activeMeetId"
        @close="onClose"
        @settings="showCallSettings = true"
      />

      <!-- Content -->
      <div class="flex-1 flex flex-col min-h-0 overflow-hidden">

        <!-- ─────────────────────────────────────────── -->
        <!-- PRE-JOIN LOBBY                              -->
        <!-- ─────────────────────────────────────────── -->
        <div v-if="!currentMeet" class="flex-1 flex items-center justify-center p-6 overflow-auto">
          <div class="flex flex-col lg:flex-row items-center gap-10 w-full max-w-4xl">

            <!-- Left: Camera preview tile -->
            <div class="flex-1 w-full max-w-xl">
              <div class="relative w-full aspect-video rounded-2xl overflow-hidden bg-[#3c4043] shadow-xl">
                <video
                  v-if="localCameraEnabled && localCameraStream"
                  ref="localVideo"
                  autoplay
                  muted
                  playsinline
                  class="w-full h-full object-cover scale-x-[-1]"
                ></video>
                <div v-else class="absolute inset-0 flex items-center justify-center">
                  <div class="w-20 h-20 rounded-full bg-white/10 flex items-center justify-center text-white/30">
                    <i class="fa-solid fa-user text-4xl"></i>
                  </div>
                </div>
                <div v-if="isStartingCamera" class="absolute inset-0 flex items-center justify-center bg-black/50">
                  <span class="loading loading-spinner loading-md text-primary"></span>
                </div>
                <div class="absolute bottom-3 left-3">
                  <span class="text-white text-sm font-medium drop-shadow-lg bg-black/40 px-2 py-1 rounded-lg backdrop-blur-sm">
                    {{ currentUserName }}
                  </span>
                </div>
                <div v-if="localMuted" class="absolute top-3 right-3">
                  <div class="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center shadow-lg">
                    <i class="fa-solid fa-microphone-slash text-white text-xs"></i>
                  </div>
                </div>
              </div>

              <!-- Camera / Mic toggle bar -->
              <div class="flex items-center justify-center gap-3 mt-4">
                <button
                  @click="toggleLocalMic"
                  class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95 shadow-md"
                  :class="localMuted ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-[#3c4043] hover:bg-[#4c5055] text-white'"
                  :title="localMuted ? 'Unmute' : 'Mute'"
                >
                  <i class="fa-solid text-base" :class="localMuted ? 'fa-microphone-slash' : 'fa-microphone'"></i>
                </button>
                <button
                  @click="toggleLocalCamera"
                  class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95 shadow-md"
                  :class="localCameraEnabled ? 'bg-[#3c4043] hover:bg-[#4c5055] text-white' : 'bg-red-500 hover:bg-red-600 text-white'"
                  :title="localCameraEnabled ? 'Turn off camera' : 'Turn on camera'"
                >
                  <i class="fa-solid text-base" :class="localCameraEnabled ? 'fa-video' : 'fa-video-slash'"></i>
                </button>
                <button
                  @click="showCallSettings = true"
                  class="w-12 h-12 rounded-full bg-[#3c4043] hover:bg-[#4c5055] flex items-center justify-center text-white transition-all duration-150 active:scale-95 shadow-md"
                  title="Settings"
                >
                  <i class="fa-solid fa-sliders text-base"></i>
                </button>
              </div>
            </div>

            <!-- Right: Join panel -->
            <div class="flex flex-col items-center gap-6 text-center lg:text-left lg:items-start w-full max-w-xs">
              <div class="space-y-2">
                <h1 class="text-2xl font-bold text-white">Ready to join?</h1>
                <p class="text-sm text-white/50">No one else is here</p>
              </div>
              <div class="flex flex-col gap-3 w-full">
                <button @click="startNewMeet" class="btn btn-primary gap-2 rounded-full px-6">
                  <i class="fa-solid fa-phone"></i>
                  Start call
                </button>
                <button
                  @click="showInviteModal = true"
                  class="btn btn-ghost gap-2 rounded-full px-6 border border-white/20 text-white/70 hover:text-white"
                >
                  <i class="fa-solid fa-link"></i>
                  Share invite
                </button>
              </div>
              <div v-if="recentMeets.length > 0" class="w-full space-y-2 pt-2">
                <div class="text-xs font-semibold text-white/30 uppercase tracking-wider">Recent</div>
                <button
                  v-for="meet in recentMeets"
                  :key="meet.meetId"
                  @click="joinMeet(meet.meetId)"
                  class="w-full flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-left"
                >
                  <div>
                    <div class="font-medium text-sm text-white">{{ meet.name }}</div>
                    <div class="text-xs text-white/40">{{ formatDate(meet.endedAt) }}</div>
                  </div>
                  <i class="fa-solid fa-arrow-right text-white/30 text-xs"></i>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ─────────────────────────────────────────── -->
        <!-- ACTIVE CALL VIEW                            -->
        <!-- ─────────────────────────────────────────── -->
        <div v-else class="flex-1 flex flex-col min-h-0">

          <!-- Participants grid area -->
          <div class="flex-1 p-4 overflow-auto">

            <!-- Duration badge -->
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2 text-sm">
                <span class="badge badge-success gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
                  Live
                </span>
                <span class="text-white/50 text-xs font-mono">{{ formattedDuration }}</span>
              </div>
              <button
                @click="showCallSettings = true"
                class="btn btn-ghost btn-xs btn-circle text-white/40 hover:text-white"
              >
                <i class="fa-solid fa-sliders"></i>
              </button>
            </div>

            <!-- Video tiles grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">

              <!-- Self camera tile -->
              <div class="relative aspect-video rounded-2xl overflow-hidden bg-[#3c4043]">
                <video
                  v-if="localCameraEnabled && localCameraStream"
                  ref="localVideoInCall"
                  autoplay
                  muted
                  playsinline
                  class="w-full h-full object-cover scale-x-[-1]"
                ></video>
                <div v-else class="absolute inset-0 flex items-center justify-center">
                  <div class="w-14 h-14 rounded-full bg-white/10 flex items-center justify-center">
                    <i class="fa-solid fa-user text-2xl text-white/30"></i>
                  </div>
                </div>
                <div class="absolute bottom-2 left-2">
                  <span class="text-white text-xs bg-black/50 px-2 py-0.5 rounded-md backdrop-blur-sm">
                    {{ currentUserName }} (You)
                  </span>
                </div>
                <div v-if="localMuted" class="absolute top-2 right-2 w-6 h-6 rounded-full bg-red-500 flex items-center justify-center">
                  <i class="fa-solid fa-microphone-slash text-white text-xs"></i>
                </div>
              </div>

              <!-- ─── Screen share tiles (one per active share) ─── -->
              <div
                v-for="share in localScreenStreams"
                :key="share.id"
                class="relative aspect-video rounded-2xl overflow-hidden bg-[#3c4043] ring-2 ring-primary/60"
              >
                <video
                  :ref="el => bindScreenShareVideo(el, share.id)"
                  autoplay
                  muted
                  playsinline
                  class="w-full h-full object-contain bg-black"
                ></video>

                <!-- Label bottom-left -->
                <div class="absolute bottom-2 left-2 flex items-center gap-1.5">
                  <span class="text-white text-xs bg-primary/70 px-2 py-0.5 rounded-md backdrop-blur-sm flex items-center gap-1">
                    <i class="fa-solid fa-share-from-square text-xs"></i>
                    {{ share.label || 'Screen' }}
                  </span>
                </div>

                <!-- Stop button top-right (×) -->
                <div class="absolute top-2 right-2">
                  <button
                    @click="stopScreenShare(share.id)"
                    class="w-7 h-7 rounded-full bg-black/60 hover:bg-red-500 flex items-center justify-center text-white transition-all duration-150 backdrop-blur-sm"
                    title="Stop this share"
                  >
                    <i class="fa-solid fa-xmark text-xs"></i>
                  </button>
                </div>
              </div>

              <!-- Remote participant tiles (mocked) -->
              <div
                v-for="participant in remoteParticipants"
                :key="participant"
                class="relative aspect-video rounded-2xl overflow-hidden bg-[#3c4043] flex items-center justify-center"
              >
                <div class="w-14 h-14 rounded-full bg-primary/30 flex items-center justify-center">
                  <i class="fa-solid fa-user text-2xl text-primary/70"></i>
                </div>
                <div class="absolute bottom-2 left-2">
                  <span class="text-white text-xs bg-black/50 px-2 py-0.5 rounded-md backdrop-blur-sm">{{ participant }}</span>
                </div>
              </div>
            </div>

            <!-- Participants list (compact) -->
            <MeetParticipants :meet="currentMeet" />
          </div>

          <!-- ─── Call controls bar ─── -->
          <div class="shrink-0 flex items-center justify-between px-6 py-4 bg-[#1c1e20] border-t border-white/5">
            <!-- Duration (left) -->
            <div class="text-xs text-white/40 font-mono w-24">{{ formattedDuration }}</div>

            <!-- Center controls -->
            <div class="flex items-center gap-3">
              <!-- Mic -->
              <button
                @click="onToggleMute"
                class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
                :class="isMuted ? 'bg-red-500 hover:bg-red-600' : 'bg-[#3c4043] hover:bg-[#4c5055]'"
                :title="isMuted ? 'Unmute' : 'Mute'"
              >
                <i class="fa-solid text-white text-base" :class="isMuted ? 'fa-microphone-slash' : 'fa-microphone'"></i>
              </button>

              <!-- Camera -->
              <button
                @click="toggleLocalCamera"
                class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
                :class="localCameraEnabled ? 'bg-[#3c4043] hover:bg-[#4c5055]' : 'bg-red-500 hover:bg-red-600'"
                :title="localCameraEnabled ? 'Turn off camera' : 'Turn on camera'"
              >
                <i class="fa-solid text-white text-base" :class="localCameraEnabled ? 'fa-video' : 'fa-video-slash'"></i>
              </button>

              <!-- ─── Screen share button — always adds a NEW share ─── -->
              <div class="relative">
                <button
                  @click="startScreenShare"
                  :disabled="isRequestingScreen"
                  class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
                  :class="isScreenSharing
                    ? 'bg-primary hover:bg-primary/80'
                    : 'bg-[#3c4043] hover:bg-[#4c5055]'"
                  :title="isScreenSharing ? 'Share another screen/tab' : 'Share screen'"
                >
                  <span v-if="isRequestingScreen" class="loading loading-spinner loading-xs text-white"></span>
                  <i v-else class="fa-solid fa-share-from-square text-white text-base"></i>
                </button>

                <!-- Count badge when >1 shares active -->
                <span
                  v-if="localScreenStreams.length > 1"
                  class="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full border border-[#1c1e20] flex items-center justify-center text-white text-[9px] font-bold"
                >
                  {{ localScreenStreams.length }}
                </span>

                <!-- Pulse dot when at least 1 share active -->
                <span
                  v-else-if="isScreenSharing"
                  class="absolute -top-0.5 -right-0.5 w-3 h-3 bg-primary rounded-full border-2 border-[#1c1e20] animate-pulse"
                ></span>
              </div>

              <!-- Settings -->
              <button
                @click="showCallSettings = true"
                class="w-12 h-12 rounded-full bg-[#3c4043] hover:bg-[#4c5055] flex items-center justify-center text-white transition-all duration-150 active:scale-95"
                title="Settings"
              >
                <i class="fa-solid fa-sliders text-base"></i>
              </button>

              <!-- Invite -->
              <button
                @click="showInviteModal = true"
                class="w-12 h-12 rounded-full bg-[#3c4043] hover:bg-[#4c5055] flex items-center justify-center text-white transition-all duration-150 active:scale-95"
                title="Invite"
              >
                <i class="fa-solid fa-user-plus text-base"></i>
              </button>

              <!-- Chat -->
              <button
                @click="openMeetChat"
                class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
                :class="activePanelTab === 'chat' && !panelCollapsed
                  ? 'bg-primary hover:bg-primary/80'
                  : 'bg-[#3c4043] hover:bg-[#4c5055]'"
                title="Meet chat"
              >
                <i class="fa-solid fa-comments text-white text-base"></i>
              </button>

              <!-- People panel toggle -->
              <button
                @click="togglePanel('people')"
                class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
                :class="activePanelTab === 'people' && !panelCollapsed
                  ? 'bg-primary hover:bg-primary/80'
                  : 'bg-[#3c4043] hover:bg-[#4c5055]'"
                :title="panelCollapsed ? 'Show participants' : 'Hide participants'"
              >
                <i class="fa-solid fa-users text-white text-base"></i>
              </button>
            </div>

            <!-- Right: Leave -->
            <div class="flex items-center gap-2 w-24 justify-end">
              <button @click="onLeaveMeet" class="btn btn-sm btn-error rounded-full px-4 gap-1.5">
                <i class="fa-solid fa-phone-slash"></i>
                Leave
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ─────────────────────────────────────────── -->
    <!-- Right Panel: People / Chat                  -->
    <!-- ─────────────────────────────────────────── -->
    <transition name="panel-slide">
      <div
        v-if="currentMeet && !panelCollapsed"
        class="border-l border-white/5 flex flex-col bg-[#202124] shrink-0"
        :style="{ width: activePanelWidth + '%' }"
      >
        <!-- Tab bar -->
        <div class="flex items-center border-b border-white/5 bg-[#1c1e20]">
          <button
            @click="activePanelTab = 'people'"
            :class="activePanelTab === 'people' ? 'border-b-2 border-primary text-white' : 'border-b-2 border-transparent text-white/40'"
            class="flex-1 btn btn-ghost btn-sm rounded-none gap-2 text-xs font-semibold"
          >
            <i class="fa-solid fa-users"></i>
            People
          </button>
          <button
            @click="activePanelTab = 'chat'"
            :class="activePanelTab === 'chat' ? 'border-b-2 border-primary text-white' : 'border-b-2 border-transparent text-white/40'"
            class="flex-1 btn btn-ghost btn-sm rounded-none gap-2 text-xs font-semibold"
          >
            <i class="fa-solid fa-comments"></i>
            Chat
          </button>
          <button
            @click="panelCollapsed = true"
            class="btn btn-ghost btn-sm btn-circle text-white/40 hover:text-white mr-1"
            title="Close panel"
          >
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="flex-1 min-h-0 overflow-hidden">
          <MeetParticipants v-if="activePanelTab === 'people'" :meet="currentMeet" />
          <div v-if="activePanelTab === 'chat'" class="flex flex-col h-full">
            <div v-if="!meetChatData" class="flex-1 flex flex-col items-center justify-center gap-4 p-6 text-center">
              <div class="w-14 h-14 rounded-full bg-white/5 flex items-center justify-center">
                <i class="fa-solid fa-comments text-2xl text-white/30"></i>
              </div>
              <div>
                <p class="text-sm text-white/60 font-medium">No chat for this meet yet</p>
                <p class="text-xs text-white/30 mt-1">Create a chat to collaborate with participants</p>
              </div>
              <button @click="createMeetChat" :disabled="isCreatingChat" class="btn btn-primary btn-sm gap-2">
                <span v-if="isCreatingChat" class="loading loading-spinner loading-xs"></span>
                <i v-else class="fa-solid fa-plus"></i>
                Create Meet Chat
              </button>
            </div>
            <ChatView
              v-else
              :chat="meetChatData"
              :kanban="null"
              :params="{ params: { chat: meetChatData } }"
              class="h-full"
            />
          </div>
        </div>
      </div>
    </transition>

    <!-- Modals -->
    <MeetInviteModal
      v-if="showInviteModal"
      :meetId="activeMeetId"
      @close="showInviteModal = false"
    />

    <MeetSettingsModal
      v-if="showCallSettings"
      :currentSettings="callSettings"
      @close="showCallSettings = false"
      @save="onSaveCallSettings"
    />
  </div>
</template>

<script>
export default {
  name: 'MeetView',
  data() {
    return {
      activeMeetId: null,
      isMuted: false,
      showInviteModal: false,
      showCallSettings: false,
      callSettings: {},
      activePanelWidth: 30,
      activePanelTab: 'people',
      panelCollapsed: true,
      isResizingPanel: false,
      startXPanel: 0,
      // Local media
      localMuted: false,
      localCameraEnabled: false,
      localCameraStream: null,
      isStartingCamera: false,
      cameraError: null,
      // Multi-screen share: array of { id, stream, label }
      localScreenStreams: [],
      isRequestingScreen: false,
      // Chat
      isCreatingChat: false
    }
  },
  computed: {
    currentMeet() {
      return this.$storex.meets.meetForId(this.activeMeetId)
    },
    recentMeets() {
      return [...this.$storex.meets.recentMeetHistory].reverse().slice(0, 5)
    },
    currentUserName() {
      return this.$storex.users.user?.username || 'You'
    },
    remoteParticipants() {
      if (!this.currentMeet) return []
      const me = this.currentUserName
      return (this.currentMeet.participants || []).filter(p => p !== me)
    },
    formattedDuration() {
      if (!this.currentMeet) return '00:00'
      const secs = this.currentMeet.duration || 0
      const h = Math.floor(secs / 3600)
      const m = Math.floor((secs % 3600) / 60)
      const s = secs % 60
      if (h > 0) {
        return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
      }
      return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    },
    meetChatData() {
      if (!this.currentMeet || !this.currentMeet.chatId) return null
      return this.$storex.chats.chats?.[this.currentMeet.chatId] || null
    },
    // True when at least one screen share is active
    isScreenSharing() {
      return this.localScreenStreams.length > 0
    }
  },
  watch: {
    currentMeet: {
      handler(newVal) {
        if (newVal && !this.activeMeetId) {
          this.activeMeetId = newVal.meetId
        }
      },
      immediate: true
    },
    'currentMeet.status'(newStatus) {
      if (newStatus === 'active') {
        this.$nextTick(() => this.bindStreamToInCallVideo())
      }
    },
    localCameraStream(stream) {
      this.$nextTick(() => {
        if (this.$refs.localVideoInCall) {
          this.$refs.localVideoInCall.srcObject = stream || null
        }
        if (this.$refs.localVideo) {
          this.$refs.localVideo.srcObject = stream || null
        }
      })
    }
  },
  mounted() {
    const meetId = this.$route?.params?.meetId
    if (meetId) {
      this.activeMeetId = meetId
      this.joinMeet(meetId)
    }
    try {
      const saved = localStorage.getItem('meetSettings')
      if (saved) {
        this.callSettings = JSON.parse(saved)
        if (this.callSettings.cameraEnabled) {
          this.localCameraEnabled = true
          this.startLocalCamera()
        }
      }
    } catch (e) {
      console.warn('[MeetView] Could not load saved settings')
    }
    document.addEventListener('mousemove', this.onResizePanelMove)
    document.addEventListener('mouseup', this.onResizePanelEnd)
  },
  beforeUnmount() {
    this.stopLocalCamera()
    this.stopAllScreenShares()
    document.removeEventListener('mousemove', this.onResizePanelMove)
    document.removeEventListener('mouseup', this.onResizePanelEnd)
  },
  methods: {
    // ─── Panel toggle ───────────────────────────────────────────────────────
    togglePanel(tab) {
      if (this.panelCollapsed) {
        this.activePanelTab = tab
        this.panelCollapsed = false
      } else if (this.activePanelTab === tab) {
        this.panelCollapsed = true
      } else {
        this.activePanelTab = tab
      }
    },

    // ─── Meet chat ──────────────────────────────────────────────────────────
    openMeetChat() {
      if (this.meetChatData) {
        this.togglePanel('chat')
      } else {
        this.activePanelTab = 'chat'
        this.panelCollapsed = false
      }
    },
    async createMeetChat() {
      if (!this.currentMeet || this.isCreatingChat) return
      this.isCreatingChat = true
      try {
        const chat = await this.$storex.chats.createNewChat({
          name: `Meet – ${this.currentMeet.name || this.activeMeetId}`,
          temp: false
        })
        if (chat?.id) {
          this.currentMeet.chatId = chat.id
        }
      } catch (error) {
        console.error('[MeetView] Failed to create meet chat:', error)
        this.$storex.session.onError('Failed to create meet chat')
      } finally {
        this.isCreatingChat = false
      }
    },

    // ─── Local camera ───────────────────────────────────────────────────────
    async toggleLocalCamera() {
      if (this.localCameraEnabled) {
        this.stopLocalCamera()
        this.localCameraEnabled = false
      } else {
        this.localCameraEnabled = true
        await this.startLocalCamera()
      }
    },
    async startLocalCamera() {
      this.isStartingCamera = true
      this.cameraError = null
      try {
        const deviceId = this.callSettings.selectedCamera
        const constraints = {
          video: deviceId ? { deviceId: { exact: deviceId } } : true,
          audio: false
        }
        const stream = await navigator.mediaDevices.getUserMedia(constraints)
        this.localCameraStream = stream
        this.$nextTick(() => {
          if (this.$refs.localVideo) this.$refs.localVideo.srcObject = stream
          if (this.$refs.localVideoInCall) this.$refs.localVideoInCall.srcObject = stream
        })
      } catch (error) {
        console.error('[MeetView] Camera error:', error)
        this.cameraError = error.message
        this.localCameraEnabled = false
        this.localCameraStream = null
      } finally {
        this.isStartingCamera = false
      }
    },
    stopLocalCamera() {
      if (this.localCameraStream) {
        this.localCameraStream.getTracks().forEach(t => t.stop())
        this.localCameraStream = null
      }
    },
    toggleLocalMic() {
      this.localMuted = !this.localMuted
    },
    bindStreamToInCallVideo() {
      if (this.$refs.localVideoInCall && this.localCameraStream) {
        this.$refs.localVideoInCall.srcObject = this.localCameraStream
      }
    },

    // ─── Multi-screen share ─────────────────────────────────────────────────

    /**
     * Bind a screen-share stream to its dynamically-created <video> element.
     * Called via :ref="el => bindScreenShareVideo(el, share.id)"
     */
    bindScreenShareVideo(el, shareId) {
      if (!el) return
      const share = this.localScreenStreams.find(s => s.id === shareId)
      if (share && el.srcObject !== share.stream) {
        el.srcObject = share.stream
      }
    },

    /**
     * Open the browser's screen/tab/window picker and add a new share tile.
     * Can be called multiple times — each call creates an independent tile.
     */
    async startScreenShare() {
      if (!navigator.mediaDevices?.getDisplayMedia) {
        this.$storex.session.onError('Screen sharing is not supported in this browser')
        return
      }
      this.isRequestingScreen = true
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: { cursor: 'always' },
          audio: false,
          // Allow user to choose: current tab, any tab, or window
          selfBrowserSurface: "include"
        })

        // Derive a human-readable label from the track
        const videoTrack = stream.getVideoTracks()[0]
        const rawLabel = videoTrack?.label || ''
        const label = this.prettifyShareLabel(rawLabel)

        const shareId = `share_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`

        // Listen for the user stopping the share via the browser's native UI
        videoTrack?.addEventListener('ended', () => {
          this.stopScreenShare(shareId)
        })

        this.localScreenStreams = [
          ...this.localScreenStreams,
          { id: shareId, stream, label }
        ]
      } catch (error) {
        // NotAllowedError = user cancelled the picker — not an error worth toasting
        if (error.name !== 'NotAllowedError') {
          console.error('[MeetView] Screen share error:', error)
          this.$storex.session.onError('Failed to start screen share: ' + error.message)
        }
      } finally {
        this.isRequestingScreen = false
      }
    },

    /**
     * Stop a specific screen share by its id.
     */
    stopScreenShare(shareId) {
      const share = this.localScreenStreams.find(s => s.id === shareId)
      if (share) {
        share.stream.getTracks().forEach(t => t.stop())
        this.localScreenStreams = this.localScreenStreams.filter(s => s.id !== shareId)
      }
    },

    /**
     * Stop ALL active screen shares (used on leave/unmount).
     */
    stopAllScreenShares() {
      this.localScreenStreams.forEach(share => {
        share.stream.getTracks().forEach(t => t.stop())
      })
      this.localScreenStreams = []
    },

    /**
     * Convert a raw MediaStreamTrack label into something readable.
     * E.g. "screen:0:0" → "Screen", "tab:chrome-extension://..." → "Tab"
     */
    prettifyShareLabel(raw) {
      if (!raw) return `Screen ${this.localScreenStreams.length + 1}`
      if (raw.toLowerCase().includes('tab')) return 'Tab'
      if (raw.toLowerCase().includes('window')) return 'Window'
      if (raw.toLowerCase().includes('screen') || raw.toLowerCase().includes('display')) return 'Screen'
      // Use the track label up to 20 chars as a fallback
      return raw.length > 20 ? raw.slice(0, 20) + '…' : raw
    },

    // ─── Meet actions ───────────────────────────────────────────────────────
    formatDate(timestamp) {
      if (!timestamp) return ''
      return new Date(timestamp).toLocaleDateString()
    },
    async startNewMeet() {
      const meetId = `meet_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      this.activeMeetId = meetId
      try {
        await this.$storex.meets.initiateMeet({
          meetId,
          name: `Meet ${new Date().toLocaleTimeString()}`
        })
      } catch (error) {
        console.error('Failed to start meet:', error)
        this.$storex.session.onError('Failed to start meet')
      }
    },
    async joinMeet(meetId) {
      this.activeMeetId = meetId
      try {
        await this.$storex.meets.joinMeet({ meetId })
      } catch (error) {
        console.error('Failed to join meet:', error)
        this.$storex.session.onError('Failed to join meet')
      }
    },
    async onToggleMute() {
      this.isMuted = !this.isMuted
      if (this.activeMeetId) {
        try {
          await this.$storex.meets.toggleMute({ meetId: this.activeMeetId })
        } catch (error) {
          console.error('Failed to toggle mute:', error)
        }
      }
    },
    async onLeaveMeet() {
      if (!this.activeMeetId) return
      this.stopLocalCamera()
      this.stopAllScreenShares()
      try {
        await this.$storex.meets.leaveMeet({ meetId: this.activeMeetId })
        this.activeMeetId = null
        this.panelCollapsed = true
      } catch (error) {
        console.error('Failed to leave meet:', error)
      }
    },
    async onEndMeet() {
      if (!this.activeMeetId) return
      this.stopLocalCamera()
      this.stopAllScreenShares()
      try {
        await this.$storex.meets.endMeet(this.activeMeetId)
        this.activeMeetId = null
        this.panelCollapsed = true
      } catch (error) {
        console.error('Failed to end meet:', error)
      }
    },
    onSaveCallSettings(settings) {
      this.callSettings = { ...settings }
      if (settings.cameraEnabled !== this.localCameraEnabled) {
        this.localCameraEnabled = settings.cameraEnabled
        if (settings.cameraEnabled) {
          this.startLocalCamera()
        } else {
          this.stopLocalCamera()
        }
      }
      this.$storex.session.onInfo('Settings saved')
    },
    onClose() {
      this.stopLocalCamera()
      this.stopAllScreenShares()
      this.$router.push({ name: 'home' })
    },

    // ─── Panel resize ────────────────────────────────────────────────────────
    startResizePanel(e) {
      this.isResizingPanel = true
      this.startXPanel = e.clientX
    },
    onResizePanelMove(e) {
      if (!this.isResizingPanel) return
      const delta = e.clientX - this.startXPanel
      this.activePanelWidth = Math.max(20, Math.min(50, this.activePanelWidth - (delta / window.innerWidth) * 100))
    },
    onResizePanelEnd() {
      if (this.isResizingPanel) {
        this.isResizingPanel = false
      }
    }
  }
}
</script>

<style scoped>
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: width 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
}
.panel-slide-enter-from,
.panel-slide-leave-to {
  width: 0 !important;
  opacity: 0;
}
</style>