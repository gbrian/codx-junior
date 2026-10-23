<script setup>
import ChatModeSelector from './ChatModeSelector.vue'
import ChatStatusSelector from './ChatStatusSelector.vue'
import ChatCostSelector from './ChatCostSelector.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div
    class="h-auto border border-base-100 rounded-xl flex flex-col shadow-sm"
    :class="isMobile ? 'px-2 py-1 gap-2' : 'px-6 py-3 gap-3'"
  >
    <!-- ═══════════════════════ MOBILE ═══════════════════════ -->
    <!-- Collapsed by default: only back • title • details toggle, so the chat
         keeps the vertical space. Every other control (breadcrumb, project,
         status, cost, counters, tags, flags, actions) lives in the panel that
         opens with the toggle. -->
    <template v-if="isMobile">
      <div class="flex items-center gap-1 min-w-0">
        <button
          class="btn btn-ghost btn-sm btn-circle shrink-0"
          @click="$emit('back')"
          title="Back"
          aria-label="Go back"
        >
          <i class="fa-solid fa-arrow-left"></i>
        </button>

        <!-- Title (editable) -->
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

        <!-- Details toggle -->
        <button
          class="btn btn-ghost btn-sm btn-circle shrink-0"
          @click="$emit('toggle-mobile-details', !mobileExpanded)"
          :title="mobileExpanded ? 'Hide chat details' : 'Show chat details'"
          :aria-expanded="mobileExpanded"
          aria-label="Toggle chat details"
        >
          <i :class="mobileExpanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-sliders'"></i>
        </button>
      </div>

      <!-- Expandable details panel -->
      <div
        v-show="mobileExpanded"
        class="flex flex-col gap-3 pt-3 border-t border-base-300"
      >
        <!-- Breadcrumb (only when nested) -->
        <div
          v-if="breadcrumb.length"
          class="flex items-center gap-1 text-xs text-base-content/50 min-w-0 overflow-hidden"
        >
          <button
            @click="$emit('select-breadcrumb', rootChat)"
            :title="rootChat.name"
            class="text-primary truncate hover:text-primary/80 focus:ring-2 focus:ring-primary/50 rounded px-1 py-0.5 outline-none whitespace-nowrap max-w-24"
          >
            {{ rootChat.name }}
          </button>
          <template v-for="(ancestor, idx) in breadcrumb" :key="ancestor.id">
            <i class="fa-solid fa-chevron-right text-[10px] opacity-40 shrink-0"></i>
            <button
              @click="$emit('select-breadcrumb', ancestor)"
              :title="ancestor.name"
              class="truncate hover:text-primary focus:ring-2 focus:ring-primary/50 rounded px-1 py-0.5 outline-none whitespace-nowrap max-w-24"
            >
              {{ ancestor.name }}
            </button>
          </template>
        </div>

        <!-- Project -->
        <div class="flex flex-wrap items-center gap-2">
          <ProjectDetailt
            @click.stop=""
            :iconify="true"
            :modelValue="currentProject"
            @update:modelValue="$emit('select-project', $event)"
          />
        </div>

        <!-- Status + Cost + Messages -->
        <div class="flex flex-wrap items-center gap-2">
          <ChatStatusSelector
            :status="chat.status"
            @status-changed="onStatusChanged"
          />
          <ChatCostSelector
            class="shrink-0"
            variant="chip"
            :cost="chat.cost || 0"
            :estimation-cost="chat.estimation_cost"
            @cost-changed="$emit('cost-changed', $event)"
          />
          <button
            @click="$emit('toggle-hidden')"
            class="btn btn-sm gap-1.5"
            :title="`${messageCount - hiddenCount} visible${hiddenCount ? `, ${hiddenCount} hidden` : ''}`"
          >
            <i class="fa-solid fa-message text-xs"></i>
            <span class="tabular-nums">{{ messageCount - hiddenCount }}</span>
            <span v-if="hiddenCount" class="flex items-center gap-1 text-warning/70">
              <i class="fa-solid fa-eye-slash text-xs"></i> {{ hiddenCount }}
            </span>
          </button>
        </div>

        <!-- Tags -->
        <div class="flex items-center gap-2 flex-wrap">
          <span
            v-for="tag in chat.tags"
            :key="tag"
            class="badge badge-outline badge-sm whitespace-nowrap"
          >
            {{ tag }}
          </span>
          <button
            class="btn btn-ghost btn-xs gap-1.5"
            @click.stop="$emit('show-add-tag')"
          >
            <i class="fa-solid fa-hashtag text-xs"></i>
            {{ chat.tags?.length ? 'Add tag' : 'Add first tag' }}
          </button>
        </div>

        <!-- Flags -->
        <div class="flex items-center gap-1.5 flex-wrap">
          <button
            class="btn btn-sm btn-ghost gap-1.5 focus:ring-2 focus:ring-primary/50"
            :class="chat.is_template ? 'text-warning' : 'text-base-content/50'"
            @click="toggleTemplate()"
          >
            <i class="fa-solid fa-star text-xs"></i> Template
          </button>
          <button
            v-if="isSelectedChatChild"
            class="btn btn-sm btn-ghost gap-1.5 focus:ring-2 focus:ring-primary/50"
            :class="chat.ignore_parent_knowledge ? 'text-base-content/50' : 'text-info'"
            @click="toggleIgnoreParentKnowledge()"
          >
            <i class="fa-solid fa-brain text-xs"></i> Parent knowledge
          </button>
          <button
            v-if="isSelectedChatChild"
            class="btn btn-sm btn-ghost gap-1.5 focus:ring-2 focus:ring-primary/50"
            :class="chat.ignore_parent_files ? 'text-base-content/50' : 'text-info'"
            @click="toggleIgnoreParentFiles()"
          >
            <i class="fa-solid fa-file text-xs"></i> Parent files
          </button>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1.5 flex-wrap">
          <button class="btn btn-sm btn-ghost gap-1.5" @click.stop="$emit('show-sidebar')">
            <i class="fa-solid fa-sitemap text-xs"></i> Tasks
          </button>
          <button class="btn btn-sm btn-ghost gap-1.5" @click.stop="$emit('show-settings')">
            <i class="fa-solid fa-gear text-xs"></i> Settings
          </button>
          <button class="btn btn-sm btn-ghost gap-1.5" @click.stop="$emit('show-export')">
            <i class="fa-solid fa-download text-xs"></i> Export
          </button>
          <button class="btn btn-sm btn-ghost gap-1.5 text-error" @click.stop="$emit('confirm-delete')">
            <i class="fa-solid fa-trash text-xs"></i> Delete
          </button>
        </div>
      </div>
    </template>

    <!-- ═══════════════════════ DESKTOP ═══════════════════════ -->
    <template v-else>
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

          <!-- Cost / Budget Control (reusable component) -->
          <ChatCostSelector
            variant="chip"
            :cost="chat.cost || 0"
            :estimation-cost="chat.estimation_cost"
            @cost-changed="$emit('cost-changed', $event)"
          />
          
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
      
      <!-- ROW 2: Project Selector + Title + Tags + Status + Toggles + Mode Selector -->
      <div class="flex items-center gap-3 min-w-0 flex-wrap">
        <!-- Project Detail Selector (Fixed Width) -->
        <div class="shrink-0">
          <ProjectDetailt
            @click.stop=""
            :iconify="true"
            :modelValue="currentProject"
            :options="{ showFolders: false, showIcon: true, showSelector: true }"
            @update:modelValue="$emit('select-project', $event)"
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

        <!-- Settings Toggles + Mode Selector (Right) -->
        <div class="flex items-center gap-1.5 ml-auto shrink-0">
          
          <!-- Template Toggle (Icon Button) -->
          <button
            @click="toggleTemplate"
            class="tooltip tooltip-bottom focus:ring-2 focus:ring-primary/50 rounded p-1 transition-colors duration-150 outline-none"
            :class="chat.is_template ? 'text-warning' : 'text-gray-500'"
            :data-tip="chat.is_template ? 'Remove from templates' : 'Mark as template'"
          >
            <i class="fa-solid fa-star text-sm"></i>
          </button>

          <!-- Ignore Parent Knowledge (Child Only) -->
          <button
            v-if="isSelectedChatChild"
            @click="toggleIgnoreParentKnowledge"
            class="tooltip tooltip-bottom focus:ring-2 focus:ring-primary/50 rounded p-1 transition-colors duration-150 outline-none"
            :class="chat.ignore_parent_knowledge ? 'text-gray-500' : 'text-info'"
            :data-tip="chat.ignore_parent_knowledge ? 'Enable parent knowledge' : 'Ignore parent knowledge'"
          >
            <i class="fa-solid fa-brain text-sm"></i>
          </button>

          <!-- Ignore Parent Files (Child Only) -->
          <button
            v-if="isSelectedChatChild"
            @click="toggleIgnoreParentFiles"
            class="tooltip tooltip-bottom focus:ring-2 focus:ring-primary/50 rounded p-1 transition-colors duration-150 outline-none"
            :class="chat.ignore_parent_files ? 'text-gray-500' : 'text-info'"
            :data-tip="chat.ignore_parent_files ? 'Enable parent files' : 'Ignore parent files'"
          >
            <i class="fa-solid fa-file text-sm"></i>
          </button>

          <!-- Chat Mode Selector (After Parent Flags) -->
          <div class="shrink-0">
            <ChatModeSelector 
              :selected-mode="chat.mode"
              @mode-changed="$emit('mode-changed', $event)"
            />
          </div>
        </div>
      </div>
    </template>
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
    isSelectedChatChild: { type: Boolean, default: false },
    targetProject: { type: Object, default: null },
    // Mobile only: the details panel is controlled by the parent so it can hide
    // other mobile chrome (e.g. the chat files strip) while collapsed.
    mobileExpanded: { type: Boolean, default: false }
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
    'status-changed',
    'cost-changed',
    'back',
    'show-sidebar',
    'toggle-mobile-details'
  ],
  data() {
    return {
      editingTitle: false,
      workingChatName: ''
    }
  },
  computed: {
    isMobile() {
      return this.$ui?.isMobile
    },
    // Project this chat works against. The chat's OWN working project
    // (`project_id`) always wins over the parent-provided `targetProject` so a
    // task created against another codebase shows the same project it was
    // created with (the sprint card renders `chat.project_id` too). The prop is
    // only a fallback for chats that don't resolve to a loaded project.
    currentProject() {
      const id = this.chat?.project_id || this.chat?.owner_project_id
      return (id && this.$storex.projects.allProjectsById?.[id]) || this.targetProject || null
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