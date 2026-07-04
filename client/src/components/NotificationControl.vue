<script setup>
import moment from 'moment'
</script>
<template>
  <div class="relative">
    <!-- Notification Control Buttons -->
    <div class="flex gap-2 items-center h-full">
      <button 
        v-for="type in notificationTypes" 
        :key="type"
        @click="togglePanel(type)"
        class="flex items-center gap-1 px-2 py-1 rounded hover:bg-base-200 transition-colors"
        :class="getButtonClass(type)"
        :title="`${type} notifications`"
      >
        <i :class="getIconClass(type)"></i>
        <span class="text-xs font-semibold">{{ getNotificationCount(type) }}</span>
      </button>
    </div>

    <!-- Notifications Panel -->
    <div 
      v-if="showPanel"
      class="absolute top-full right-0 mb-2 bg-base-100 border border-base-300 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto min-w-96"
    >
      <!-- Panel Header -->
      <div :class="getHeaderClass(activePanel)" class="sticky top-0 px-4 py-2 border-b border-base-300 flex justify-between items-center">
        <span class="text-sm font-semibold capitalize">{{ activePanel }} Notifications</span>
        <button 
          @click="closePanel"
          class="text-lg hover:opacity-80"
        >
          ×
        </button>
      </div>

      <!-- Notifications List -->
      <div v-if="filteredNotifications.length > 0" class="divide-y divide-base-200">
        <div 
          v-for="(notification, idx) in filteredNotifications" 
          :key="idx"
          @click="removeNotification(notification)"
          class="p-3 hover:bg-base-200 cursor-pointer transition-colors group"
        >
          <div class="flex justify-between items-start gap-2">
            <div class="flex-1 min-w-0">
              <div class="text-xs text-base-content/60 mb-1">
                {{ moment(notification.ts).format('HH:mm:ss') }}
              </div>
              <div class="text-sm break-words">{{ notification.text }}</div>
            </div>
            <span class="text-sm text-base-content-ERROR-40 group-hover:text-error whitespace-nowrap">
              (×)
            </span>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="p-4 text-center text-base-content/60 text-sm">
        No {{ activePanel }} notifications
      </div>

      <!-- Clear All Button -->
      <div v-if="filteredNotifications.length > 0" class="sticky bottom-0 bg-base-200 border-t border-base-300 p-2">
        <button 
          @click="clearAll"
          class="w-full btn btn-xs btn-outline text-error"
        >
          Clear All
        </button>
      </div>
    </div>

    <!-- Backdrop to close panel -->
    <div 
      v-if="showPanel"
      @click="closePanel"
      class="fixed inset-0 z-40"
    ></div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showPanel: false,
      activePanel: 'info',
      notificationTypes: ['info', 'warning', 'error']
    }
  },
  computed: {
    allNotifications() {
      return this.$storex.ui.notifications || []
    },
    filteredNotifications() {
      return this.allNotifications.filter(n => n.type === this.activePanel)
    }
  },
  methods: {
    getNotificationCount(type) {
      return this.allNotifications.filter(n => n.type === type).length
    },
    getIconClass(type) {
      const icons = {
        info: 'fa-solid fa-circle-info text-info',
        warning: 'fa-solid fa-triangle-exclamation text-warning',
        error: 'fa-solid fa-circle-xmark text-error'
      }
      return icons[type] || 'fa-solid fa-bell'
    },
    getButtonClass(type) {
      const classes = {
        info: 'bg-info/10 text-info hover:bg-info/20',
        warning: 'bg-warning/10 text-warning hover:bg-warning/20',
        error: 'bg-error/10 text-error hover:bg-error/20'
      }
      return classes[type]
    },
    getHeaderClass(type) {
      const classes = {
        info: 'bg-info text-info-content',
        warning: 'bg-warning text-warning-content',
        error: 'bg-error text-errorjec-content'
      }
      return classes[type] || 'bg-base-300'
    },
    togglePanel(type) {
      if (this.showPanel && this.activePanel === type) {
        this.closePanel()
      } else {
        this.activePanel = type
        this.showPanel = true
      }
    },
    closePanel() {
      this.showPanel = false
    },
    removeNotification(notification) {
      this.$storex.ui.clearNotifications([notification])
    },
    clearAll() {
      this.$storex.ui.clearNotifications(this.$storex.ui.notifications.filter(n => n.type !== this.activePanel))
    }
  }
}
</script>