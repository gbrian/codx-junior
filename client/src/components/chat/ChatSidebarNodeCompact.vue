<script setup>
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
import ChatSidebarNodeExtended from './ChatSidebarNodeExtended.vue'
import ChatNodeHoverPanel from './ChatNodeHoverPanel.vue'
</script>

<template>
  <div class="w-full relative group">
    <div
      class="p-1 rounded-lg border-2 cursor-pointer transition-all flex justify-center"
      :class="selectedChatId === chat.id
        ? 'border-warning bg-warning/10'
        : 'border-base-content/10 bg-base-100 hover:bg-base-200'"
      @click="$emit('select', chat)"
    >
      <!-- Icon Only -->
      <div class="flex flex-col items-center gap-1">
        <ProjectIcon
          :icon-only="true"
          :width="3"
          :project="$chats.getChatWorkingProject(chat)" />
        <div v-if="isUpdating" class="shrink-0">
          <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
        </div>
        <ChatIcon v-else :mode="chat.mode" class="text-xs shrink-0" />
      </div>
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

      <!-- Children list inside hover panel -->
      <div v-if="hasChildren" class="mt-2 bg-base-100 border-2 border-base-content/10 rounded-lg shadow-2xl p-3 w-72">
        <div class="text-xs font-semibold text-base-content/60 uppercase tracking-wider mb-2">Subtasks</div>
        <div class="space-y-1 max-h-48 overflow-y-auto">
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
    </div>
  </div>
</template>

<script>
export default {
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