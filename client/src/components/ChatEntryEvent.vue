<script setup>
</script>

<template>
  <div v-if="lifecycleEvent" class="rounded-lg border border-base-300 bg-base-100 text-base-content">
    <!-- Header row -->
    <div class="flex items-center gap-3 px-4 py-3">
      <!-- Status icon -->
      <i :class="statusIcon" class="text-base w-4 text-center flex-shrink-0"></i>

      <!-- Identity -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-semibold text-sm">
            Run <code class="font-mono text-xs bg-base-200 px-1.5 py-0.5 rounded">{{ lifecycleEvent.run_id?.slice(0, 8) }}</code>
          </span>
          <span class="badge badge-sm" :class="statusBadgeClass">{{ lifecycleEvent.status }}</span>
        </div>
        <p class="text-xs text-base-content/50 mt-0.5">{{ lifecycleEvent.timestamp }}</p>
      </div>

      <!-- Duration -->
      <div
        v-if="lifecycleEvent.duration_ms !== null && lifecycleEvent.duration_ms !== undefined"
        class="flex items-center gap-1.5 text-xs text-base-content/60 flex-shrink-0"
      >
        <i class="fa-regular fa-clock text-base-content/40"></i>
        <span class="font-mono font-semibold text-base-content">{{ (lifecycleEvent.duration_ms / 1000).toFixed(2) }}s</span>
      </div>
    </div>

    <!-- Event lines (only when present) -->
    <div v-if="eventLines && eventLines.length" class="px-4 pb-3 space-y-1">
      <div
        v-for="(line, index) in eventLines"
        :key="index"
        class="flex items-start gap-2 text-xs text-base-content/70"
      >
        <i class="fa-solid fa-chevron-right text-base-content/30 mt-0.5 text-[10px] flex-shrink-0"></i>
        <span class="leading-relaxed">{{ line }}</span>
      </div>
    </div>

    <!-- Error block -->
    <div
      v-if="lifecycleEvent.status === 'error' && lifecycleEvent.error"
      class="mx-4 mb-3 rounded-md bg-error/10 border border-error/25 px-3 py-2.5"
    >
      <p class="text-xs font-semibold text-error flex items-center gap-1.5 mb-1">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Error
      </p>
      <pre class="text-xs font-mono text-base-content/80 whitespace-pre-wrap break-all">{{ lifecycleEvent.error }}</pre>
    </div>

    <!-- Footer: analytics -->
    <div
      v-if="analytics"
      class="flex items-center gap-4 px-4 py-2.5 border-t border-base-200 text-xs text-base-content/60"
    >
      <div class="flex items-center gap-1.5">
        <i class="fa-solid fa-microchip text-info/70"></i>
        <span class="font-mono font-semibold text-base-content">{{ analytics.total_tokens }}</span>
        <span>tokens</span>
      </div>
      <div v-if="analytics.cost" class="flex items-center gap-1.5">
        <i class="fa-solid fa-coins text-success/70"></i>
        <span class="font-mono font-semibold text-base-content">${{ analytics.cost.toFixed(4) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    lifecycleEvent: {
      type: Object,
      default: null
    },
    eventLines: {
      type: Array,
      default: () => []
    },
    metadata: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    statusIcon() {
      switch (this.lifecycleEvent?.status) {
        case 'running': return 'fa-solid fa-circle-notch fa-spin text-info'
        case 'done':    return 'fa-solid fa-circle-check text-success'
        case 'error':   return 'fa-solid fa-circle-xmark text-error'
        default:        return 'fa-solid fa-circle-dot text-base-content/30'
      }
    },
    statusBadgeClass() {
      switch (this.lifecycleEvent?.status) {
        case 'running': return 'badge-info badge-outline'
        case 'done':    return 'badge-success badge-outline'
        case 'error':   return 'badge-error badge-outline'
        default:        return 'badge-ghost'
      }
    },
    analytics() {
      return this.metadata?.analytics || null
    }
  }
}
</script>