<script setup>
import { ref } from 'vue'
</script>

<template>
  <div class="relative">
    <!-- Bell Icon Button -->
    <button
      class="p-1.5 text-base-content/40 hover:text-base-content/80 transition-colors relative"
      :class="hasNotifications ? '' : ''"
      @click="showCard = !showCard"
      title="Show events and notifications"
    >
      <i class="fas fa-bell text-sm"></i>
      <span
        v-if="hasNotifications"
        class="absolute top-0 right-0 w-2 h-2 bg-error rounded-full animate-pulse"
      ></span>
    </button>

    <!-- Floating Card -->
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 scale-95 translate-y-2"
      enter-to-class="opacity-100 scale-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0"
      leave-to-class="opacity-0 scale-95 translate-y-2"
    >
      <div
        v-if="showCard"
        class="absolute top-full left-0 mt-2 w-80 bg-base-100 rounded-lg shadow-2xl border border-base-content/10 z-50 overflow-hidden"
        @click.stop
      >
        <!-- Card Header -->
        <div class="bg-gradient-to-r from-codx-primary/20 to-codx-secondary/20 px-4 py-3 border-b border-base-content/5">
          <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold ">Recent Events</h3>
            <button
              class="text-base-content/40 hover:text-base-content/80 transition-colors"
              @click="showCard = false"
            >
              <i class="fas fa-xmark text-xs"></i>
            </button>
          </div>
        </div>

        <!-- Events List -->
        <div class="max-h-96 overflow-y-auto">
          <!-- Last Event (Latest) -->
          <div v-if="lastEvent" class="px-4 py-3 border-b border-base-content/5 bg-white/2">
            <div class="flex items-start gap-3">
              <div class="shrink-0 mt-1">
                <i :class="getEventIcon(lastEvent)" class="text-lg"></i>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-2">
                  <span class="text-xs font-semibold text-base-content/80 uppercase">{{ getEventType(lastEvent) }}</span>
                  <span class="text-xs text-base-content/40 shrink-0">{{ formatTime(lastEvent.ts) }}</span>
                </div>
                <p class="text-sm text-base-content/70 mt-1 break-words">
                  {{ getEventMessage(lastEvent) }}
                </p>
              </div>
            </div>
          </div>

          <!-- Error Notifications -->
          <div v-if="errorNotifications.length > 0">
            <div class="px-4 py-2 bg-error/10 border-b border-error/20 sticky top-0">
              <span class="text-xs font-semibold text-error uppercase">Errors ({{ errorNotifications.length }})</span>
            </div>
            <div
              v-for="notif in errorNotifications.slice(0, 3)"
              :key="notif.id"
              class="px-4 py-2 border-b border-base-content/5 hover:bg-white/5 transition-colors"
            >
              <div class="flex items-start gap-2">
                <i class="fa-solid fa-circle-exclamation text-error text-xs mt-1 shrink-0"></i>
                <div class="flex-1 min-w-0">
                  <p class="text-xs text-error font-medium break-words">{{ notif.title || notif.text }}</p>
                  <p v-if="notif.text && notif.title" class="text-xs text-base-content/50 mt-0.5 break-words">
                    {{ notif.text }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Warning Notifications -->
          <div v-if="warningNotifications.length > 0">
            <div class="px-4 py-2 bg-warning/10 border-b border-warning/20 sticky top-0">
              <span class="text-xs font-semibold text-warning uppercase">Warnings ({{ warningNotifications.length }})</span>
            </div>
            <div
              v-for="notif in warningNotifications.slice(0, 2)"
              :key="notif.id"
              class="px-4 py-2 border-b border-base-content/5 hover:bg-white/5 transition-colors"
            >
              <div class="flex items-start gap-2">
                <i class="fa-solid fa-triangle-exclamation text-warning text-xs mt-1 shrink-0"></i>
                <div class="flex-1 min-w-0">
                  <p class="text-xs text-warning font-medium break-words">{{ notif.title || notif.text }}</p>
                  <p v-if="notif.text && notif.title" class="text-xs text-base-content/50 mt-0.5 break-words">
                    {{ notif.text }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Success Notifications -->
          <div v-if="successNotifications.length > 0">
            <div class="px-4 py-2 bg-success/10 border-b border-success/20 sticky top-0">
              <span class="text-xs font-semibold text-success uppercase">Success ({{ successNotifications.length }})</span>
            </div>
            <div
              v-for="notif in successNotifications.slice(0, 2)"
              :key="notif.id"
              class="px-4 py-2 border-b border-base-content/5 hover:bg-white/5 transition-colors"
            >
              <div class="flex items-start gap-2">
                <i class="fa-solid fa-circle-check text-success text-xs mt-1 shrink-0"></i>
                <div class="flex-1 min-w-0">
                  <p class="text-xs text-success font-medium break-words">{{ notif.title || notif.text }}</p>
                  <p v-if="notif.text && notif.title" class="text-xs text-base-content/50 mt-0.5 break-words">
                    {{ notif.text }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="!hasNotifications" class="px-4 py-8 text-center">
            <i class="fas fa-bell text-base-content/20 text-2xl mb-2"></i>
            <p class="text-sm text-base-content/40">No events yet</p>
          </div>
        </div>

        <!-- Card Footer -->
        <div v-if="hasNotifications" class="px-4 py-2 border-t border-base-content/5 bg-white/2">
          <button class="w-full text-xs text-center py-1.5 text-base-content/60 hover:text-base-content/80 transition-colors">
            Clear all
          </button>
        </div>
      </div>
    </transition>

    <!-- Click Outside Handler -->
    <div
      v-if="showCard"
      class="fixed inset-0 z-40"
      @click="showCard = false"
    ></div>
  </div>
</template>

<script>
import moment from 'moment'

export default {
  data() {
    return {
      showCard: false
    }
  },
  computed: {
    lastEvent() {
      return this.$storex.session.lastEvent
    },
    errorNotifications() {
      return this.$ui.notifications.filter(n => n.type === 'error').slice().reverse()
    },
    warningNotifications() {
      return this.$ui.notifications.filter(n => n.type === 'warning').slice().reverse()
    },
    successNotifications() {
      return this.$ui.notifications.filter(n => n.type === 'success').slice().reverse()
    },
    infoNotifications() {
      return this.$ui.notifications.filter(n => n.type === 'info').slice().reverse()
    },
    hasNotifications() {
      return (
        this.errorNotifications.length > 0 ||
        this.warningNotifications.length > 0 ||
        this.successNotifications.length > 0 ||
        this.infoNotifications.length > 0 ||
        !!this.lastEvent
      )
    }
  },
  watch: {
    showCard(newVal) {
      if (newVal) {
        this.$nextTick(() => {
          document.addEventListener('click', this.handleClickOutside)
        })
      } else {
        document.removeEventListener('click', this.handleClickOutside)
      }
    }
  },
  beforeUnmount() {
    document.removeEventListener('click', this.handleClickOutside)
  },
  methods: {
    handleClickOutside(event) {
      const card = this.$el.querySelector('[class*="absolute"]')
      const button = this.$el.querySelector('button')
      if (card && !card.contains(event.target) && !button.contains(event.target)) {
        this.showCard = false
      }
    },
    getEventIcon(event) {
      const type = event?.data?.type || event?.event || ''
      if (type.includes('error')) return 'fa-solid fa-circle-xmark text-error'
      if (type.includes('warn')) return 'fa-solid fa-triangle-exclamation text-warning'
      if (type.includes('success')) return 'fa-solid fa-circle-check text-success'
      if (type.includes('loaded')) return 'fa-solid fa-download text-info'
      return 'fa-solid fa-circle-info text-info'
    },
    getEventType(event) {
      return event?.data?.event_type || event?.data?.type || event?.event || 'Event'
    },
    getEventMessage(event) {
      const { data } = event
      if (data?.event_type === 'loaded' || data?.type === 'loaded') {
        return data.file_path || 'File loaded'
      }
      return data?.message?.content || data?.text || event?.message || 'No message'
    },
    formatTime(timestamp) {
      if (!timestamp) return ''
      return moment(timestamp).format('HH:mm:ss')
    }
  }
}
</script>