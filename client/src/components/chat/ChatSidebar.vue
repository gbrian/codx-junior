<script setup>
import ChatIcon from './ChatIcon.vue'
import ChatModeSelector from './ChatModeSelector.vue'
import ChatSidebarNode from './ChatSidebarNode.vue'
</script>

<template>
  <div class="w-64 border-r border-base-300 bg-base-100 flex flex-col h-full overflow-hidden">
    
    <!-- Root Chat Card -->
    <div class="p-3 border-b border-base-300 shrink-0">
      <div
        class="p-3 rounded-lg border-2 cursor-pointer transition-all hover:border-warning hover:bg-warning/5"
        :class="selectedChatId === rootChat.id 
          ? 'border-warning bg-warning/10' 
          : 'border-base-content/10 bg-base-200'"
        @click="selectChat(rootChat)"
      >
        <div class="flex items-center gap-2 mb-1">
          <ChatIcon :mode="rootChat.mode" class="shrink-0" />
          <span class="font-bold text-sm flex-1 truncate">{{ rootChat.name }}</span>
          <span class="text-xs text-base-content/40 shrink-0 tabular-nums">
            {{ rootChat.messages?.length || 0 }}
          </span>
        </div>
        <div v-if="rootChat.description" class="text-xs text-base-content/60 line-clamp-2">
          {{ rootChat.description }}
        </div>
      </div>
    </div>

    <!-- Mode Selector (Root Chat Only) -->
    <div class="px-3 py-2 border-b border-base-300 shrink-0">
      <ChatModeSelector 
        :selected-mode="rootChat.mode"
        @mode-changed="onRootModeChanged"
      />
    </div>

    <!-- Parent Content Controls (When Selected Chat is a Child Task) -->
    <div class="px-3 py-2 border-b border-base-300 shrink-0 space-y-2" v-if="isSelectedChatChild">
      <div class="text-xs font-semibold text-base-content/60 uppercase">Parent Content</div>
      
      <!-- Ignore Parent Knowledge -->
      <label class="flex items-center gap-2 cursor-pointer hover:bg-base-200/50 px-2 py-1 rounded transition-colors">
        <input 
          type="checkbox" 
          class="checkbox checkbox-sm"
          :checked="selectedChat?.ignore_parent_knowledge"
          @change="toggleIgnoreParentKnowledge"
        />
        <span class="text-xs flex-1">Ignore parent knowledge</span>
        <i class="fa-solid fa-circle-question text-xs text-base-content/40 tooltip" data-tip="Don't use parent chat context"></i>
      </label>

      <!-- Ignore Parent Files -->
      <label class="flex items-center gap-2 cursor-pointer hover:bg-base-200/50 px-2 py-1 rounded transition-colors">
        <input 
          type="checkbox" 
          class="checkbox checkbox-sm"
          :checked="selectedChat?.ignore_parent_files"
          @change="toggleIgnoreParentFiles"
        />
        <span class="text-xs flex-1">Ignore parent files</span>
        <i class="fa-solid fa-circle-question text-xs text-base-content/40 tooltip" data-tip="Don't inherit parent file list"></i>
      </label>
    </div>

    <!-- Quick Actions -->
    <div class="px-3 py-2 border-b border-base-300 shrink-0 space-y-1">
      <button 
        class="btn btn-sm btn-block btn-ghost justify-start gap-2 text-xs"
        @click="$emit('add-subtask', rootChat)"
      >
        <i class="fa-solid fa-plus"></i> New Subtask
      </button>
      <button 
        class="btn btn-sm btn-block btn-ghost justify-start gap-2 text-xs"
        @click="$emit('action', { type: 'new-tag' })"
      >
        <i class="fa-solid fa-hashtag"></i> Add Tag
      </button>
    </div>

    <!-- Hierarchy Tree -->
    <div class="flex-1 overflow-y-auto p-3 space-y-2 min-h-0">
      <ChatSidebarNode
        v-for="child in rootChildren"
        :key="child.id"
        :chat="child"
        :allChats="allChats"
        :selectedChatId="selectedChatId"
        @select="selectChat"
      />
    </div>

    <!-- Footer: Actions -->
    <div class="border-t border-base-300 p-3 space-y-1 shrink-0">
      <button 
        class="btn btn-xs btn-block btn-ghost justify-start gap-2"
        @click="$emit('action', { type: 'timeline' })"
      >
        <i class="fa-solid fa-timeline"></i> Timeline
      </button>
      <button 
        class="btn btn-xs btn-block btn-ghost justify-start gap-2"
        @click="$emit('action', { type: 'export' })"
      >
        <i class="fa-solid fa-download"></i> Export
      </button>
      <button 
        class="btn btn-xs btn-block btn-ghost justify-start gap-2"
        @click="$emit('action', { type: 'settings' })"
      >
        <i class="fa-solid fa-gear"></i> Settings
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    rootChat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null },
    workingChatMode: { type: String, default: 'chat' },
    chatSearch: { type: String, default: null }
  },
  emits: ['select', 'add-subtask', 'action', 'update-search', 'mode-changed', 'parent-flags-changed'],
  computed: {
    rootChildren() {
      return this.allChats.filter(c => c.parent_id === this.rootChat.id)
    },
    selectedChat() {
      return this.allChats.find(c => c.id === this.selectedChatId) || this.rootChat
    },
    isSelectedChatChild() {
      return this.selectedChat && this.selectedChat.parent_id && this.selectedChat.id !== this.rootChat.id
    }
  },
  methods: {
    selectChat(chat) {
      this.$emit('select', chat)
    },
    onRootModeChanged(newMode) {
      this.rootChat.mode = newMode
      this.$emit('mode-changed', { chat: this.rootChat, mode: newMode })
    },
    toggleIgnoreParentKnowledge() {
      if (!this.selectedChat) return
      this.selectedChat.ignore_parent_knowledge = !this.selectedChat.ignore_parent_knowledge
      this.$emit('parent-flags-changed', {
        chat: this.selectedChat,
        flag: 'ignore_parent_knowledge',
        value: this.selectedChat.ignore_parent_knowledge
      })
    },
    toggleIgnoreParentFiles() {
      if (!this.selectedChat) return
      this.selectedChat.ignore_parent_files = !this.selectedChat.ignore_parent_files
      this.$emit('parent-flags-changed', {
        chat: this.selectedChat,
        flag: 'ignore_parent_files',
        value: this.selectedChat.ignore_parent_files
      })
    }
  }
}
</script>