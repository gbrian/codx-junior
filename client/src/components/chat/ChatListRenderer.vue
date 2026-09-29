<script setup>
import ChatSidebarNodeExtended from './ChatSidebarNodeExtended.vue'
import ChatSidebarNode from './ChatSidebarNode.vue'
</script>

<template>
  <!-- Collapsed mode: Chat icons -->
  <div v-if="isCompact" class="flex flex-col gap-2 overflow-y-auto flex-1 scrollbar-none">
    <div
      v-for="chat in displayedChatsCompact"
      :key="chat.id"
      @click="handleSelectChat(chat)"
      class="relative cursor-pointer group"
      :title="chat.name"
    >
      <div
        class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold border transition-all duration-200"
        :class="[
          selectedChatId === chat.id
            ? 'bg-codx-secondary text-white border-codx-primary/60 shadow-md'
            : 'text-white border-white/20 hover:bg-white/20 hover:border-white/30',
          isVisibleChat(chat) && 'ring-2 ring-warning/50'
        ]"
      >
        {{ getInitials(chat.name) }}
      </div>

      <!-- Unread badge -->
      <div v-if="getUnreadCount(chat) > 0" class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-error text-white text-[9px] font-bold flex items-center justify-center border border-[#1a1a1a]">
        {{ getUnreadCount(chat) > 9 ? '9+' : getUnreadCount(chat) }}
      </div>

      <!-- Tooltip -->
      <div class="absolute left-14 top-1/2 -translate-y-1/2 bg-white/20 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 border border-white/20">
        {{ chat.name }}
      </div>
    </div>

    <!-- Loading spinner -->
    <div v-if="isLoading" class="flex justify-center py-2">
      <span class="loading loading-spinner loading-xs"></span>
    </div>

    <!-- Show more indicator -->
    <div v-if="chatList.length > 5" class="text-[9px] text-white/30 text-center">
      +{{ chatList.length - 5 }}
    </div>
  </div>

  <!-- Expanded mode: Chat cards/nodes list -->
  <div v-else class="overflow-y-auto flex-1 px-2 py-2" @scroll="handleScroll">
    <!-- Empty state -->
    <div v-if="chatList.length === 0 && !isLoading" class="text-center py-8 text-white/30 text-xs">
      <i class="fas fa-inbox text-2xl mb-2 block"></i>
      <p>No chats</p>
    </div>

    <!-- Chat items -->
    <div v-else class="flex flex-col gap-2 overflow-x-hidden">
      <!-- Use ChatSidebarNodeExtended if useExtended is true -->
      <ChatSidebarNodeExtended
        v-if="useExtended"
        v-for="chat in chatList"
        :key="chat.id"
        :chatId="chat.id"
        :selected-chat-id="selectedChatId"
        @select="handleSelectChat"
      />

      <!-- Use ChatSidebarNode for standard nodes -->
      <ChatSidebarNode
        v-else
        v-for="chat in chatList"
        :chat="chat"
        :allChats="allChats"
        :selectedChatId="selectedChatId"
        :isCompact="isCompact"
        @select="handleSelectChat"
        @add-subtask="$emit('add-subtask', $event)"
        @delete-chat="$emit('delete-chat', $event)"
        @click.stop=""
      />

      <!-- Loading indicator -->
      <div v-if="isLoading" class="flex justify-center py-2">
        <span class="loading loading-spinner loading-xs"></span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chatList: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null },
    isCompact: { type: Boolean, default: false },
    isLoading: { type: Boolean, default: false },
    allChats: { type: Array, default: () => [] },
    useExtended: { type: Boolean, default: false },
    visibleChatIds: { type: Set, default: () => new Set() },
    unreadCountCache: { type: Object, default: () => ({}) }
  },
  emits: ['select', 'add-subtask', 'delete-chat', 'load-more'],
  computed: {
    displayedChatsCompact() {
      return this.chatList.slice(0, 5)
    }
  },
  methods: {
    handleSelectChat(chat) {
      this.$emit('select', chat)
    },
    handleScroll(e) {
      const { scrollTop, clientHeight, scrollHeight } = e.target
      if (scrollHeight - scrollTop - clientHeight < 100) {
        this.$emit('load-more')
      }
    },
    isVisibleChat(chat) {
      return this.visibleChatIds.has(chat.id)
    },
    getUnreadCount(chat) {
      return this.unreadCountCache[chat.id] || 0
    },
    getInitials(name) {
      if (!name) return 'CH'
      const cleanName = name.replace(/[^\w\s-]/g, '').trim()
      const words = cleanName.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    }
  }
}
</script>