<template>
  <div class="flex gap-2">
    <div v-if="workspace.status === 'running'" class="flex gap-2 flex-1">
      <button
        class="btn btn-sm btn-warning flex-1"
        :disabled="isLoading"
        @click="stop"
      >
        <span v-if="isLoading" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-stop"></i>
        Stop
      </button>
      <button class="btn btn-sm btn-ghost" @click="openLogs">
        <i class="fa-solid fa-list"></i>
      </button>
    </div>

    <div v-else-if="workspace.status === 'stopped'" class="flex gap-2 flex-1">
      <button
        class="btn btn-sm btn-success flex-1"
        :disabled="isLoading"
        @click="start"
      >
        <span v-if="isLoading" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-play"></i>
        Start
      </button>
    </div>

    <div v-else class="flex items-center gap-2 flex-1 px-2">
      <span class="loading loading-spinner loading-sm"></span>
      <span class="text-sm">{{ workspace.status }}</span>
    </div>

    <div class="divider divider-horizontal m-0"></div>

    <button class="btn btn-sm btn-primary" @click="edit">
      <i class="fa-solid fa-pen"></i> Edit
    </button>
    <button class="btn btn-sm btn-error btn-outline" @click="deleteWorkspace">
      <i class="fa-solid fa-trash"></i>
    </button>
  </div>
</template>

<script>
export default {
  props: ['workspace', 'project'],
  emits: ['start', 'stop', 'edit', 'delete', 'logs'],
  data() {
    return {
      isLoading: false
    }
  },
  methods: {
    async start() {
      this.isLoading = true
      try {
        await this.project.$api.workspaces.lifecycle.start(this.workspace.id)
        this.$emit('start')
      } catch (error) {
        console.error('Failed to start workspace', error)
      } finally {
        this.isLoading = false
      }
    },
    async stop() {
      this.isLoading = true
      try {
        await this.project.$api.workspaces.lifecycle.stop(this.workspace.id)
        this.$emit('stop')
      } catch (error) {
        console.error('Failed to stop workspace', error)
      } finally {
        this.isLoading = false
      }
    },
    edit() {
      this.$emit('edit')
    },
    deleteWorkspace() {
      this.$emit('delete')
    },
    openLogs() {
      this.$emit('logs')
    }
  }
}
</script>