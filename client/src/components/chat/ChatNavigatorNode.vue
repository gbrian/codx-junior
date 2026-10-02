<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="space-y-1">
    <!-- Node Card -->
    <div
      class="p-2 rounded-lg border-2 cursor-pointer transition-all group flex items-center justify-between"
      :class="selectedChatId === chat.id
        ? 'border-warning bg-warning/10'
        : 'border-base-content/10 bg-base-200 hover:border-base-content/30'"
      @click="selectChat"
    >
      <!-- Left Content -->
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <ChatIcon :mode="chat.mode" class="text-xs shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="font-semibold text-xs truncate">{{ chat.name }}</div>
          <div v-if="chat.description" class="text-xs text-base-content/50 line-clamp-1">
            {{ chat.description }}
          </div>
        </div>
        <span class="text-xs text-base-content/40 shrink-0">{{ chat.messages?.length || 0 }}</span>
      </div>

      <!-- Right Actions (visible on hover) -->
      <button
        class="btn btn-xs btn-ghost opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
        @click.stop="addSubtask"
        title="Create subtask"
      >
        <i class="fa-solid fa-plus text-primary"></i>
      </button>
    </div>

    <!-- Children (Recursive) -->
    <div v-if="children.length" class="ml-4 space-y-1">
      <ChatNavigatorNode
        v-for="child in children"
        :key="child.id"
        :chat="child"
        :allChats="allChats"
        :selectedChatId="selectedChatId"
        :depth="depth + 1"
        @select="selectChat"
        @add-subtask="emitAddSubtask"
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
    allChats: {
      type: Array,
      default: () => []
    },
    selectedChatId: {
      type: String,
      default: null
    },
    depth: {
      type: Number,
      default: 0
    }
  },
  computed: {
    children() {
      return this.allChats
        .filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => (a.child_index ?? 999999) - (b.child_index ?? 999999) || a.name.localeCompare(b.name))
    }
  },
  methods: {
    selectChat() {
      this.$emit('select', this.chat)
    },
    addSubtask() {
      this.$emit('add-subtask', this.chat)
    },
    emitAddSubtask(parentChat) {
      this.$emit('add-subtask', parentChat)
    }
  }
}
</script>