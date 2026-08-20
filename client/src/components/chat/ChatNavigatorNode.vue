<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-1">
    <!-- Node Card -->
    <div
      class="p-3 rounded-lg border cursor-pointer transition-all text-sm"
      :class="[
        isSelected
          ? 'border-warning bg-warning/10'
          : 'border-base-content/10 bg-base-100 hover:border-base-content/30 hover:bg-base-200',
        hasChildren ? 'border-l-4 border-l-primary' : ''
      ]"
      @click="selectNode"
    >
      <div class="flex items-center gap-2">
        <!-- Expand/Collapse Button -->
        <button
          v-if="hasChildren"
          class="btn btn-xs btn-ghost p-0 w-5 h-5 flex items-center justify-center shrink-0"
          @click.stop="toggleExpand"
        >
          <i 
            class="fa-solid fa-chevron-right text-xs transition-transform duration-200"
            :class="isExpanded ? 'rotate-90' : ''"
          ></i>
        </button>
        <div v-else class="w-5 shrink-0"></div>

        <!-- Chat Icon -->
        <ChatIcon :mode="chat.mode" class="text-xs opacity-70 shrink-0" />
        
        <!-- Chat Name -->
        <span class="font-semibold text-sm truncate flex-1">{{ chat.name }}</span>
        
        <!-- Message Count -->
        <span class="text-xs text-base-content/40 shrink-0">
          {{ (chat.messages || []).length }}
        </span>

        <!-- Add Subtask Button (Visible on Hover) -->
        <button
          class="btn btn-xs btn-ghost p-0 w-5 h-5 opacity-0 hover:opacity-100 transition-opacity"
          @click.stop="onAddSubtask"
          title="Add subtask"
        >
          <i class="fa-solid fa-plus text-xs"></i>
        </button>
      </div>

      <!-- Description -->
      <div v-if="chat.description" class="text-xs text-base-content/50 truncate ml-7 mt-1">
        {{ chat.description }}
      </div>
    </div>

    <!-- Nested Children Tree -->
    <div v-if="isExpanded && hasChildren" class="ml-3 flex flex-col gap-1 border-l border-base-content/10 pl-2 py-1">
      <ChatNavigatorNode
        v-for="child in children"
        :key="child.id"
        :chat="child"
        :allChats="allChats"
        :selectedChatId="selectedChatId"
        :depth="depth + 1"
        @select="$emit('select', $event)"
        @add-subtask="$emit('add-subtask', $event)"
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
      required: true
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
  data() {
    return {
      isExpanded: this.depth < 2
    }
  },
  computed: {
    children() {
      return this.allChats
        .filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    hasChildren() {
      return this.children.length > 0
    },
    isSelected() {
      return this.selectedChatId === this.chat.id
    }
  },
  methods: {
    toggleExpand() {
      this.isExpanded = !this.isExpanded
    },
    selectNode() {
      this.$emit('select', this.chat)
    },
    onAddSubtask() {
      this.$emit('add-subtask', this.chat)
    }
  }
}
</script>