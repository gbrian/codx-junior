<script setup>
</script>

<template>
  <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10 bg-base-200 rounded-t-lg">
    <!-- Left: Meet name + info -->
    <div class="flex items-center gap-3 min-w-0">
      <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center shrink-0">
        <i class="fa-solid fa-video text-primary"></i>
      </div>
      <div class="min-w-0">
        <h2 class="text-base font-semibold truncate">{{ meet?.name || 'Meet' }}</h2>
        <div class="text-xs text-base-content/60">
          {{ meetId }}
        </div>
      </div>
    </div>

    <!-- Right: Status + actions -->
    <div class="flex items-center gap-2 shrink-0">
      <!-- Status badge -->
      <span v-if="meet?.status === 'active'" class="badge badge-success badge-sm gap-1">
        <span class="w-1.5 h-1.5 bg-success rounded-full animate-pulse"></span>
        Live
      </span>
      <span v-else class="badge badge-warning badge-sm gap-1">
        <span class="w-1.5 h-1.5 bg-warning rounded-full animate-pulse"></span>
        {{ meet?.status || 'Idle' }}
      </span>

      <!-- Settings button -->
      <button
        @click="$emit('settings')"
        class="btn btn-ghost btn-sm btn-circle"
        title="Settings"
      >
        <i class="fa-solid fa-sliders"></i>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MeetHeader',
  props: {
    meet: { type: Object, default: null },
    meetId: { type: String, default: '' }
  },
  emits: ['close', 'settings']
}
</script>