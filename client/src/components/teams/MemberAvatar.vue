<script setup>
</script>

<template>
  <div class="relative shrink-0" :class="sizeClass">
    <div
      class="w-full h-full rounded-full flex items-center justify-center font-bold text-white"
      :style="{ backgroundColor: avatarColor }"
    >
      {{ member.username?.[0]?.toUpperCase() || '?' }}
    </div>
    <!-- Status dot -->
    <span
      v-if="showStatus"
      class="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-base-200"
      :class="statusDotClass"
    ></span>
  </div>
</template>

<script>
const STATUS_COLORS = {
  online: 'bg-success',
  away: 'bg-warning',
  busy: 'bg-error',
  offline: 'bg-base-content/30'
}

// Deterministic color from username
const PALETTE = ['#6366f1','#8b5cf6','#ec4899','#ef4444','#f97316','#14b8a6','#3b82f6','#22c55e']

export default {
  name: 'MemberAvatar',
  props: {
    member: { type: Object, required: true },
    size: { type: String, default: 'sm' }, // xs | sm | md | lg
    showStatus: { type: Boolean, default: true }
  },
  computed: {
    sizeClass() {
      return { xs: 'w-6 h-6', sm: 'w-8 h-8', md: 'w-10 h-10', lg: 'w-14 h-14' }[this.size] || 'w-8 h-8'
    },
    avatarColor() {
      const str = this.member.username || ''
      const idx = str.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % PALETTE.length
      return PALETTE[idx]
    },
    statusDotClass() {
      return STATUS_COLORS[this.member.status] || STATUS_COLORS.offline
    }
  }
}
</script>