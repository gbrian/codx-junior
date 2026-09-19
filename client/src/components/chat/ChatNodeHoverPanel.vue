<script setup>
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
</script>

<template>
  <div class="bg-base-100 border-2 border-base-content/10 rounded-lg shadow-2xl p-4 w-72">
    <div class="space-y-3">
      <!-- Header -->
      <div class="flex items-center gap-3 pb-3 border-b border-base-200">
        <ProjectIcon
          :icon-only="true"
          :width="4"
          :project="$chats.getChatProject({ owner_project_id: chat.project_id || chat.owner_project_id })" />
        <ChatIcon :mode="chat.mode" class="text-lg shrink-0" />
        <span class="font-bold text-base flex-1 min-w-0 line-clamp-2 break-words">{{ chat.name }}</span>
      </div>

      <!-- Description & Stats -->
      <div class="space-y-2">
        <div v-if="chat.description" class="text-sm text-base-content/80 leading-relaxed">
          {{ chat.description }}
        </div>
        <div class="text-xs text-base-content/60 font-medium flex items-center gap-1">
          <i class="fa-solid fa-message text-xs"></i>
          <span>{{ chat.messages?.length || 0 }} messages</span>
        </div>
      </div>

      <!-- Mode Info -->
      <div class="bg-base-200/50 rounded px-3 py-2 border border-base-300">
        <div class="text-xs text-base-content/70">
          <span class="font-semibold">Mode:</span>
          <span class="capitalize ml-1">{{ chat.mode }}</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 pt-2 border-t border-base-200">
        <button
          class="btn btn-sm btn-ghost flex-1 justify-center gap-2 text-xs"
          @click.stop="$emit('add-subtask', chat)"
        >
          <i class="fa-solid fa-plus"></i>
          <span>Add Task</span>
        </button>
        <button
          class="btn btn-sm btn-ghost flex-1 justify-center gap-2 text-xs text-error hover:bg-error/10"
          @click.stop="$emit('delete-chat', chat)"
        >
          <i class="fa-solid fa-trash"></i>
          <span>Delete</span>
        </button>
      </div>

      <!-- Children count -->
      <div v-if="childrenCount > 0" class="text-xs text-base-content/50 flex items-center gap-1">
        <i class="fa-solid fa-sitemap"></i>
        <span>{{ childrenCount }} subtask{{ childrenCount > 1 ? 's' : '' }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] }
  },
  emits: ['add-subtask', 'delete-chat'],
  computed: {
    childrenCount() {
      return this.allChats.filter(c => c.parent_id === this.chat.id).length
    }
  }
}
</script>