<script setup>
import LogViewer from '../LogViewer.vue'
import RequestMetrics from './RequestMetrics.vue'
</script>

<template>
  <div class="p-4 md:p-8">
    <h1 class="text-xl font-semibold mb-4">Metrics Dashboard</h1>
    <RequestMetrics :logs="logs" class="mb-6" />
    <LogViewer :logs.sync="logs" />
  </div>
</template>

<script>
export default {
  data() {
    return {
      logs: []
    }
  },
  methods: {
    // Fetch logs from the server
    async fetchLogs() {
      try {
        const response = await fetch('/api/logs')
        if (!response.ok) {
          console.error('Failed to fetch logs:', response.statusText)
          return
        }
        // Assign logs from server response
        this.logs = await response.json()
      } catch (error) {
        console.error('Error fetching logs:', error)
      }
    }
  },
  mounted() {
    // Fetch logs when the component is mounted
    this.fetchLogs()
  }
}
</script>