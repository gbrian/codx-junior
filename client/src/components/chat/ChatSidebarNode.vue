<script setup>
import ChatIcon from './ChatIcon.vue'
</script>

<template>
  <div class="group/node">
    <!-- Chat Node Card -->
    <div
      class="p-3 rounded-lg border-2 cursor-pointer transition-all"
      :class="selectedChatId === chat.id
        ? 'border-warning bg-warning/10'
        : 'border-base-content/10 bg-base-100 hover:bg-base-200'"
      @click="selectChat"
    >
      <div class="flex items-center gap-2">
        <!-- Expand/Collapse Button -->
        <button
          v-if="hasChildren"
          class="btn btn-xs btn-ghost p-0 w-5 h-5 shrink-0"
          @click.stop="isExpanded = !isExpanded"
          :title="isExpanded ? 'Collapse' : 'Expand'"
        >
          <i :class="[
            'fa-solid text-xs',
            isExpanded ? 'fa-chevron-down' : 'fa-chevron-right'
          ]"></i>
        </button>
        <div v-else class="w-5 shrink-0"></div>

        <!-- Icon + Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <ChatIcon :mode="chat.mode" class="text-xs shrink-0" />
            <span class="font-bold text-sm truncate">{{ chat.name }}</span>
            <span class="text-xs text-base-content/40 shrink-0 tabular-nums">
              {{ chat.messages?.length || 0 }}
            </span>
          </div>
          <div v-if="chat.description" class="text-xs text-base-content/60 line-clamp-1 mt-0.5">
            {{ chat.description }}
          </div>
        </div>

        <!-- Action Buttons (visible on hover) -->
        <div class="opacity-0 group-hover/node:opacity-100 transition-opacity flex items-center gap-1 shrink-0">
          <!-- Plus: Create subtask -->
          <button
            class="btn btn-xs btn-ghost p-0 w-5 h-5"
            title="Create subtask"
            @click.stop="$emit('add-subtask', chat)"
          >
            <i class="fa-solid fa-plus text-xs"></i>
          </button>
          <!-- Trash: Delete subtask -->
          <button
            class="btn btn-xs btn-ghost p-0 w-5 h-5 text-error hover:bg-error/10"
            title="Delete subtask"
            @click.stop="$emit('delete-chat', chat)"
          >
            <i class="fa-solid fa-trash text-xs"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Children (Nested) -->
    <div v-if="isExpanded && hasChildren" class="ml-4 mt-2 space-y-2">
      <ChatSidebarNode
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
  props: {
    chat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null }
  },
  emits: ['select', 'add-subtask', 'delete-chat'],
  data() {
    return {
      isExpanded: true
    }
  },
  computed: {
    children() {
      return this.allChats.filter(c => c.parent_id === this.chat.id)
    },
    hasChildren() {
      return this.children.length > 0
    }
  },
  methods: {
    selectChat() {
      this.$emit('select', this.chat)
    }
  }
}
</script>