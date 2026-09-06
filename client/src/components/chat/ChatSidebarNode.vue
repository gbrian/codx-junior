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

        <!-- Context Menu -->
        <div class="opacity-0 group-hover/node:opacity-100 transition-opacity shrink-0">
          <div class="dropdown dropdown-end">
            <button 
              class="btn btn-xs btn-ghost"
              @click.stop
            >
              <i class="fa-solid fa-ellipsis-h text-xs"></i>
            </button>
            <ul class="dropdown-content menu bg-base-100 rounded-lg shadow-lg w-40 p-1 z-50 text-xs">
              <li><a @click.stop="$emit('select', chat)">Open</a></li>
              <li><a @click.stop="$emit('add-subtask', chat)">New Subtask</a></li>
              <li class="divider m-0"></li>
              <li><a @click.stop="togglePin" class="text-warning">
                <i :class="chat.pinned ? 'fa-solid fa-bookmark' : 'fa-regular fa-bookmark'"></i>
                {{ chat.pinned ? 'Unpin' : 'Pin' }}
              </a></li>
              <li><a @click.stop="toggleArchive" class="text-info">
                <i class="fa-solid fa-box-archive"></i> Archive
              </a></li>
            </ul>
          </div>
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
  emits: ['select', 'add-subtask'],
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
    },
    togglePin() {
      this.chat.pinned = !this.chat.pinned
    },
    toggleArchive() {
      this.chat.hide = !this.chat.hide
    }
  }
}
</script>