<template>
  <div class="modal modal-open">
    <div class="modal-box w-full max-w-4xl h-[80vh] flex flex-col">
      <h3 class="font-bold text-lg mb-4">
        <i class="fa-solid fa-list"></i>
        Workspace Logs - {{ workspace.name }}
      </h3>

      <div v-if="isLoading" class="flex-1 flex items-center justify-center">
        <span class="loading loading-spinner loading-lg"></span>
      </div>

      <div v-else class="flex-1 overflow-y-auto bg-base-900 rounded-lg p-4 font-mono text-sm mb-4">
        <div v-if="logs" class="text-base-content/80 whitespace-pre-wrap break-words">{{ logs }}</div>
        <div v-else class="text-base-content/50 text-center py-8">No logs available</div>
      </div>

      <div class="modal-action">
        <button class="btn btn-ghost" @click="refresh">
          <i class="fa-solid fa-arrows-rotate"></i> Refresh
        </button>
        <button class="btn" @click="$emit('close')">Close</button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @click="$emit('close')"></form>
  </div>
</template>

<script>
export default {
  props: ['workspace', 'project'],
  emits: ['close'],
  data() {
    return {
      logs: '',
      isLoading: false
    }
  },
  async mounted() {
    await this.refresh()
  },
  methods: {
    async refresh() {
      this.isLoading = true
      try {
        const response = await this.project.$api.workspaces.lifecycle.logs(this.workspace.id, 500)
        this.logs = response.logs || ''
      } catch (error) {
        this.logs = `Error loading logs: ${error.message}`
      } finally {
        this.isLoading = false
      }
    }
  }
}
</script>