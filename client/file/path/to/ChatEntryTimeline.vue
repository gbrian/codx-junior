<script setup>
import ChatEventBadge from './ChatEventBadge.vue'
import ToolEventRow from './ToolEventRow.vue'
import LifecycleEventRow from './LifecycleEventRow.vue'
</script>

<template>
  <div v-if="hasEvents" class="chat-entry-timeline">
    <!-- Toggle header -->
    <div class="timeline-header">
      <button @click="expanded = !expanded" class="btn btn-sm btn-ghost gap-2">
        <i :class="[expanded ? 'fa-chevron-down' : 'fa-chevron-right']" class="fa-solid"></i>
        <span class="text-xs font-semibold">Events ({{ eventCount }})</span>
      </button>
      <div class="flex gap-1">
        <span 
          v-if="toolCount" 
          class="badge badge-xs badge-warning gap-1"
        >
          <i class="fa-solid fa-wrench"></i> {{ toolCount }}
        </span>
        <span 
          v-if="lifecycleCount" 
          class="badge badge-xs badge-info gap-1"
        >
          <i class="fa-solid fa-list"></i> {{ lifecycleCount }}
        </span>
      </div>
    </div>

    <!-- Timeline content -->
    <div v-if="expanded" class="timeline-content">
      <div class="timeline-track">
        <div 
          v-for="(event, idx) in sortedEvents" 
          :key="`${event.type}-${idx}`"
          class="timeline-item"
        >
          <!-- Timeline dot -->
          <div class="timeline-dot" :class="`dot-${event.type}`">
            <i :class="getEventIcon(event)"></i>
          </div>

          <!-- Timeline content card -->
          <div class="timeline-card">
            <!-- Row renderer based on event type -->
            <ToolEventRow 
              v-if="event.type === 'tool'"
              :toolEvent="event.data"
              compact
            />
            <LifecycleEventRow 
              v-else-if="event.type === 'lifecycle'"
              :lifecycleEvent="event.data"
              compact
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    lifecycleEvents: Array,
    toolEvents: Array,
    metadata: Object
  },
  data() {
    return {
      expanded: false
    }
  },
  computed: {
    eventCount() {
      return (this.lifecycleEvents?.length || 0) + (this.toolEvents?.length || 0)
    },
    toolCount() {
      return this.toolEvents?.length || 0
    },
    lifecycleCount() {
      return this.lifecycleEvents?.length || 0
    },
    hasEvents() {
      return this.eventCount > 0
    },
    sortedEvents() {
      const events = []
      
      // Add lifecycle events with timestamps
      this.lifecycleEvents?.forEach(le => {
        events.push({
          type: 'lifecycle',
          data: le,
          timestamp: le.timestamp || new Date().toISOString()
        })
      })
      
      // Add tool events with timestamps
      this.toolEvents?.forEach(te => {
        events.push({
          type: 'tool',
          data: te,
          timestamp: te.started_at || new Date().toISOString()
        })
      })
      
      return events.sort((a, b) => 
        new Date(a.timestamp) - new Date(b.timestamp)
      )
    }
  },
  methods: {
    getEventIcon(event) {
      if (event.type === 'tool') {
        const status = event.data.status
        if (status === 'running') return 'fa-solid fa-spinner fa-spin text-info'
        if (status === 'done') return 'fa-solid fa-check-circle text-success'
        if (status === 'error') return 'fa-solid fa-exclamation-circle text-error'
        return 'fa-solid fa-wrench'
      }
      
      if (event.type === 'lifecycle') {
        const status = event.data.status
        if (status === 'running') return 'fa-solid fa-circle-notch fa-spin text-info'
        if (status === 'done') return 'fa-solid fa-circle-check text-success'
        if (status === 'error') return 'fa-solid fa-circle-xmark text-error'
        return 'fa-solid fa-circle-dot'
      }
      
      return 'fa-solid fa-circle'
    }
  }
}
</script>
