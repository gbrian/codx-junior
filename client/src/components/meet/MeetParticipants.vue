<script setup>
</script>

<template>
  <div class="p-4 space-y-4">
    <!-- Participants header -->
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold">
        Participants
        <span class="text-base-content/60 font-normal">({{ meet?.participants?.length || 0 }})</span>
      </h3>
    </div>

    <!-- Participants grid/list -->
    <div v-if="meet?.participants?.length" class="space-y-3">
      <div
        v-for="username in meet.participants"
        :key="username"
        class="flex items-center gap-3 p-3 rounded-lg bg-base-content/5 border border-base-content/10 hover:border-base-content/20 transition-all"
      >
        <!-- Avatar -->
        <div class="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
          <i class="fa-solid fa-user text-primary text-sm"></i>
        </div>

        <!-- Username -->
        <div class="flex-1 min-w-0">
          <div class="text-sm font-semibold truncate">{{ username }}</div>
          <div class="text-xs text-base-content/50">
            <span v-if="isYou(username)" class="badge badge-xs badge-ghost">You</span>
            <span v-else class="text-base-content/40">Connected</span>
          </div>
        </div>

        <!-- Status indicators -->
        <div class="flex items-center gap-1.5 shrink-0">
          <!-- Microphone status -->
          <div
            class="w-7 h-7 rounded-lg flex items-center justify-center"
            :class="isMuted(username) ? 'bg-base-content/10' : 'bg-success/20'"
            :title="isMuted(username) ? 'Muted' : 'Microphone on'"
          >
            <i
              class="fa-solid text-xs"
              :class="isMuted(username) ? 'fa-microphone-slash text-base-content/40' : 'fa-microphone text-success'"
            ></i>
          </div>

          <!-- Speaker volume (placeholder) -->
          <div class="w-7 h-7 rounded-lg bg-base-content/5 flex items-center justify-center">
            <i class="fa-solid fa-volume-2 text-xs text-base-content/40"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="text-center py-8 text-base-content/40">
      <i class="fa-solid fa-users text-3xl mb-2 block"></i>
      <p class="text-sm">No participants yet</p>
    </div>

    <!-- Invite info -->
    <div class="p-3 rounded-lg bg-info/10 border border-info/30 text-xs text-info space-y-2">
      <div class="flex items-start gap-2">
        <i class="fa-solid fa-info-circle mt-0.5 shrink-0"></i>
        <div>
          <p class="font-semibold mb-1">Share this meet:</p>
          <p class="text-info/80">Send the meet ID to invite others to join</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MeetParticipants',
  props: {
    meet: { type: Object, default: null }
  },
  data() {
    return {
      mutedParticipants: {}
    }
  },
  methods: {
    isYou(username) {
      const currentUser = this.$storex.users.user?.username || 'me'
      return username === currentUser
    },
    isMuted(username) {
      // Mock implementation - would come from actual audio state
      return this.mutedParticipants[username] || false
    }
  }
}
</script>