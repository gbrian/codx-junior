<script setup>
import ChatModeSelector from './ChatModeSelector.vue'
</script>

<template>
  <div class="h-auto border border-base-300 bg-base-100 rounded-lg px-3 md:px-6 py-2 md:py-2 flex flex-col overflow-hidden">
    
    <!-- ROW 1: Breadcrumb + Right Stats -->
    <div class="flex items-center gap-1 md:gap-2 text-xs min-w-0 min-h-5 md:min-h-6">
      <!-- Breadcrumb (left, truncated) -->
      <div class="flex items-center gap-1 md:gap-2 min-w-0 overflow-hidden">
        <span 
          class="text-primary font-bold truncate hover:underline cursor-pointer transition-colors whitespace-nowrap shrink-0"
          @click="$emit('select-breadcrumb', rootChat)"
          :title="rootChat.name"
        >
          {{ rootChat.name }}
        </span>
        <template v-for="(ancestor, idx) in breadcrumb" :key="ancestor.id">
          <i class="fa-solid fa-chevron-right text-xs opacity-50 shrink-0"></i>
          <span 
            class="truncate hover:underline cursor-pointer text-xs transition-colors hover:text-primary whitespace-nowrap"
            @click="$emit('select-breadcrumb', ancestor)"
            :title="ancestor.name"
          >
            {{ ancestor.name }}
          </span>
        </template>
      </div>
      
      <!-- Right side stats (hidden on mobile, compact on desktop) -->
      <div class="flex items-center gap-1 md:gap-2 ml-auto shrink-0">
        <!-- Template badge -->
        <span class="badge badge-warning badge-sm" v-if="chat.is_template">Template</span>
        <!-- Message Count Badge -->
        <div class="flex items-center gap-1 text-xs shrink-0 cursor-pointer hover:text-primary transition-colors"
          @click="$emit('toggle-hidden')"
        >
          <i class="fa-solid fa-message"></i>
          <span class="tabular-nums">{{ messageCount - hiddenCount }}</span>
          <span v-if="hiddenCount" class="flex items-center gap-1 text-warning/60">
            <i class="fa-solid fa-eye-slash text-xs"></i>
            {{ hiddenCount }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- ROW 2: Mode Selector + Title + Tags + Settings Toggles -->
    <div class="flex items-center gap-1 md:gap-2 min-w-0 min-h-5 md:min-h-6 mt-1">
      <!-- Chat Mode Selector (left, compact) -->
      <div class="shrink-0">
        <ChatModeSelector 
          :selected-mode="chat.mode"
          @mode-changed="$emit('mode-changed', $event)"
        />
      </div>

      <!-- Title (left, truncated) -->
      <div class="flex items-center gap-1 md:gap-2 min-w-0 flex-1 overflow-hidden">
        <input
          v-if="editingTitle"
          v-model="workingChatName"
          @keydown.enter="saveTitle"
          @keydown.esc="editingTitle = false"
          @blur="saveTitle"
          class="input input-sm input-bordered flex-1 min-w-0 text-sm"
          placeholder="Chat name..."
          autofocus
        />
        <span
          v-else
          class="font-bold text-base md:text-sm cursor-pointer hover:text-primary transition-colors truncate block"
          @dblclick="editingTitle = true"
          :title="chat.name"
        >
          {{ chat.name }}
        </span>
      </div>
      
      <!-- Tags (center-right) -->
      <div class="flex items-center gap-1 md:gap-2 shrink-0 overflow-hidden">
        <div class="flex items-center gap-0.5 md:gap-1 truncate">
          <div 
            v-for="tag in chat.tags" 
            :key="tag"
            class="badge badge-xs badge-outline text-xs shrink-0"
            :title="tag"
          >
            {{ tag }}
          </div>
        </div>
        
        <button
          @click.stop="$emit('show-add-tag')"
          class="btn btn-ghost btn-xs p-1 h-5 w-5 shrink-0"
          title="Add new tag"
        >
          <i class="fa-solid fa-hashtag text-xs"></i>
        </button>
      </div>

      <!-- Settings Toggles (right) -->
      <div class="flex items-center gap-1 md:gap-2 ml-auto shrink-0">
        <!-- Template Toggle -->
        <label 
          class="flex items-center gap-1 cursor-pointer tooltip tooltip-left"
          data-tip="Mark as template"
          :class="{ 'opacity-50': !isSelectedChatChild }"
        >
          <input 
            type="checkbox" 
            class="checkbox checkbox-xs"
            :checked="chat.is_template"
            @change="toggleTemplate"
          />
          <i class="fa-solid fa-star text-xs"></i>
        </label>

        <!-- Ignore Parent Knowledge Toggle (only for child chats) -->
        <label 
          v-if="isSelectedChatChild"
          class="flex items-center gap-1 cursor-pointer tooltip tooltip-left"
          data-tip="Ignore parent knowledge"
        >
          <input 
            type="checkbox" 
            class="checkbox checkbox-xs"
            :checked="chat.ignore_parent_knowledge"
            @change="toggleIgnoreParentKnowledge"
          />
          <i class="fa-solid fa-book-slash text-xs"></i>
        </label>

        <!-- Ignore Parent Files Toggle (only for child chats) -->
        <label 
          v-if="isSelectedChatChild"
          class="flex items-center gap-1 cursor-pointer tooltip tooltip-left"
          data-tip="Ignore parent files"
        >
          <input 
            type="checkbox" 
            class="checkbox checkbox-xs"
            :checked="chat.ignore_parent_files"
            @change="toggleIgnoreParentFiles"
          />
          <i class="fa-solid fa-file-slash text-xs"></i>
        </label>
      </div>
    </div>

  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, required: true },
    rootChat: { type: Object, required: true },
    breadcrumb: { type: Array, default: () => [] },
    messageCount: { type: Number, default: 0 },
    hiddenCount: { type: Number, default: 0 },
    showHidden: { type: Boolean, default: false },
    isSelectedChatChild: { type: Boolean, default: false }
  },
  emits: [
    'update-name',
    'toggle-hidden',
    'toggle-pinned',
    'select-project',
    'select-breadcrumb',
    'show-settings',
    'show-export',
    'confirm-delete',
    'show-add-tag',
    'remove-tag',
    'mode-changed',
    'toggle-template',
    'toggle-ignore-parent-knowledge',
    'toggle-ignore-parent-files'
  ],
  data() {
    return {
      editingTitle: false,
      workingChatName: ''
    }
  },
  watch: {
    chat: {
      immediate: true,
      handler(newVal) {
        this.workingChatName = newVal?.name || ''
      }
    }
  },
  methods: {
    saveTitle() {
      if (this.workingChatName.trim()) {
        this.chat.name = this.workingChatName
        this.$emit('update-name', this.chat)
      }
      this.editingTitle = false
    },
    toggleTemplate() {
      this.$emit('toggle-template', !this.chat.is_template)
    },
    toggleIgnoreParentKnowledge() {
      this.$emit('toggle-ignore-parent-knowledge', !this.chat.ignore_parent_knowledge)
    },
    toggleIgnoreParentFiles() {
      this.$emit('toggle-ignore-parent-files', !this.chat.ignore_parent_files)
    }
  }
}
</script>