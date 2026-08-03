<template>
  <div class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50" v-if="isLoading">
    <div class="bg-base-200 rounded-lg shadow-xl p-8 max-w-md w-full mx-4">
      <!-- Header -->
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-center mb-2">Loading Project</h2>
        <p class="text-lg text-center text-primary font-semibold">{{ projectName }}</p>
      </div>

      <!-- Progress Bar -->
      <div class="mb-6">
        <div class="h-2 bg-base-300 rounded-full overflow-hidden">
          <div 
            class="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-300"
            :style="{ width: `${overallProgress}%` }"
          />
        </div>
        <p class="text-sm text-gray-400 text-center mt-2">{{ overallProgress }}%</p>
      </div>

      <!-- Steps -->
      <div class="space-y-3">
        <div 
          v-for="step in steps" 
          :key="step.id"
          class="flex items-center gap-3 p-3 rounded-lg transition-colors"
          :class="getStepClass(step)"
        >
          <!-- Icon -->
          <div class="flex-shrink-0 w-6 h-6 flex items-center justify-center">
            <div v-if="step.status === 'completed'" class="text-success">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
            </div>
            <div v-else-if="step.status === 'loading'" class="animate-spin text-primary">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div v-else class="w-5 h-5 rounded-full border-2 border-base-400" />
          </div>

          <!-- Step Info -->
          <div class="flex-1 min-w-0">
            <p class="font-medium text-sm truncate">{{ step.label }}</p>
            <p v-if="step.sublabel" class="text-xs text-gray-400 truncate">{{ step.sublabel }}</p>
          </div>

          <!-- Progress -->
          <div v-if="step.status === 'loading' && step.progress" class="text-xs font-mono text-gray-400">
            {{ step.progress }}%
          </div>
        </div>
      </div>

      <!-- Error Message -->
      <div v-if="errorMessage" class="mt-6 p-4 bg-error/20 border border-error rounded-lg">
        <p class="text-sm text-error">{{ errorMessage }}</p>
      </div>

      <!-- Retry Button -->
      <div v-if="errorMessage" class="mt-6 flex gap-2">
        <button 
          @click="retryLoading"
          class="flex-1 btn btn-primary btn-sm"
        >
          Retry
        </button>
        <button 
          @click="cancelLoading"
          class="flex-1 btn btn-ghost btn-sm"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      isLoading: false,
      projectName: '',
      errorMessage: null,
      steps: [
        { id: 'fetch', label: 'Fetching project settings', status: 'pending', progress: 0, sublabel: null },
        { id: 'settings', label: 'Loading configuration', status: 'pending', progress: 0, sublabel: null },
        { id: 'models', label: 'Loading AI models', status: 'pending', progress: 0, sublabel: null },
        { id: 'chats', label: 'Loading chats', status: 'pending', progress: 0, sublabel: null },
        { id: 'views', label: 'Restoring workspace views', status: 'pending', progress: 0, sublabel: null },
        { id: 'finalize', label: 'Finalizing', status: 'pending', progress: 0, sublabel: null }
      ]
    }
  },
  computed: {
    overallProgress() {
      const completed = this.steps.filter(s => s.status === 'completed').length
      const total = this.steps.length
      return Math.round((completed / total) * 100)
    }
  },
  mounted() {
    window.addEventListener('project-loading-step', this.handleStepUpdate)
  },
  beforeUnmount() {
    window.removeEventListener('project-loading-step', this.handleStepUpdate)
  },
  methods: {
    handleStepUpdate(event) {
      const { stepId, status, options = {} } = event.detail
      this.updateStep(stepId, status, options)
    },

    startLoading(projectName) {
      this.projectName = projectName
      this.isLoading = true
      this.errorMessage = null
      this.resetSteps()
    },

    resetSteps() {
      this.steps.forEach(step => {
        step.status = 'pending'
        step.progress = 0
        step.sublabel = null
      })
    },

    updateStep(stepId, status, options = {}) {
      const step = this.steps.find(s => s.id === stepId)
      if (step) {
        step.status = status
        if (options.progress !== undefined) step.progress = options.progress
        if (options.sublabel !== undefined) step.sublabel = options.sublabel
      }
    },

    completeStep(stepId, sublabel = null) {
      this.updateStep(stepId, 'completed', { progress: 100, sublabel })
    },

    markStepLoading(stepId, sublabel = null) {
      this.updateStep(stepId, 'loading', { sublabel })
    },

    markStepError(stepId, sublabel = null) {
      this.updateStep(stepId, 'error', { sublabel })
    },

    finishLoading() {
      this.completeStep('finalize')
      setTimeout(() => {
        this.isLoading = false
      }, 500)
    },

    setError(message) {
      this.errorMessage = message
    },

    retryLoading() {
      this.errorMessage = null
      this.resetSteps()
      this.$emit('retry')
    },

    cancelLoading() {
      this.isLoading = false
      this.errorMessage = null
      this.resetSteps()
      this.$emit('cancel')
    },

    getStepClass(step) {
      if (step.status === 'completed') {
        return 'bg-success/10 text-success'
      } else if (step.status === 'loading') {
        return 'bg-primary/10 text-primary'
      } else if (step.status === 'error') {
        return 'bg-error/10 text-error'
      }
      return 'bg-base-300 text-base-content/50'
    }
  }
}
</script>