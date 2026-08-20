<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ChatNavigatorNode from './ChatNavigatorNode.vue'
</script>

<template>
  <div>
    <!-- Trigger Button -->
    <button 
      class="btn btn-sm btn-ghost gap-2 tooltip"
      @click="openDrawer"
      :data-tip="`${totalDescendants} subtasks`"
      title="Open task navigator"
    >
      <i class="fa-solid fa-layer-group"></i>
      <span class="badge badge-sm badge-primary">{{ totalDescendants || childrenChats.length }}</span>
    </button>

    <!-- Drawer Backdrop & Panel -->
    <div 
      v-if="isOpen"
      class="fixed inset-0 z-50 flex"
      @click.self="closeDrawer"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/30" @click="closeDrawer"></div>

      <!-- Drawer Panel -->
      <div class="relative w-96 bg-base-100 shadow-xl flex flex-col h-full overflow-hidden">
        <!-- Header -->
        <div class="shrink-0 p-4 border-b border-base-content/10">
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-lg font-bold flex items-center gap-2">
              <i class="fa-solid fa-layer-group text-primary"></i>
              Task Navigator
            </h2>
            <button class="btn btn-sm btn-ghost" @click="closeDrawer">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <div v-if="rootChat" class="text-sm text-base-content/60">
            {{ rootChat.name }}
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="flex-1 flex items-center justify-center">
          <div class="flex flex-col items-center gap-2">
            <div class="loading loading-spinner loading-lg text-primary"></div>
            <span class="text-sm text-base-content/60">Loading tasks...</span>
          </div>
        </div>

        <!-- Tree Content -->
        <div v-else class="flex-1 overflow-y-auto p-4 scrollbar-thin space-y-2">
          <!-- Add New Task Button (First Entry) -->
          <button
            class="w-full p-3 rounded-lg border-2 border-dashed border-primary/50 bg-primary/5 hover:bg-primary/10 hover:border-primary transition-all flex items-center gap-2 text-primary font-semibold text-sm"
            @click="onAddNewTask"
          >
            <i class="fa-solid fa-plus text-lg"></i>
            Add New Task
          </button>

          <!-- Root Chat Card -->
          <div
            v-if="rootChat"
            class="p-3 rounded-lg border-2 cursor-pointer transition-all"
            :class="selectedChatId === rootChat.id
              ? 'border-warning bg-warning/10'
              : 'border-base-content/10 bg-base-200 hover:border-base-content/30'"
            @click="selectChat(rootChat)"
          >
            <div class="flex items-center gap-2 mb-1">
              <ChatIcon :mode="rootChat.mode" class="text-sm" />
              <span class="font-bold text-sm truncate flex-1">{{ rootChat.name }}</span>
              <span class="text-xs text-base-content/40">{{ rootChat.messages?.length || 0 }}</span>
            </div>
            <div v-if="rootChat.description" class="text-xs text-base-content/60 line-clamp-2">
              {{ rootChat.description }}
            </div>
            <div v-if="totalDescendants" class="text-xs text-primary mt-1">
              {{ totalDescendants }} subtasks
            </div>
          </div>

          <!-- CHANGED: Use allLoadedChats and selectedChatId from props -->
          <ChatNavigatorNode
            v-for="child in rootChildren"
            :key="child.id"
            :chat="child"
            :allChats="allLoadedChats"
            :selectedChatId="selectedChatId"
            :depth="0"
            @select="selectChat"
            @add-subtask="onAddSubtask"
          />

          <!-- Empty State -->
          <div v-if="!rootChildren.length && !isLoading" class="text-center text-sm text-base-content/40 py-8">
            <i class="fa-regular fa-inbox text-2xl block mb-2 opacity-50"></i>
            No subtasks yet
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  components: { ChatIcon, ChatNavigatorNode },
  props: {
    rootChat: {
      type: Object,
      required: true
    },
    allLoadedChats: {
      type: Array,
      default: () => []
    },
    selectedChatId: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      isOpen: false,
      isLoading: false
    }
  },
  computed: {
    childrenChats() {
      if (!this.rootChat?.id) return []
      return this.$chats.allChats.filter(c => c.parent_id === this.rootChat.id)
    },
    rootChildren() {
      if (!this.rootChat?.id) return []
      return this.allLoadedChats
        .filter(c => c.parent_id === this.rootChat.id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    totalDescendants() {
      if (!this.rootChat?.id) return 0
      const countDescendants = (parentId) => {
        return this.allLoadedChats
          .filter(c => c.parent_id === parentId)
          .reduce((sum, child) => sum + 1 + countDescendants(child.id), 0)
      }
      return countDescendants(this.rootChat.id)
    }
  },
  methods: {
    openDrawer() {
      this.isOpen = true
    },
    closeDrawer() {
      this.isOpen = false
    },
    selectChat(chat) {
      this.$emit('select', chat)
      this.closeDrawer()
    },
    onAddNewTask() {
      this.$emit('add-subtask', this.rootChat)
      this.closeDrawer()
    },
    onAddSubtask(parentChat) {
      this.$emit('add-subtask', parentChat)
    }
  }
}
</script>