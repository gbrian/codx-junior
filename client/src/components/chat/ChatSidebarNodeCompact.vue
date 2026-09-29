<script setup>
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
import ChatNodeHoverPanel from './ChatNodeHoverPanel.vue'
</script>

<template>
  <div class="w-full relative group">
    <div
      class="p-1 rounded-lg border-l-4 cursor-pointer transition-all flex justify-center relative"
      :class="[
        $chats.statusBorderColor(chat.status),
        selectedChatId === chat.id
          ? 'bg-primary/10'
          : 'bg-base-100 hover:bg-base-200'
      ]"
      @click="$emit('select', chat)"
    >
      <!-- Unread badge -->
      <div
        v-if="unreadCount > 0"
        class="absolute -top-1 -right-1 z-10 min-w-4 h-4 px-1 rounded-full bg-error text-white text-[9px] font-bold flex items-center justify-center border border-base-100"
      >
        {{ unreadCount > 9 ? '9+' : unreadCount }}
      </div>

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