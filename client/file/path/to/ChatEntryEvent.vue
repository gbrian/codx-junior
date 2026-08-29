<!-- Add to props -->
compact: {
  type: Boolean,
  default: false
}

<!-- Adjust template to conditionally render based on compact -->
<div :class="[
  'lifecycle-event',
  compact ? 'compact-layout' : 'expanded-layout'
]">
  <!-- Compact: timeline-friendly layout -->
  <div v-if="compact" class="flex items-start gap-2 text-xs">
    <i :class="statusIcon" class="text-sm mt-0.5"></i>
    <div class="flex-1">
      <div class="font-semibold">
        Run <code class="text-[10px] bg-base-200 px-1 py-0.5 rounded">
          {{ lifecycleEvent.run_id?.slice(0, 8) }}
        </code>
      </div>
      <p class="text-base-content/60 text-[10px]">{{ lifecycleEvent.timestamp }}</p>
    </div>
    <span class="badge badge-xs" :class="statusBadgeClass">{{ lifecycleEvent.status }}</span>
    <span v-if="lifecycleEvent.duration_ms" class="text-base-content/60">
      {{ (lifecycleEvent.duration_ms / 1000).toFixed(2) }}s
    </span>
  </div>

  <!-- Expanded (existing) -->
  <div v-if="!compact" class="rounded-lg border border-base-300 bg-base-100">
    <!-- ... existing content ... -->
  </div>
</div>

<style scoped>
.compact-layout {
  @apply bg-transparent border-0 p-0;
}

.expanded-layout {
  @apply border border-base-300 rounded-lg p-3;
}
</style>