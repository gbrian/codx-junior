<script setup>
import ChatEntryEventCard from './ChatEntryEventCard.vue'
import ChatEntryToolCard from './ChatEntryToolCard.vue'
import ChatEntryMetadata from './ChatEntryMetadata.vue'
</script>

<template>
  <div 
    v-if="isOpen"
    class="fixed inset-0 z-40"
    @click.self="close"
  >
    <!-- Drawer panel -->
    <div 
      class="fixed left-0 top-0 h-full w-96 bg-base-100 border-r border-base-300 shadow-xl flex flex-col animate-slide-in-left z-50 overflow-hidden"
      @click.stop
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-base-300 flex-shrink-0">
        <h3 class="font-semibold text-sm flex items-center gap-2">
          <i class="fa-solid fa-stream text-info"></i>
          Processing Details
        </h3>
        <button 
          @click="close"
          class="btn btn-xs btn-ghost"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Single scrollable content area -->
      <div class="flex-1 overflow-y-auto">
        <!-- Summary section -->
        <div class="px-4 py-3 border-b border-base-300 flex-shrink-0">
          <h4 class="text-xs font-semibold text-base-content/70 mb-3 flex items-center gap-2">
            <i class="fa-solid fa-chart-line"></i> Summary
          </h4>
          <ChatEntryMetadata 
            :metadata="metadata"
            :toolCount="toolCount"
            :lifecycleCount="lifecycleCount"
          />
        </div>

        <!-- Tools section -->
        <div v-if="toolEvents.length > 0" class="px-4 py-3 border-b border-base-300">
          <h4 class="text-xs font-semibold text-base-content/70 mb-2 flex items-center gap-2">
            <i class="fa-solid fa-wrench text-warning"></i> Tools ({{ toolCount }})
          </h4>
          <div class="space-y-2">
            <ChatEntryToolCard 
              v-for="(event, idx) in toolEvents" 
              :key="`tool-${idx}`"
              :event="{ data: event, type: 'tool', timestamp: event.created_at || event.timestamp }"
              :isExpanded="true"
              @toggle="toggleExpanded(`tool-${idx}`)"
            />
          </div>
        </div>

        <!-- Events section -->
        <div v-if="lifecycleEvents.length > 0" class="px-4 py-3">
          <h4 class="text-xs font-semibold text-base-content/70 mb-2 flex items-center gap-2">
            <i class="fa-solid fa-list text-info"></i> Events ({{ lifecycleCount }})
          </h4>
          <div class="space-y-2">
            <ChatEntryEventCard 
              v-for="(event, idx) in lifecycleEvents" 
              :key="`lifecycle-${idx}`"
              :event="{ data: event, type: 'lifecycle', timestamp: event.created_at || event.timestamp }"
              :isExpanded="true"
              @toggle="toggleExpanded(`lifecycle-${idx}`)"
            />
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="totalEvents === 0" class="text-center py-12 text-base-content/50 text-sm">
          <i class="fa-solid fa-inbox text-2xl mb-2 block"></i>
          <p>No events or tools executed</p>
        </div>
      </div>

      <!-- Footer stats -->
      <div class="border-t border-base-300 px-4 py-2 text-xs text-base-content/60 flex-shrink-0">
        <div class="flex justify-between items-center">
          <span>{{ totalEvents }} event{{ totalEvents !== 1 ? 's' : '' }}</span>
          <span v-if="metadata?.time_taken" class="text-success">
            <i class="fa-solid fa-hourglass-end"></i> {{ formatDuration(metadata.time_taken) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/20" @click="close"></div>
  </div>
</template>

<script>
import moment from 'moment'

export default {
  props: {
    isOpen: Boolean,
    lifecycleEvents: {
      type: Array,
      default: () => []
    },
    toolEvents: {
      type: Array,
      default: () => []
    },
    metadata: Object
  },
  emits: ['close'],
  data() {
    return {
      expandedId: null
    }
  },
  computed: {
    toolCount() {
      return this.toolEvents?.length || 0
    },
    lifecycleCount() {
      return this.lifecycleEvents?.length || 0
    },
    totalEvents() {
      return this.toolCount + this.lifecycleCount
    }
  },
  methods: {
    close() {
      this.$emit('close')
    },
    toggleExpanded(eventId) {
      this.expandedId = this.expandedId === eventId ? null : eventId
    },
    formatDuration(seconds) {
      if (!seconds) return '0s'
      const baseMoment = moment({ h: 0, m: 0, s: 0, ms: 0 })
      return baseMoment.add(Math.floor(seconds), 'seconds').format('mm:ss')
    }
  },
  watch: {
    isOpen(newVal) {
      if (newVal) {
        this.expandedId = null
      }
    }
  }
}
</script>

<style scoped>
@keyframes slide-in-left {
  from {
    transform: translateX(-100%)
  }
  to {
    transform: translateX(0)
  }
}

.animate-slide-in-left {
  animation: slide-in-left 0.3s ease-out
}
</style>