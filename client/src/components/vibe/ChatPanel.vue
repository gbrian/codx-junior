<script setup>
import Chat from '@/components/chat/Chat.vue'
import ChatPanelHeader from '@/components/vibe/ChatPanelHeader.vue'
import KanbanContainer from '@/components/kanban/KanbanContainer.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full relative overflow-hidden">
    <!-- Header with search, messages count, etc -->
    <ChatPanelHeader
      :chat="chat"
      :filter="filter"
      :showHiddenMessages="showHidden"
      @reload="$emit('reload')"
      @new-subtask="$emit('new-subtask')"
      @create-subtasks="$emit('create-subtasks')"
      @new-tag="$emit('new-tag')"
      @update:chat="$emit('update:chat', $event)"
      @update:search="$emit('update:search', $event)"
      @update:showHidden="showHidden = $event"
      @delete-chat="$emit('delete-chat', $event)"
    />

    <!-- Kanban overlay (toggles between Kanban and Chat) -->
    <div v-if="showKanban" class="absolute inset-0 flex flex-col bg-base-100/95 z-30 rounded-lg overflow-hidden">
      <div class="flex items-center gap-2 px-2 py-2 border-b border-base-content/10 shrink-0">
        <span class="text-xs font-semibold">Select task or create new</span>
        <button class="btn btn-xs btn-ghost ml-auto" @click="$emit('close-kanban')">
          <i class="fa-solid fa-times"></i>
        </button>
      </div>
      <div class="grow overflow-hidden">
        <KanbanContainer :params="kanbanParams" @chat-selected="$emit('kanban-chat-selected', $event)" />
      </div>
    </div>

    <!-- Chat view -->
    <div v-if="chat" class="grow min-h-0 overflow-hidden">
      <Chat
        :key="chat.id"
        :chat="chat"
        :showHidden="showHidden"
        :filter="filter"
        class="h-full px-2 pb-2"
        @refresh-chat="$emit('reload')"
      />
    </div>

    <!-- Empty state -->
    <div v-else class="grow flex flex-col items-center justify-center gap-3 text-base-content/40">
      <i class="fa-solid fa-inbox text-4xl"></i>
      <span class="text-sm">No active session</span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, default: null },
    showKanban: { type: Boolean, default: false },
    kanbanParams: { type: Object, default: () => ({}) },
    filter: { type: String, default: '' },
  },
  data() {
    return {
      showHidden: false
    }
  },
  emits: [
    'kanban-chat-selected', 'close-kanban',
    'reload', 'new-subtask', 'create-subtasks', 'new-tag',
    'update:chat', 'update:search', 'update:showHidden', 'delete-chat'
  ]
}
</script>