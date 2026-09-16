<script setup>
</script>

<template>
  <div 
    v-if="toasts.length > 0"
    class="toast-component fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none"
  >
    <transition-group name="list" tag="div" class="flex flex-col gap-2">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto"
        @mouseenter="pauseAutoDismiss(toast.id)"
        @mouseleave="resumeAutoDismiss(toast.id)"
      >
        <div 
          :class="[
            'alert alert-sm gap-2 max-w-sm shadow-lg',
            toastClasses[toast.type]
          ]"
        >
          <i :class="toastIcons[toast.type]"></i>
          <span class="text-sm">{{ toast.message }}</span>
          <button 
            class="btn btn-ghost btn-xs ml-auto"
            @click="removeToast(toast.id)"
          >
            <i class="fa-solid fa-xmark text-xs"></i>
          </button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script>
import { $storex } from '../store'

export default {
  name: 'Toast',
  data() {
    return {
      toasts: [],
      nextId: 0,
      dismissTimers: {},
      toastClasses: {
        success: 'alert-success',
        error: 'alert-error',
        warning: 'alert-warning',
        info: 'alert-info'
      },
      toastIcons: {
        success: 'fa-solid fa-check-circle text-success',
        error: 'fa-solid fa-circle-xmark text-error',
        warning: 'fa-solid fa-triangle-exclamation text-warning',
        info: 'fa-solid fa-circle-info text-info'
      }
    }
  },
  mounted() {
    // Register this component instance with the store when it mounts
    $storex.toast.registerInstance(this)
  },
  methods: {
    show(message, type = 'info', duration = 3000) {
      const id = this.nextId++
      const toast = { id, message, type }
      this.toasts.push(toast)
      
      if (duration > 0) {
        this.dismissTimers[id] = setTimeout(() => {
          this.removeToast(id)
        }, duration)
      }
      
      return id
    },
    removeToast(id) {
      clearTimeout(this.dismissTimers[id])
      delete this.dismissTimers[id]
      const idx = this.toasts.findIndex(t => t.id === id)
      if (idx !== -1) {
        this.toasts.splice(idx, 1)
      }
    },
    pauseAutoDismiss(id) {
      clearTimeout(this.dismissTimers[id])
    },
    resumeAutoDismiss(id) {
      const toast = this.toasts.find(t => t.id === id)
      if (toast) {
        this.dismissTimers[id] = setTimeout(() => {
          this.removeToast(id)
        }, 3000)
      }
    },
    success(message, duration = 3000) {
      return this.show(message, 'success', duration)
    },
    error(message, duration = 3000) {
      return this.show(message, 'error', duration)
    },
    warning(message, duration = 3000) {
      return this.show(message, 'warning', duration)
    },
    info(message, duration = 3000) {
      return this.show(message, 'info', duration)
    },
    clear() {
      Object.values(this.dismissTimers).forEach(timer => clearTimeout(timer))
      this.dismissTimers = {}
      this.toasts = []
    }
  }
}
</script>