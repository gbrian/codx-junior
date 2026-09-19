<script setup>
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
import ChatNodeHoverPanel from './ChatNodeHoverPanel.vue'
</script>

<template>
  <div class="w-full">
    <!-- Node Row -->
    <div
      class="relative group p-2 rounded-lg border-2 cursor-pointer transition-all"
      :class="selectedChatId === chat.id
        ? 'border-warning bg-warning/10'
        : 'border-base-content/10 bg-base-100 hover:bg-base-200'"
      @click="$emit('select', chat)"
    >
      <div class="flex items-center gap-2">
        <ProjectIcon
          :icon-only="true"
          :width="3"
          :project="$chats.getChatProject({ owner_project_id: chat.project_id || chat.owner_project_id })" />
        <div v-if="isUpdating" class="shrink-0">
          <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
        </div>
        <ChatIcon v-else :mode="chat.mode" class="text-xs shrink-0" />
        <span class="text-xs font-medium flex-1 truncate">{{ chat.name }}</span>
        <span class="text-xs text-base-content/40 tabular-nums shrink-0">{{ chat.messages?.length || 0 }}</span>
      </div>
      <div v-if="chat.description" class="text-xs text-base-content/50 line-clamp-1 mt-1 pl-5">
        {{ chat.description }}
      </div>

      <!-- Action buttons (visible on hover) -->
      <div class="absolute right-1 top-1 hidden group-hover:flex gap-1 bg-base-100/90 rounded p-0.5">
        <button
          class="btn btn-xs btn-ghost p-1 h-auto min-h-0"
          title="Add subtask"
          @click.stop="$emit('add-subtask', chat)"
        >
          <i class="fa-solid fa-plus text-xs"></i>
        </button>
        <button
          class="btn btn-xs btn-ghost p-1 h-auto min-h-0 text-error"
          title="Delete"
          @click.stop="$emit('delete-chat', chat)"
        >
          <i class="fa-solid fa-trash text-xs"></i>
        </button>
      </div>

      <!-- Hover Floating Panel -->
      <div
        class="absolute left-full top-0 ml-2 z-50 pointer-events-none opacity-0 group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity duration-150"
      >
        <ChatNodeHoverPanel
          :chat="chat"
          :allChats="allChats"
          @add-subtask="$emit('add-subtask', $event)"
          @delete-chat="$emit('delete-chat', $event)"
        />
      </div>
    </div>

    <!-- Children -->
    <div v-if="hasChildren" class="ml-3 mt-1 space-y-1 border-l border-base-300 pl-2">
      <ChatSidebarNodeExtended
        v-for="child in children"
        :key="child.id"
        :chat="child"
        :allChats="allChats"
        :selectedChatId="selectedChatId"
        @select="$emit('select', $event)"
        @add-subtask="$emit('add-subtask', $event)"
        @delete-chat="$emit('delete-chat', $event)"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatSidebarNodeExtended',
  props: {
    chat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null }
  },
  emits: ['select', 'add-subtask', 'delete-chat'],
  computed: {
    children() {
      return this.allChats.filter(c => c.parent_id === this.chat.id)
    },
    hasChildren() {
      return this.children.length > 0
    },
    isUpdating() {
      return this.$storex.chats.isChatUpdating(this.chat.id)
    }
  }
}
</script>