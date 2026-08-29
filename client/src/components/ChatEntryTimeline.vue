<script setup>
import ChatEntryEvent from './ChatEntryEvent.vue'
import ChatEntryTools from './ChatEntryTools.vue'
</script>


<template>
  <div v-if="hasEvents" class="chat-entry-timeline">
    <!-- Toggle header -->
    <div class="timeline-header">
      <button @click="expanded = !expanded" class="btn btn-sm btn-ghost gap-2">
        <i :class="[expanded ? 'fa-chevron-down' : 'fa-chevron-right']" class="fa-solid"></i>
        <span class="text-xs font-semibold">
          <i class="fa-solid fa-clock"></i> Events ({{ eventCount }})
        </span>
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
            <i :class="getEventIcon(event)" class="text-xs"></i>
          </div>

          <!-- Timeline content card -->
          <div class="timeline-card">
            <!-- Render event components in compact mode -->
            <ChatEntryTools 
              v-if="event.type === 'tool'"
              :toolEvent="event.data"
              :compact="true"
            />
            <ChatEntryEvent 
              v-else-if="event.type === 'lifecycle'"
              :lifecycleEvent="event.data"
              :compact="true"
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
      
      if (this.lifecycleEvents && Array.isArray(this.lifecycleEvents)) {
        this.lifecycleEvents.forEach(le => {
          events.push({
            type: 'lifecycle',
            data: le,
            timestamp: le.created_at || le.timestamp || new Date().toISOString()
          })
        })
      }
      
      if (this.toolEvents && Array.isArray(this.toolEvents)) {
        this.toolEvents.forEach(te => {
          events.push({
            type: 'tool',
            data: te,
            timestamp: te.created_at || te.timestamp || new Date().toISOString()
          })
        })
      }
      
      return events.sort((a, b) => {
        const aTime = new Date(a.timestamp).getTime()
        const bTime = new Date(b.timestamp).getTime()
        return aTime - bTime
      })
    }
  },
  methods: {
    getEventIcon(event) {
      if (event.type === 'tool') {
        const status = event.data.status
        if (status === 'running') return 'fa-solid fa-spinner fa-spin text-info'
        if (status === 'done') return 'fa-solid fa-check-circle text-success'
        if (status === 'error') return 'fa-solid fa-exclamation-circle text-error'
        return 'fa-solid fa-wrench text-base-content/40'
      }
      
      if (event.type === 'lifecycle') {
        const status = event.data.status
        if (status === 'running') return 'fa-solid fa-circle-notch fa-spin text-info'
        if (status === 'done' || status === 'completed') return 'fa-solid fa-circle-check text-success'
        if (status === 'error') return 'fa-solid fa-circle-xmark text-error'
        if (status === 'cancelled') return 'fa-solid fa-ban text-warning'
        return 'fa-solid fa-circle-dot text-base-content/40'
      }
      
      return 'fa-solid fa-circle text-base-content/40'
    }
  }
}
</script>