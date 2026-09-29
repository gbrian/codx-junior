<script setup>
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
import ChatSidebarNodeExtended from './ChatSidebarNodeExtended.vue'
import ChatNodeHoverPanel from './ChatNodeHoverPanel.vue'
</script>

<template>
  <div class="w-full relative group">
    <div
      class="p-1 rounded-lg border-2 cursor-pointer transition-all flex justify-center relative"
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
        
        <!-- Unread badge for assistant messages from others -->
        <div v-if="unreadCount > 0" class="indicator">
          <span class="indicator-item badge badge-error badge-xs">{{ unreadCount }}</span>
        </div>
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
    },
    unreadCount() {
      const currentUsername = this.$user?.username
      if (!currentUsername) return 0
      
      // Count unread assistant messages from other users
      return (this.chat.messages || []).filter(msg => {
        const isAssistantMsg = msg.role === 'assistant'
        const isOtherUser = msg.user !== currentUsername
        const isUnread = !msg.read_by || !msg.read_by.includes(currentUsername)
        return isAssistantMsg && isOtherUser && isUnread && !msg.hide
      }).length
    }
  }
}
</script>