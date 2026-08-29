<script setup>
import moment from 'moment'
</script>

<template>
  <div class="space-y-3">
    <!-- Primary metrics grid -->
    <div class="grid grid-cols-4 gap-2">
      <div class="bg-base-200 rounded p-2 text-center">
        <p class="text-[10px] text-base-content/60 mb-1">
          <i class="fa-solid fa-bolt"></i> Tokens
        </p>
        <p class="text-sm font-bold text-primary">{{ metadata?.analytics?.total_tokens?.toLocaleString() || 0 }}</p>
        <p class="text-[9px] text-base-content/50 mt-0.5">{{ metadata?.analytics?.prompt_tokens || 0 }} / {{ metadata?.analytics?.completion_tokens || 0 }}</p>
      </div>
      <div class="bg-base-200 rounded p-2 text-center">
        <p class="text-[10px] text-base-content/60 mb-1">
          <i class="fa-solid fa-wrench"></i> Tools
        </p>
        <p class="text-sm font-bold text-warning">{{ toolCount }}</p>
        <p class="text-[9px] text-base-content/50 mt-0.5">executed</p>
      </div>
      <div class="bg-base-200 rounded p-2 text-center">
        <p class="text-[10px] text-base-content/60 mb-1">
          <i class="fa-solid fa-list"></i> Events
        </p>
        <p class="text-sm font-bold text-info">{{ lifecycleCount }}</p>
        <p class="text-[9px] text-base-content/50 mt-0.5">lifecycle</p>
      </div>
      <div class="bg-base-200 rounded p-2 text-center">
        <p class="text-[10px] text-base-content/60 mb-1">
          <i class="fa-solid fa-hourglass-end"></i> Duration
        </p>
        <p class="text-sm font-bold text-success">{{ formatDuration(metadata?.time_taken) }}</p>
        <p class="text-[9px] text-base-content/50 mt-0.5">{{ metadata?.time_taken?.toFixed(2) }}s</p>
      </div>
    </div>

    <!-- Model & Session Info -->
    <div class="bg-base-200/50 rounded p-2 space-y-1">
      <div class="flex items-center justify-between text-xs">
        <span class="text-base-content/60">
          <i class="fa-solid fa-robot"></i> Model:
        </span>
        <span class="font-mono font-semibold text-primary">{{ metadata?.model || 'N/A' }}</span>
      </div>
      <div class="flex items-center justify-between text-xs">
        <span class="text-base-content/60">
          <i class="fa-solid fa-hashtag"></i> Request ID:
        </span>
        <span class="font-mono text-[10px] text-base-content/70 truncate">{{ metadata?.cancellation_token_id?.slice(0, 12) || 'N/A' }}</span>
      </div>
      <div v-if="metadata?.start_time" class="flex items-center justify-between text-xs">
        <span class="text-base-content/60">
          <i class="fa-solid fa-clock"></i> Started:
        </span>
        <span class="text-base-content/80">{{ formatTime(metadata.start_time) }}</span>
      </div>
    </div>

    <!-- Token Breakdown -->
    <div class="bg-info/10 border border-info/20 rounded p-2">
      <p class="text-xs font-semibold text-info mb-2">
        <i class="fa-solid fa-chart-pie"></i> Token Analysis
      </p>
      <div class="space-y-1">
        <div class="flex justify-between items-center text-xs">
          <span class="text-base-content/60">Prompt Tokens:</span>
          <div class="flex items-center gap-2">
            <div class="w-24 bg-base-300 rounded-full h-1.5">
              <div 
                class="bg-info h-full rounded-full" 
                :style="{width: getTokenPercentage('prompt') + '%'}"
              ></div>
            </div>
            <span class="font-mono font-semibold w-16 text-right">{{ metadata?.analytics?.prompt_tokens?.toLocaleString() || 0 }}</span>
          </div>
        </div>
        <div class="flex justify-between items-center text-xs">
          <span class="text-base-content/60">Completion Tokens:</span>
          <div class="flex items-center gap-2">
            <div class="w-24 bg-base-300 rounded-full h-1.5">
              <div 
                class="bg-success h-full rounded-full" 
                :style="{width: getTokenPercentage('completion') + '%'}"
              ></div>
            </div>
            <span class="font-mono font-semibold w-16 text-right">{{ metadata?.analytics?.completion_tokens?.toLocaleString() || 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Performance Metrics -->
    <div class="bg-warning/10 border border-warning/20 rounded p-2">
      <p class="text-xs font-semibold text-warning mb-2">
        <i class="fa-solid fa-gauge-high"></i> Performance
      </p>
      <div class="space-y-1 text-xs">
        <div class="flex justify-between">
          <span class="text-base-content/60">Total Duration:</span>
          <span class="font-semibold">{{ metadata?.time_taken?.toFixed(2) }}s</span>
        </div>
        <div v-if="metadata?.first_chunk_time_taken" class="flex justify-between">
          <span class="text-base-content/60">Time to First Token:</span>
          <span class="font-semibold">{{ metadata.first_chunk_time_taken.toFixed(3) }}s</span>
        </div>
        <div class="flex justify-between">
          <span class="text-base-content/60">Tokens/Second:</span>
          <span class="font-semibold">{{ getTokensPerSecond() }}</span>
        </div>
      </div>
    </div>

    <!-- Analytics Tools Section -->
    <div v-if="metadata?.analytics?.tools && Object.keys(metadata.analytics.tools).length > 0" class="bg-base-200/50 rounded p-2">
      <p class="text-xs font-semibold text-base-content mb-2">
        <i class="fa-solid fa-screwdriver"></i> Tool Stats
      </p>
      <div class="space-y-1">
        <div v-for="(value, tool) in metadata.analytics.tools" :key="tool" class="flex justify-between text-xs">
          <span class="text-base-content/60 truncate">{{ tool }}:</span>
          <span class="font-mono text-base-content">{{ value }}</span>
        </div>
      </div>
    </div>

    <!-- Error Indicator -->
    <div v-if="metadata?.error" class="bg-error/10 border border-error/30 rounded p-2">
      <p class="text-[10px] text-error font-semibold mb-1">
        <i class="fa-solid fa-circle-exclamation"></i> Error Occurred
      </p>
      <p class="text-[10px] text-error/80 break-words">{{ metadata.error }}</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    metadata: Object,
    toolCount: Number,
    lifecycleCount: Number
  },
  methods: {
    formatDuration(seconds) {
      if (!seconds) return '0s'
      const baseMoment = moment({ h: 0, m: 0, s: 0, ms: 0 })
      return baseMoment.add(Math.floor(seconds), 'seconds').format('mm:ss')
    },
    formatTime(timestamp) {
      return moment(timestamp).format('HH:mm:ss')
    },
    getTokenPercentage(type) {
      const total = this.metadata?.analytics?.total_tokens || 1
      const value = type === 'prompt' 
        ? (this.metadata?.analytics?.prompt_tokens || 0)
        : (this.metadata?.analytics?.completion_tokens || 0)
      return Math.round((value / total) * 100)
    },
    getTokensPerSecond() {
      if (!this.metadata?.analytics?.total_tokens || !this.metadata?.time_taken) return '0'
      const tps = this.metadata.analytics.total_tokens / this.metadata.time_taken
      return tps.toFixed(1)
    }
  }
}
</script>