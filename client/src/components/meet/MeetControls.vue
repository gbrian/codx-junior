<script setup>
import MicIndicator from './MicIndicator.vue'
</script>

<template>
  <!-- Call controls bar.
       Desktop (lg+): 3-column grid → duration | controls | leave/end.
       Mobile (<lg): stacked & centered → controls row, then leave/end row.
       The call duration is hidden on mobile to keep the bar compact. -->
  <div class="shrink-0 flex flex-col items-center gap-2 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:items-center lg:gap-4 px-3 py-3 lg:px-6 lg:py-4 bg-[#1c1e20] border-t border-white/5">
    <!-- Duration (left) — hidden on mobile -->
    <div class="hidden lg:block text-xs text-white/40 font-mono">{{ duration }}</div>

    <!-- Center controls -->
    <div class="w-full lg:w-auto flex flex-wrap items-center justify-center gap-1.5 sm:gap-2 lg:gap-3">
      <!-- Microphone -->
      <button
        @click="$emit('toggle-mute')"
        class="w-11 h-11 lg:w-12 lg:h-12 rounded-full flex items-center justify-center text-white transition-all duration-150 active:scale-95"
        :class="isMuted ? 'bg-red-500 hover:bg-red-600' : 'bg-[#3c4043] hover:bg-[#4c5055]'"
        :title="isMuted ? 'Unmute' : 'Mute'"
        :aria-label="isMuted ? 'Unmute microphone' : 'Mute microphone'"
      >
        <MicIndicator :enabled="!isMuted" size="lg" tone="inherit" />
      </button>

      <!-- Camera -->
      <button
        @click="$emit('toggle-camera')"
        class="w-11 h-11 lg:w-12 lg:h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
        :class="cameraEnabled ? 'bg-[#3c4043] hover:bg-[#4c5055]' : 'bg-red-500 hover:bg-red-600'"
        :title="cameraEnabled ? 'Turn off camera' : 'Turn on camera'"
        :aria-label="cameraEnabled ? 'Turn off camera' : 'Turn on camera'"
      >
        <i class="fa-solid text-white text-base" :class="cameraEnabled ? 'fa-video' : 'fa-video-slash'"></i>
      </button>

      <!-- Screen share — always adds a NEW share -->
      <div class="relative">
        <button
          @click="$emit('start-screen-share')"
          :disabled="isRequestingScreen"
          class="w-11 h-11 lg:w-12 lg:h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
          :class="isScreenSharing ? 'bg-primary hover:bg-primary/80' : 'bg-[#3c4043] hover:bg-[#4c5055]'"
          :title="isScreenSharing ? 'Share another screen/tab' : 'Share screen'"
          aria-label="Share screen"
        >
          <span v-if="isRequestingScreen" class="loading loading-spinner loading-xs text-white"></span>
          <i v-else class="fa-solid fa-share-from-square text-white text-base"></i>
        </button>

        <!-- Count badge when >1 shares active -->
        <span
          v-if="screenShareCount > 1"
          class="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full border border-[#1c1e20] flex items-center justify-center text-white text-[9px] font-bold"
        >
          {{ screenShareCount }}
        </span>

        <!-- Pulse dot when at least 1 share active -->
        <span
          v-else-if="isScreenSharing"
          class="absolute -top-0.5 -right-0.5 w-3 h-3 bg-primary rounded-full border-2 border-[#1c1e20] animate-pulse"
        ></span>
      </div>

      <!-- Settings -->
      <button
        @click="$emit('settings')"
        class="w-11 h-11 lg:w-12 lg:h-12 rounded-full bg-[#3c4043] hover:bg-[#4c5055] flex items-center justify-center text-white transition-all duration-150 active:scale-95"
        title="Settings"
        aria-label="Settings"
      >
        <i class="fa-solid fa-sliders text-base"></i>
      </button>

      <!-- Invite -->
      <button
        @click="$emit('invite')"
        class="w-11 h-11 lg:w-12 lg:h-12 rounded-full bg-[#3c4043] hover:bg-[#4c5055] flex items-center justify-center text-white transition-all duration-150 active:scale-95"
        title="Invite"
        aria-label="Invite participants"
      >
        <i class="fa-solid fa-user-plus text-base"></i>
      </button>

      <!-- Chat -->
      <button
        @click="$emit('chat')"
        class="w-11 h-11 lg:w-12 lg:h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
        :class="activePanelTab === 'chat' && !panelCollapsed ? 'bg-primary hover:bg-primary/80' : 'bg-[#3c4043] hover:bg-[#4c5055]'"
        title="Meet chat"
        aria-label="Meet chat"
      >
        <i class="fa-solid fa-comments text-white text-base"></i>
      </button>

      <!-- People panel toggle -->
      <button
        @click="$emit('people')"
        class="w-11 h-11 lg:w-12 lg:h-12 rounded-full flex items-center justify-center transition-all duration-150 active:scale-95"
        :class="activePanelTab === 'people' && !panelCollapsed ? 'bg-primary hover:bg-primary/80' : 'bg-[#3c4043] hover:bg-[#4c5055]'"
        :title="panelCollapsed ? 'Show participants' : 'Hide participants'"
        aria-label="Toggle participants panel"
      >
        <i class="fa-solid fa-users text-white text-base"></i>
      </button>
    </div>

    <!-- Right: Leave / End -->
    <div class="w-full lg:w-auto flex items-center gap-2 justify-center lg:justify-end">
      <button
        v-if="isInitiator"
        @click="$emit('end')"
        class="btn btn-sm btn-outline btn-error rounded-full px-4 gap-1.5"
        title="End call for everyone"
      >
        <i class="fa-solid fa-phone-slash"></i>
        End
      </button>
      <button
        @click="$emit('leave')"
        class="btn btn-sm btn-error rounded-full px-4 gap-1.5"
        title="Leave call"
      >
        <i class="fa-solid fa-phone-slash"></i>
        Leave
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MeetControls',
  props: {
    isMuted: { type: Boolean, default: false },
    cameraEnabled: { type: Boolean, default: false },
    screenShareCount: { type: Number, default: 0 },
    isRequestingScreen: { type: Boolean, default: false },
    activePanelTab: { type: String, default: 'people' },
    panelCollapsed: { type: Boolean, default: true },
    duration: { type: String, default: '00:00' },
    isInitiator: { type: Boolean, default: false }
  },
  emits: ['toggle-mute', 'toggle-camera', 'start-screen-share', 'settings', 'invite', 'chat', 'people', 'leave', 'end'],
  computed: {
    isScreenSharing() {
      return this.screenShareCount > 0
    }
  }
}
</script>