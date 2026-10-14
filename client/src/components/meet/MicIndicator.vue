<script setup>
</script>

<template>
  <span
    class="mic-indicator relative inline-flex items-center justify-center shrink-0"
    :class="boxClass"
    :title="resolvedTitle"
    :aria-label="resolvedTitle"
    role="img"
  >
    <!-- Pulse ring while the mic is actually picking up audio -->
    <span
      v-if="isSpeaking && animated"
      class="absolute inset-0 rounded-full bg-success/40 animate-ping"
    ></span>
    <i
      class="fa-solid relative z-10"
      :class="[iconClass, iconSizeClass, colorClass]"
      aria-hidden="true"
    ></i>
  </span>
</template>

<script>
export default {
  name: 'MicIndicator',
  props: {
    // Mic capture state. `null` → read the global meets store so the same
    // component reflects the LOCAL microphone everywhere by default.
    enabled: { type: Boolean, default: null },
    // Whether audio is currently detected. `null` → read from the store.
    speaking: { type: Boolean, default: null },
    // 'sm' | 'md' | 'lg'
    size: { type: String, default: 'md' },
    // 'auto' applies semantic colors; 'inherit' keeps the parent's text color
    // (useful inside coloured buttons).
    tone: { type: String, default: 'auto' },
    // Allow the speaking pulse animation.
    animated: { type: Boolean, default: true },
    // Override the tooltip/label; otherwise a sensible default is derived.
    title: { type: String, default: '' }
  },
  computed: {
    isEnabled() {
      if (this.enabled === null) {
        return this.$storex.meets.isLocalMicOn
      }
      return this.enabled
    },
    isSpeaking() {
      if (!this.isEnabled) return false
      if (this.speaking === null) {
        return this.$storex.meets.isMicSpeaking
      }
      return this.speaking
    },
    iconClass() {
      return this.isEnabled ? 'fa-microphone' : 'fa-microphone-slash'
    },
    iconSizeClass() {
      return {
        sm: 'text-xs',
        md: 'text-sm',
        lg: 'text-base'
      }[this.size] || 'text-sm'
    },
    boxClass() {
      return {
        sm: 'w-4 h-4',
        md: 'w-5 h-5',
        lg: 'w-7 h-7'
      }[this.size] || 'w-5 h-5'
    },
    colorClass() {
      if (this.tone === 'inherit') return ''
      if (!this.isEnabled) return 'text-base-content/30'
      if (this.isSpeaking) return 'text-success'
      return 'text-success/70'
    },
    resolvedTitle() {
      if (this.title) return this.title
      if (!this.isEnabled) return 'Microphone muted'
      if (this.isSpeaking) return 'Microphone active — speaking'
      return 'Microphone on'
    }
  }
}
</script>