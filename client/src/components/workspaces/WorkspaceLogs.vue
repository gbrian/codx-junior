<template>
  <!-- Modal mode (default) -->
  <div v-if="!inline" class="modal modal-open">
    <div class="modal-box w-full max-w-4xl h-[80vh] flex flex-col">
      <h3 class="font-bold text-lg mb-4">
        <i class="fa-solid fa-list"></i>
        Workspace Logs — {{ workspace.name }}
      </h3>
      <div class="flex-1 overflow-y-auto bg-base-300 rounded-lg p-4 font-mono text-sm mb-4">
        <div v-if="isLoading" class="flex items-center justify-center py-8">
          <span class="loading loading-spinner loading-lg"></span>
        </div>
        <div v-else-if="logs" class="text-base-content/80 whitespace-pre-wrap break-words">{{ logs }}</div>
        <div v-else class="text-base-content/50 text-center py-8">No logs available</div>
      </div>
      <div class="modal-action">
        <button class="btn btn-ghost btn-sm" @click="refresh">
          <i class="fa-solid fa-arrows-rotate" :class="{ 'animate-spin': isLoading }"></i> Refresh
        </button>
        <button class="btn btn-sm" @click="$emit('close')">Close</button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @click="$emit('close')"></form>
  </div>

  <!-- Inline mode (used inside WorkspaceSettings tabs) -->
  <div v-else class="h-full flex flex-col">
    <div class="flex items-center gap-2 mb-3 shrink-0">
      <h3 class="font-semibold flex-1">Logs — {{ workspace.name }}</h3>
      <select v-model="tailLines" class="select select-bordered select-xs w-28" @change="refresh">
        <option :value="100">Last 100</option>
        <option :value="200">Last 200</option>
        <option :value="500">Last 500</option>
        <option :value="1000">Last 1000</option>
      </select>
      <button class="btn btn-ghost btn-xs" @click="refresh" :disabled="isLoading">
        <i class="fa-solid fa-arrows-rotate" :class="{ 'animate-spin': isLoading }"></i>
      </button>
    </div>
    <div class="flex-1 overflow-y-auto bg-base-300 rounded-lg p-4 font-mono text-sm">
      <div v-if="isLoading" class="flex items-center justify-center py-8">
        <span class="loading loading-spinner loading-lg"></span>
      </div>
      <div v-else-if="logs" class="text-base-content/80 whitespace-pre-wrap break-words">{{ logs }}</div>
      <div v-else class="text-base-content/50 text-center py-8">No logs available</div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    workspace: Object,
    project: {
      default: null
    },
    // ADDED: inline=true renders without modal wrapper (for use in tabs)
    inline: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close'],
  data() {
    return {
      logs: '',
      isLoading: false,
      tailLines: 200
    }
  },
  computed: {
    theProject() {
      return this.project || this.$project
    }
  },
  async mounted() {
    await this.refresh()
  },
  methods: {
    async refresh() {
      this.isLoading = true
      try {
        // FIXED: was this.project.$api.workspaces — correct path is projects.workspaces
        const response = await this.theProject.$api.projects.workspaces.lifecycle.logs(this.workspace.id, this.tailLines)
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