<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-2">
    <!-- Node Card -->
    <div
      :data-chat-id="chat.id"
      draggable="true"
      class="flex flex-col gap-1 p-2 rounded-lg border-2 cursor-move shrink-0 w-36 transition-all duration-200"
      :class="[
        isSelected
          ? 'border-warning bg-warning/10'
          : 'border-base-content/10 bg-base-200 hover:border-base-content/30',
        isDragged ? 'opacity-50 scale-95' : '',
        isDragOver ? 'ring-2 ring-primary ring-offset-2 ring-offset-base-300' : ''
      ]"
      @click="$emit('select')"
      @dragstart="$emit('drag-start', $event)"
      @dragend="$emit('drag-end')"
      @dragover.prevent="$emit('drag-over', $event)"
      @dragenter="$emit('drag-enter')"
    >
      <div class="flex items-center gap-1">
        <span class="text-xs text-base-content/40 font-mono w-4">{{ index + 1 }}</span>
        <ChatIcon :mode="chat.mode" class="text-xs opacity-70" />
        <div 
          class="loading loading-bars text-info loading-sm opacity-60"
          title="Running..."
          v-if="isUpdating"
        ></div>
        <img class="w-3 h-3 rounded-full ml-auto" :src="projectIcon" />
      </div>
      <div class="font-bold text-xs truncate text-base-content/80 font-medium leading-tight" :title="chat.name">
        {{ chat.name }}
      </div>
      <div class="flex items-center justify-between">
        <span class="text-xs text-base-content/40">
          {{ (chat.messages || []).length }} msgs
        </span>
        <span class="badge badge-xs truncate"
          :class="chat.column === 'Done' ? 'badge-success' : chat.column === 'In Progress' ? 'badge-warning' : 'badge-ghost'">
          {{ chat.column || '?' }}
        </span>
      </div>
    </div>

    <!-- Nested Children (if any) -->
    <div v-if="hasChildren" class="ml-4 flex flex-col gap-2 border-l border-base-content/10 pl-2">
      <ChatTreeNode
        v-for="(childChat, idx) in nestedChildren"
        :key="childChat.id"
        :chat="childChat"
        :index="idx"
        :isSelected="selectedChatId === childChat.id"
        :isDragged="draggedItemId === childChat.id"
        :isDragOver="false"
        :depth="depth + 1"
        :allChats="allChats"
        :projectIcon="projectIcon"
        :isUpdating="isChatUpdating(childChat.id)"
        @select="$emit('select', childChat)"
        @add-subtask="$emit('add-subtask', childChat)"
        @drag-start="$emit('drag-start', $event)"
        @drag-end="$emit('drag-end')"
        @drag-over="$emit('drag-over', $event)"
        @drag-enter="$emit('drag-enter')"
      />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: {
      type: Object,
      required: true
    },
    index: {
      type: Number,
      required: true
    },
    isSelected: {
      type: Boolean,
      default: false
    },
    isDragged: {
      type: Boolean,
      default: false
    },
    isDragOver: {
      type: Boolean,
      default: false
    },
    depth: {
      type: Number,
      default: 0
    },
    allChats: {
      type: Array,
      default: () => []
    },
    projectIcon: {
      type: String,
      required: true
    },
    isUpdating: {
      type: Boolean,
      default: false
    },
    selectedChatId: {
      type: String,
      default: null
    },
    draggedItemId: {
      type: String,
      default: null
    }
  },
  computed: {
    nestedChildren() {
      return this.allChats
        .filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    hasChildren() {
      return this.nestedChildren.length > 0
    }
  },
  methods: {
    isChatUpdating(chatId) {
      return this.$chats?.isChatUpdating(chatId) || false
    }
  }
}
</script>