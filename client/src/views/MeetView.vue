<script setup>
import MeetHeader from '@/components/meet/MeetHeader.vue'
import MeetParticipants from '@/components/meet/MeetParticipants.vue'
import MeetInviteModal from '@/components/meet/MeetInviteModal.vue'
import MeetSettingsModal from '@/components/meet/MeetSettingsModal.vue'
import MeetControls from '@/components/meet/MeetControls.vue'
import MicIndicator from '@/components/meet/MicIndicator.vue'
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
        <!-- INCOMING JOIN REQUESTS (knock / admit)      -->
        <!-- ─────────────────────────────────────────── -->
        <div
          v-if="joinRequests.length"
          class="shrink-0 px-4 py-3 bg-warning/10 border-b border-warning/30 space-y-2"
        >
          <div
            v-for="req in joinRequests"
            :key="req.key"
            class="flex items-center gap-3"
          >
            <img
              :src="req.fromAvatar || `https://api.dicebear.com/7.x/initials/svg?seed=${req.from}`"
              :alt="req.from"
              class="w-9 h-9 rounded-full shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-white truncate">
                {{ req.fromName }} wants to join
              </div>
              <div class="text-xs text-white/40">Waiting for your approval</div>
            </div>
            <button
              @click="admitJoinRequest(req)"
              class="btn btn-success btn-xs rounded-full gap-1"
              title="Admit"
            >
              <i class="fa-solid fa-check"></i>
              Admit
            </button>
            <button
              @click="denyJoinRequest(req)"
              class="btn btn-ghost btn-xs rounded-full gap-1 text-white/60 hover:text-white"
              title="Deny"
            >
              <i class="fa-solid fa-xmark"></i>
              Deny
            </button>
          </div>
        </div>

        <!-- ─────────────────────────────────────────── -->
        <!-- PRE-JOIN LOBBY                              -->
        <!-- ─────────────────────────────────────────── -->
        <div v-if="!currentMeet" class="flex-1 flex items-center justify-center p-6 overflow-auto">
          <div class="flex flex-col lg:flex-row items-center gap-10 w-full max-w-5xl">

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
                  <MicIndicator :enabled="!localMuted" size="lg" tone="inherit" />
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
            <div class="flex flex-col items-center gap-5 text-center lg:text-left lg:items-start w-full max-w-sm">
              <div class="space-y-2">
                <h1 class="text-2xl font-bold text-white">Ready to join?</h1>
                <p class="text-sm text-white/50">Start a call or join with a code</p>
              </div>

              <!-- Start / Join actions (side by side when there is room) -->
              <div class="w-full space-y-2">
                <div class="flex flex-wrap items-stretch gap-2">
                  <button
                    @click="startNewMeet"
                    class="btn btn-primary gap-2 rounded-full px-5 flex-1 min-w-[8.5rem] whitespace-nowrap"
                  >
                    <i class="fa-solid fa-phone"></i>
                    Start call
                  </button>

                  <div class="flex-1 min-w-[11rem] flex items-center gap-2">
                    <input
                      v-model="joinCode"
                      @keyup.enter="onJoinByCode"
                      type="text"
                      placeholder="Join with a code"
                      class="input input-sm input-bordered flex-1 min-w-0 font-mono lowercase tracking-wider bg-white/5 border-white/10 text-white placeholder:text-white/30"
                    />
                    <button
                      @click="onJoinByCode"
                      :disabled="!joinCode || isJoining"
                      class="btn btn-sm btn-primary rounded-full px-4 shrink-0"
                    >
                      <span v-if="isJoining" class="loading loading-spinner loading-xs"></span>
                      <span v-else>Join</span>
                    </button>
                  </div>
                </div>
                <p v-if="joinError" class="text-xs text-error text-left">{{ joinError }}</p>
              </div>

              <!-- Active meets where you are a participant -->
              <div v-if="joinableMeets.length > 0" class="w-full space-y-2">
                <div class="text-xs font-semibold text-white/30 uppercase tracking-wider text-left">Your active meets</div>
                <button
                  v-for="meet in joinableMeets"
                  :key="meet.meetId"
                  @click="onJoinActiveMeet(meet)"
                  class="w-full flex items-center justify-between px-3 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-left"
                >
                  <div class="min-w-0">
                    <div class="font-medium text-sm text-white truncate">{{ meet.name }}</div>
                    <div class="text-xs text-white/40 font-mono lowercase">{{ formatCode(meet.meetId) }}</div>
                  </div>
                  <i class="fa-solid fa-arrow-right text-white/30 text-xs"></i>
                </button>
              </div>

              <!-- Recent -->
              <div v-if="recentMeets.length > 0" class="w-full space-y-2 pt-1">
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

              <!-- Remote participant tiles (real media when available) -->
              <div
                v-for="participant in remoteParticipants"
                :key="participant"
                class="relative aspect-video rounded-2xl overflow-hidden bg-[#3c4043] flex items-center justify-center"
              >
                <video
                  v-if="hasRemoteStream(participant)"
                  :ref="el => bindRemoteVideo(el, participant)"
                  autoplay
                  playsinline
                  class="w-full h-full object-cover"
                ></video>
                <div v-else class="w-14 h-14 rounded-full bg-primary/30 flex items-center justify-center">
                  <i class="fa-solid fa-user text-2xl text-primary/70"></i>
                </div>
                <div class="absolute bottom-2 left-2">
                  <span class="text-white text-xs bg-black/50 px-2 py-0.5 rounded-md backdrop-blur-sm">{{ participant }}</span>
                </div>
              </div>
            </div>

          </div>

          <!-- ─── Call controls bar ─── -->
          <MeetControls
            :is-muted="isMuted"
            :camera-enabled="localCameraEnabled"
            :screen-share-count="localScreenStreams.length"
            :is-requesting-screen="isRequestingScreen"
            :active-panel-tab="activePanelTab"
            :panel-collapsed="panelCollapsed"
            :duration="formattedDuration"
            :is-initiator="isInitiator"
            @toggle-mute="onToggleMute"
            @toggle-camera="toggleLocalCamera"
            @start-screen-share="startScreenShare"
            @settings="showCallSettings = true"
            @invite="showInviteModal = true"
            @chat="openMeetChat"
            @people="togglePanel('people')"
            @leave="onLeaveMeet"
            @end="onEndMeet"
          />
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
import { formatMeetCode } from '@/utils/meetCode'
import { createMicLevelMonitor } from '@/utils/audioLevel'

