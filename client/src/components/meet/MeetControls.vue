<script setup>
</script>

<template>
  <div class="flex items-center justify-center gap-3 px-4 py-4 border-t border-base-content/10 bg-base-200 rounded-b-lg">
    <!-- Mute toggle -->
    <button
      @click="$emit('toggle-mute')"
      class="btn btn-circle btn-lg"
      :class="isMuted ? 'btn-error' : 'btn-ghost border border-base-content/20'"
      :title="isMuted ? 'Unmute microphone' : 'Mute microphone'"
    >
      <i class="fa-solid text-xl" :class="isMuted ? 'fa-microphone-slash' : 'fa-microphone'"></i>
    </button>

    <!-- Camera toggle (disabled - voice only) -->
    <button
      class="btn btn-circle btn-lg btn-ghost border border-base-content/20 opacity-40 cursor-not-allowed"
      title="Camera (coming soon)"
      disabled
    >
      <i class="fa-solid fa-video-slash text-xl"></i>
    </button>

    <!-- Screen share (disabled for now) -->
    <button
      class="btn btn-circle btn-lg btn-ghost border border-base-content/20 opacity-40 cursor-not-allowed"
      title="Screen share (coming soon)"
      disabled
    >
      <i class="fa-solid fa-share-from-square text-xl"></i>
    </button>

    <!-- Spacer -->
    <div class="flex-1"></div>

    <!-- Invite button -->
    <button
      @click="$emit('invite')"
      class="btn btn-sm btn-ghost gap-2 border border-base-content/20"
    >
      <i class="fa-solid fa-user-plus"></i>
      Invite
    </button>

    <!-- Settings button -->
    <button
      @click="$emit('settings')"
      class="btn btn-sm btn-ghost gap-2 border border-base-content/20"
    >
      <i class="fa-solid fa-sliders"></i>
      Settings
    </button>

    <!-- Leave call button -->
    <button
      @click="$emit('leave')"
      class="btn btn-sm btn-warning gap-2"
    >
      <i class="fa-solid fa-arrow-right-from-bracket"></i>
      Leave
    </button>

    <!-- End call button (only for initiator) -->
    <button
      v-if="isInitiator"
      @click="$emit('end')"
      class="btn btn-sm btn-error gap-2"
    >
      <i class="fa-solid fa-phone-slash"></i>
      End Call
    </button>
  </div>
</template>

<script>
export default {
  name: 'MeetControls',
  props: {
    meet: { type: Object, default: null },
    isMuted: { type: Boolean, default: false }
  },
  emits: ['toggle-mute', 'leave', 'end', 'invite', 'settings'],
  computed: {
    isInitiator() {
      const currentUser = this.$storex.users.user?.username || 'me'
      return this.meet?.initiator === currentUser
    }
  }
}
</script>