<script setup>
import AppIcon from '../apps/AppIcon.vue'
import WorkspaceStatusBadge from './WorkspaceStatusBadge.vue'
</script>

<template>
  <div class="card bg-base-100 border border-base-200 hover:border-primary/30 hover:shadow-lg transition-all cursor-pointer group" @click="$emit('select')">

    <!-- Header with Status -->
    <div class="card-body p-4">
      <div class="flex items-start justify-between mb-2">
        <div class="flex-1">
          <h2 class="card-title text-base">{{ workspace.name }}</h2>
          <p class="text-xs text-base-content/50">{{ workspace.folder_path }}</p>
        </div>
        <WorkspaceStatusBadge :status="workspace.status" />
      </div>

      <p v-if="workspace.description" class="text-sm text-base-content/60 line-clamp-2">
        {{ workspace.description }}
      </p>

      <!-- Apps Preview -->
      <div v-if="workspace.apps?.length" class="flex items-center gap-2 my-2">
        <span class="text-xs font-semibold text-base-content/50">Apps:</span>
        <div class="flex gap-1 flex-wrap">
          <div
            v-for="(app, idx) in workspace.apps.slice(0, 3)"
            :key="idx"
            class="tooltip"
            :data-tip="app.name"
          >
            <AppIcon :app="app" class="w-5 h-5" />
          </div>
          <span v-if="workspace.apps.length > 3" class="text-xs text-base-content/40">
            +{{ workspace.apps.length - 3 }}
          </span>
        </div>
      </div>

      <!-- Projects & Users info -->
      <div class="flex gap-3 text-xs text-base-content/50 my-2">
        <div class="flex items-center gap-1">
          <i class="fa-solid fa-folder"></i>
          <span>{{ workspace.project_ids?.length || 0 }} project{{ workspace.project_ids?.length !== 1 ? 's' : '' }}</span>
        </div>
        <div v-if="workspace.user_ids?.length" class="flex items-center gap-1">
          <i class="fa-solid fa-users"></i>
          <span>{{ workspace.user_ids.length }} user{{ workspace.user_ids.length !== 1 ? 's' : '' }}</span>
        </div>
        <div v-else class="flex items-center gap-1 text-success">
          <i class="fa-solid fa-circle-check"></i>
          <span>Public</span>
        </div>
      </div>

      <!-- Template Badge -->
      <div class="flex items-center gap-2 mb-3">
        <span class="badge badge-sm badge-ghost">{{ workspace.template }}</span>
        <span v-if="workspace.use_sysbox" class="badge badge-sm badge-info">Sysbox</span>
      </div>

      <!-- Actions -->
      <div class="card-actions justify-between pt-2 border-t border-base-200 opacity-0 group-hover:opacity-100 transition-opacity">
        <div class="flex gap-1">
          <button
            v-if="workspace.status === 'stopped'"
            class="btn btn-xs btn-success"
            @click.stop="$emit('start')"
            title="Start workspace"
          >
            <i class="fa-solid fa-play"></i>
          </button>
          <button
            v-else-if="workspace.status === 'running'"
            class="btn btn-xs btn-warning"
            @click.stop="$emit('stop')"
            title="Stop workspace"
          >
            <i class="fa-solid fa-stop"></i>
          </button>
          <button v-else class="btn btn-xs btn-disabled">
            <span class="loading loading-spinner loading-xs"></span>
          </button>
        </div>
        <div class="flex gap-1">
          <button
            class="btn btn-xs btn-primary"
            @click.stop="$emit('edit')"
            title="Edit workspace"
          >
            <i class="fa-solid fa-pen"></i>
          </button>
          <button
            class="btn btn-xs btn-error btn-outline"
            @click.stop="$emit('delete')"
            title="Delete workspace"
          >
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['workspace', 'project'],
  emits: ['select', 'edit', 'delete', 'start', 'stop']
}
</script>