export default {
  name: 'MeetView',
  props: {
    // Panel params (desktop mode) may carry a meetId to auto-join a deep link.
    params: { type: Object, default: () => ({}) }
  },
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
      // Join by code
      joinCode: '',
      joinError: null,
      isJoining: false,
      // Local media
      localMuted: false,
      localMicStream: null,
      // Web Audio level monitor for the local mic (reports 0–100 to the store)
      micMonitor: null,
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
    // Meet currently registered in the store (set by the REST lifecycle and by
    // socket events such as an approved join request). Mirroring it makes every
    // entry path open the call room.
    storeCurrentMeetId() {
      return this.$storex.meets.currentMeetId
    },
    currentMeet() {
      return this.$storex.meets.meetForId(this.activeMeetId)
    },
    recentMeets() {
      return [...this.$storex.meets.recentMeetHistory].reverse().slice(0, 5)
    },
    // Active meets where the current user is already a participant
    joinableMeets() {
      if (this.currentMeet) return []
      return this.$storex.meets.joinableMeets
    },
    // Incoming knock requests (people asking to join this meet)
    joinRequests() {
      return this.$storex.meets.joinRequestsList
    },
    currentUserName() {
      return this.$storex.users.user?.username || 'You'
    },
    // Whether the current user created this meet (can end it for everyone).
    isInitiator() {
      return !!this.currentMeet && this.currentMeet.initiator === this.currentUserName
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
    // Mirror the store's current meet into the view so "Start call", "Join with
    // a code", an approved knock, an accepted invitation and a deep link all
    // open the call room.
    storeCurrentMeetId: {
      handler(meetId) {
        if (meetId && meetId !== this.activeMeetId) {
          this.activeMeetId = meetId
        }
      },
      immediate: true
    },
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
        // Real call: acquire the microphone (unless muted) and publish media,
        // then bind the local preview.
        if (!this.localMuted && !this.localMicStream) {
          this.enableMic()
        }
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
    // Resolve a meetId from a deep link (route param or panel params)
    const meetId = this.$route?.params?.meetId ||
      this.params?.meetId ||
      this.params?.params?.meetId
    if (meetId) {
      this.activeMeetId = meetId
      this.joinMeet(meetId)
    }
    // Discover active meets to (re)join
    this.$storex.meets.loadActiveMeets().catch(() => {})
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
    const meetId = this.activeMeetId
    this.disableMic()
    this.stopLocalCamera()
    this.stopAllScreenShares()
    if (meetId) {
      // Stop publishing and leave the meet on the backend
      this.$storex.meets.setLocalStream({ meetId, stream: null })
      this.$storex.meets.leaveMeet({ meetId }).catch(() => {})
    }
    document.removeEventListener('mousemove', this.onResizePanelMove)
    document.removeEventListener('mouseup', this.onResizePanelEnd)
  },
  methods: {
    // ─── Formatting ─────────────────────────────────────────────────────────
    formatCode(meetId) {
      return formatMeetCode(meetId)
    },

    // ─── Join requests (knock approval) ─────────────────────────────────────
    admitJoinRequest(req) {
      this.$storex.meets.approveJoinRequest({ meetId: req.meetId, from: req.from })
    },
    denyJoinRequest(req) {
      this.$storex.meets.rejectJoinRequest({ meetId: req.meetId, from: req.from })
    },

    // ─── Join by code ───────────────────────────────────────────────────────
    async onJoinByCode() {
      const code = this.joinCode?.trim()
      if (!code) return
      this.joinError = null
      this.isJoining = true
      try {
        const result = await this.$storex.meets.joinByCode({ code })
        this.joinCode = ''
        // A direct join returns the meet id; a "knock" returns { pending: true }
        // and the room opens once the host approves (via storeCurrentMeetId).
        if (typeof result === 'string' && result) {
          this.activeMeetId = result
        }
      } catch (error) {
        console.error('[MeetView] join by code failed:', error)
        this.joinError = error.message || 'Could not join with that code'
      } finally {
        this.isJoining = false
      }
    },
    async onJoinActiveMeet(meet) {
      if (!meet?.meetId) return
      try {
        await this.$storex.meets.joinMeet({ meetId: meet.meetId })
        this.activeMeetId = meet.meetId
      } catch (error) {
        console.error('[MeetView] join active meet failed:', error)
        this.$storex.session.onError('Failed to join meet')
      }
    },

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

    // ─── Local media publishing ─────────────────────────────────────────────
    /**
     * Merge the active mic + camera tracks and publish them to the store so
     * they are sent to every connected peer.
     */
    publishLocalMedia() {
      if (!this.activeMeetId || !this.currentMeet) return
      const tracks = []
      if (this.localMicStream) tracks.push(...this.localMicStream.getAudioTracks())
      if (this.localCameraStream) tracks.push(...this.localCameraStream.getVideoTracks())
      const stream = tracks.length ? new MediaStream(tracks) : null
      this.$storex.meets.setLocalStream({ meetId: this.activeMeetId, stream })
    },

    // ─── Microphone ─────────────────────────────────────────────────────────
    async enableMic() {
      if (this.localMicStream) return
      try {
        const deviceId = this.callSettings.selectedMicrophone
        const audio = (deviceId && deviceId !== 'default')
          ? {
              deviceId: { exact: deviceId },
              echoCancellation: this.callSettings.echoCancellation !== false,
              noiseSuppression: this.callSettings.noiseSuppression !== false,
              autoGainControl: this.callSettings.autoGainControl !== false
            }
          : true
        this.localMicStream = await navigator.mediaDevices.getUserMedia({ audio, video: false })
        // Create the level monitor once and (re)bind it to the current stream so
        // the global "speaking" state tracks whatever mic is capturing.
        if (!this.micMonitor) {
          this.micMonitor = createMicLevelMonitor({
            onLevel: (level) => this.$storex.meets.setMicLevel(level)
          })
        }
        this.micMonitor.start(this.localMicStream)
        // Reflect the mic state globally so the UI (Meet panel tab, call
        // controls, participant list) shows it — even in the pre-join lobby.
        this.$storex.meets.setLocalMicEnabled(true)
        this.publishLocalMedia()
      } catch (error) {
        console.error('[MeetView] Microphone error:', error)
        this.$storex.session.onWarning('Microphone unavailable')
      }
    },
    disableMic() {
      // Stop the level monitor first so it reports a final 0 level.
      if (this.micMonitor) {
        this.micMonitor.stop()
      }
      if (this.localMicStream) {
        this.localMicStream.getTracks().forEach(t => t.stop())
        this.localMicStream = null
        this.publishLocalMedia()
      }
      this.$storex.meets.setLocalMicEnabled(false)
    },
    async toggleLocalMic() {
      this.localMuted = !this.localMuted
      this.isMuted = this.localMuted
      if (this.localMuted) {
        this.disableMic()
      } else {
        await this.enableMic()
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
        // Reflect the camera state globally so the UI (e.g. the Meet panel tab
        // icon) shows it even in the pre-join lobby with no active meet.
        this.$storex.meets.setLocalCameraEnabled(true)
        this.publishLocalMedia()
        this.$nextTick(() => {
          if (this.$refs.localVideo) this.$refs.localVideo.srcObject = stream
          if (this.$refs.localVideoInCall) this.$refs.localVideoInCall.srcObject = stream
        })
      } catch (error) {
        console.error('[MeetView] Camera error:', error)
        this.cameraError = error.message
        this.localCameraEnabled = false
        this.localCameraStream = null
        this.$storex.meets.setLocalCameraEnabled(false)
      } finally {
        this.isStartingCamera = false
      }
    },
    stopLocalCamera() {
      if (this.localCameraStream) {
        this.localCameraStream.getTracks().forEach(t => t.stop())
        this.localCameraStream = null
        this.publishLocalMedia()
      }
      // Keep the global camera flag in sync when the camera is turned off.
      this.$storex.meets.setLocalCameraEnabled(false)
    },
    bindStreamToInCallVideo() {
      if (this.$refs.localVideoInCall && this.localCameraStream) {
        this.$refs.localVideoInCall.srcObject = this.localCameraStream
      }
    },

    // ─── Remote media ───────────────────────────────────────────────────────
    hasRemoteStream(username) {
      return !!this.currentMeet?.remoteStreams?.[username]
    },
    bindRemoteVideo(el, username) {
      if (!el) return
      const stream = this.currentMeet?.remoteStreams?.[username]
      if (stream && el.srcObject !== stream) {
        el.srcObject = stream
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
      // The store generates a shareable code when no meetId is supplied.
      try {
        const meetId = await this.$storex.meets.initiateMeet({
          name: `Meet ${new Date().toLocaleTimeString()}`
        })
        if (meetId) this.activeMeetId = meetId
        // Refresh so this meet appears in the discovery list for invites.
        this.$storex.meets.loadActiveMeets().catch(() => {})
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
      await this.toggleLocalMic()
    },
    async onLeaveMeet() {
      if (!this.activeMeetId) return
      const meetId = this.activeMeetId
      this.disableMic()
      this.stopLocalCamera()
      this.stopAllScreenShares()
      try {
        await this.$storex.meets.leaveMeet({ meetId })
      } catch (error) {
        console.error('Failed to leave meet:', error)
      }
      this.activeMeetId = null
      this.panelCollapsed = true
    },
    async onEndMeet() {
      if (!this.activeMeetId) return
      const meetId = this.activeMeetId
      this.disableMic()
      this.stopLocalCamera()
      this.stopAllScreenShares()
      try {
        await this.$storex.meets.endMeet(meetId)
      } catch (error) {
        console.error('Failed to end meet:', error)
      }
      this.activeMeetId = null
      this.panelCollapsed = true
    },
    async onSaveCallSettings(settings) {
      this.callSettings = { ...settings }
      if (settings.cameraEnabled !== this.localCameraEnabled) {
        this.localCameraEnabled = settings.cameraEnabled
        if (settings.cameraEnabled) {
          await this.startLocalCamera()
        } else {
          this.stopLocalCamera()
        }
      }
      // Re-acquire the microphone so the new device/options apply
      if (!this.localMuted) {
        this.disableMic()
        await this.enableMic()
      }
      this.$storex.session.onInfo('Settings saved')
    },
    async onClose() {
      await this.onLeaveMeet()
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
