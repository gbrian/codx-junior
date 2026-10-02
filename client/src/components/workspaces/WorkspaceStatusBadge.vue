<template>
  <div :class="['badge', badgeClass, 'gap-1']">
    <span :class="['w-2 h-2 rounded-full animate-pulse', dotClass]" v-if="status !== 'stopped'"></span>
    {{ statusLabel }}
  </div>
</template>

<script>
export default {
  props: {
    status: {
      type: String,
      default: 'stopped'
    }
  },
  computed: {
    statusLabel() {
      const labels = {
        'stopped': 'Stopped',
        'starting': 'Starting',
        'running': 'Running',
        'error': 'Error'
      }
      return labels[this.status] || 'Unknown'
    },
    badgeClass() {
      const classes = {
        'stopped': 'badge-ghost',
        'starting': 'badge-warning',
        'running': 'badge-success',
        'error': 'badge-error'
      }
      return classes[this.status] || 'badge-ghost'
    },
    dotClass() {
      const classes = {
        'running': 'bg-success',
        'starting': 'bg-warning',
        'error': 'bg-error'
      }
      return classes[this.status] || ''
    }
  }
}
</script>