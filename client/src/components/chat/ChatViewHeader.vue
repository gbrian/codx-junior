<script setup>
import ChatModeSelector from './ChatModeSelector.vue'
import ChatStatusSelector from './ChatStatusSelector.vue'
</script>

<template>
  <div class="h-auto border border-base-100 rounded-xl px-6 py-3 flex flex-col gap-3 shadow-sm">
    
    <!-- ROW 1: Breadcrumb + Stats (Left + Right) -->
    <div class="flex items-center gap-3 text-xs min-w-0">
      <!-- Breadcrumb Navigation (Left, Truncated) -->
      <div class="flex items-center gap-2 min-w-0 overflow-hidden flex-1">
        <button
          @click="$emit('select-breadcrumb', rootChat)"
          :title="rootChat.name"
          class="text-sm font-semibold text-primary truncate hover:text-primary/80 focus:ring-2 focus:ring-primary/50 rounded px-1 py-0.5 transition-colors duration-150 outline-none whitespace-nowrap shrink-0"
        >
          {{ rootChat.name }}
        </button>
        
        <template v-for="(ancestor, idx) in breadcrumb" :key="ancestor.id">
          <i class="fa-solid fa-chevron-right text-xs opacity-40 shrink-0"></i>
          <button
            @click="$emit('select-breadcrumb', ancestor)"
            :title="ancestor.name"
            class="text-xs text-base-content/70 truncate hover:text-primary focus:ring-2 focus:ring-primary/50 rounded px-1 py-0.5 transition-colors duration-150 outline-none whitespace-nowrap"
          >
            {{ ancestor.name }}
          </button>
        </template>
      </div>
      
      <!-- Right Stats (Compact) -->
      <div class="flex items-center gap-2 ml-auto shrink-0">
        <!-- Template Badge -->
        <div v-if="chat.is_template" class="badge badge-warning badge-sm text-xs" title="This is a template">
          <i class="fa-solid fa-star text-xs mr-1"></i>
          Template
        </div>
        
        <!-- Message Count -->
        <button
          @click="$emit('toggle-hidden')"
          :title="`${messageCount - hiddenCount} visible${hiddenCount ? `, ${hiddenCount} hidden` : ''}`"
          class="flex items-center gap-1.5 text-xs text-base-content/60 hover:text-base-content/90 focus:ring-2 focus:ring-primary/50 rounded px-2 py-1 transition-colors duration-150 outline-none"
        >
          <i class="fa-solid fa-message text-xs"></i>
          <span class="tabular-nums font-medium">{{ messageCount - hiddenCount }}</span>
          <span v-if="hiddenCount" class="flex items-center gap-1 text-warning/70">
            <i class="fa-solid fa-eye-slash text-xs"></i>
            {{ hiddenCount }}
          </span>
        </button>
      </div>
    </div>
    
    <!-- ROW 2: Mode + Title + Tags + Status + Settings -->
    <div class="flex items-center gap-3 min-w-0 flex-wrap">
      <!-- Chat Mode Selector (Fixed Width) -->
      <div class="shrink-0">
        <ChatModeSelector 
          :selected-mode="chat.mode"
          @mode-changed="$emit('mode-changed', $event)"
        />
      </div>

      <!-- Divider -->
      <div class="w-px h-5 bg-base-300 shrink-0 hidden sm:block"></div>

      <!-- Title (Editable) -->
      <div class="flex-1 min-w-0">
        <input
          v-if="editingTitle"
          v-model="workingChatName"
          @keydown.enter="saveTitle"
          @keydown.esc="editingTitle = false"
          @blur="saveTitle"
          class="input input-sm input-bordered w-full text-sm focus:ring-2 focus:ring-primary/50 focus:border-primary/50"
          placeholder="Chat name..."
          autofocus
        />
        <button
          v-else
          @dblclick="editingTitle = true"
          :title="chat.name"
          class="text-sm font-semibold text-base-content truncate hover:text-primary focus:ring-2 focus:ring-primary/50 rounded px-1 py-0.5 transition-colors duration-150 outline-none block w-full text-left"
        >
          <span v-if="chat.auto_initialize">*</span>{{ chat.name }}
        </button>
      </div>
      
      <!-- Tags Section -->
      <div class="flex items-center gap-2 shrink-0 overflow-x-auto">
        <div class="flex items-center gap-1">
          <div 
            v-for="tag in chat.tags" 
            :key="tag"
            class="badge badge-outline badge-sm text-xs whitespace-nowrap"
            :title="tag"
          >
            {{ tag }}
          </div>
        </div>
        
        <button
          @click.stop="$emit('show-add-tag')"
          :title="chat.tags?.length ? 'Add another tag' : 'Add first tag'"
          class="btn btn-ghost btn-xs p-1 h-6 w-6 shrink-0 focus:ring-2 focus:ring-primary/50"
        >
          <i class="fa-solid fa-hashtag text-xs"></i>
        </button>
      </div>

      <!-- Status Selector -->
      <div class="shrink-0 relative">
        <ChatStatusSelector
          :status="chat.status"
          @status-changed="onStatusChanged"
        />
      </div>

      <!-- Settings Toggles (Right) -->
      <div class="flex items-center gap-1.5 ml-auto shrink-0">
        
        <!-- Template Toggle (Available for All) -->
        <label 
          class="tooltip tooltip-bottom"
          data-tip="Mark as template"
        >
          <input 
            type="checkbox" 
            class="checkbox checkbox-sm focus:ring-2 focus:ring-primary/50"
            :checked="chat.is_template"
            @change="toggleTemplate"
          />
        </label>

        <!-- Ignore Parent Knowledge (Child Only) -->
        <label 
          v-if="isSelectedChatChild"
          class="tooltip tooltip-bottom"
          data-tip="Ignore parent knowledge"
        >
          <input 
            type="checkbox" 
            class="checkbox checkbox-sm focus:ring-2 focus:ring-primary/50"
            :checked="chat.ignore_parent_knowledge"
            @change="toggleIgnoreParentKnowledge"
          />
        </label>

        <!-- Ignore Parent Files (Child Only) -->
        <label 
          v-if="isSelectedChatChild"
          class="tooltip tooltip-bottom"
          data-tip="Ignore parent files"
        >
          <input 
            type="checkbox" 
            class="checkbox checkbox-sm focus:ring-2 focus:ring-primary/50"
            :checked="chat.ignore_parent_files"
            @change="toggleIgnoreParentFiles"
          />
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
    'toggle-ignore-parent-files',
    'status-changed'
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
    },
    onStatusChanged(newStatus) {
      this.$emit('status-changed', newStatus)
    }
  }
}
</script>