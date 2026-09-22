<script setup>
import AppWindow from '../windowManager/AppWindow.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full bg-base-100 relative">
    <!-- Header with app info and close button -->
    <div class="shrink-0 flex items-center justify-between px-4 py-3 border-b border-base-300/50 bg-base-100">
      <div class="flex items-center gap-2 min-w-0">
        <i
          v-if="appIcon"
          :class="appIcon"
          class="text-lg text-primary shrink-0"
        ></i>
        <span class="text-sm font-medium text-base-content truncate">
          {{ appName }}
        </span>
      </div>
      <div class="flex items-center gap-1">
        <button
          class="btn btn-ghost btn-sm btn-circle text-base-content/60 hover:text-base-content"
          title="Close app"
          @click="$emit('close')"
        >
          <i class="fas fa-xmark"></i>
        </button>
      </div>
    </div>

    <!-- Iframe container - hidden until loaded -->
    <div class="flex-1 overflow-hidden" :class="isLoading ? 'invisible' : 'visible'">
      <AppWindow
        :key="app.key"
        :app="app"
        @loaded="onIframeLoaded"
      />
    </div>

    <!-- Loading state overlay -->
    <div v-if="isLoading" class="absolute z-10 inset-0 flex items-center justify-center bg-base-100/50">
      <div class="flex flex-col items-center gap-3">
        <span class="loading loading-spinner loading-md text-primary"></span>
        <span class="text-sm text-base-content/60">Loading {{ appName }}...</span>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="absolute z-10 inset-0 flex items-center justify-center bg-base-100/50">
      <div class="flex flex-col items-center gap-3 text-center px-4">
        <i class="fas fa-circle-exclamation text-lg text-error"></i>
        <span class="text-sm text-base-content/60">{{ error }}</span>
        <button
          class="btn btn-sm btn-primary mt-2"
          @click="retry"
        >
          Retry
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    app: {
      type: Object,
      required: true
    }
  },
  emits: ['close', 'loaded'],
  data() {
    return {
      isLoading: true,
      error: null,
      loadTimeout: null
    }
  },
  computed: {
    appName() {
      return this.app?.name || 'Workspace App'
    },
    appIcon() {
      return this.app?.icon || null
    },
    appUrl() {
      return this.app?.path
    }
  },
  mounted() {
    this.setupLoadTimeout()
  },
  beforeUnmount() {
    this.clearLoadTimeout()
  },
  methods: {
    setupLoadTimeout() {
      this.clearLoadTimeout()
      this.loadTimeout = setTimeout(() => {
        if (this.isLoading) {
          this.error = 'Failed to load app. Please try again.'
        }
      }, 15000)
    },
    clearLoadTimeout() {
      if (this.loadTimeout) {
        clearTimeout(this.loadTimeout)
        this.loadTimeout = null
      }
    },
    onIframeLoaded() {
      this.clearLoadTimeout()
      this.isLoading = false
      this.error = null
      this.$emit('loaded')
    },
    retry() {
      this.error = null
      this.isLoading = true
      this.setupLoadTimeout()
    }
  }
}
</script>