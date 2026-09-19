<script setup>
import ChatSidebarNodeCompact from './ChatSidebarNodeCompact.vue'
import ChatSidebarNodeExtended from './ChatSidebarNodeExtended.vue'
</script>

<template>
  <ChatSidebarNodeCompact
    v-if="isCompact"
    :chat="chat"
    :allChats="allChats"
    :selectedChatId="selectedChatId"
    @select="$emit('select', $event)"
    @add-subtask="$emit('add-subtask', $event)"
    @delete-chat="$emit('delete-chat', $event)"
  />
  <ChatSidebarNodeExtended
    v-else
    :chat="chat"
    :allChats="allChats"
    :selectedChatId="selectedChatId"
    @select="$emit('select', $event)"
    @add-subtask="$emit('add-subtask', $event)"
    @delete-chat="$emit('delete-chat', $event)"
  />
</template>

<script>
export default {
  props: {
    chat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null },
    isCompact: { type: Boolean, default: false }
  },
  emits: ['select', 'add-subtask', 'delete-chat']
}
</script>