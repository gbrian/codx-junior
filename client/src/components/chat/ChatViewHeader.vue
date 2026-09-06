<script setup>
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div class="h-16 border border-base-300 bg-base-100 rounded-lg px-6 flex items-center gap-4">

    <div class="flex flex-col">
      <!-- Breadcrumb Navigation -->
      <div class="flex items-center gap-2 text-xs min-w-0 flex-shrink-0 click">
        <span class="text-primary font-bold truncate">{{ rootChat.name }}</span>
        <template v-for="(ancestor, idx) in breadcrumb" :key="ancestor.id">
          <i class="fa-solid fa-chevron-right text-xs opacity-50"></i>
          <span class="truncate hover:underline cursor-pointer text-xs">{{ ancestor.name }}</span>
        </template>
      </div>
      <!-- Title (Editable Inline) -->
      <div class="flex gap-1 items-center min-w-0">
          <ProjectDetailt
            :iconify="true"
            :modelValue="targetProject"
            :options="{ showFolders: false, showIcon: true, showSelector: true }"
            @update:modelValue="$emit('select-project', $event)"
          />

        <input
          v-if="editingTitle"
          v-model="workingChatName"
          @keydown.enter="saveTitle"
          @keydown.esc="editingTitle = false"
          @blur="saveTitle"
          class="input input-sm input-bordered w-full"
          placeholder="Chat name..."
          autofocus
        />
        <span
          v-else
          class="font-bold text-base cursor-pointer hover:text-primary transition-colors truncate block"
          @dblclick="editingTitle = true"
          :title="chat.name"
        >
          {{ chat.name }}
        </span>
      </div>
    </div>
    <!-- Divider -->
    <div class="grow"></div>

    <!-- Message Count Badge -->
    <div class="flex items-center gap-1 text-xs text-base-content/60 shrink-0 click"
      @click="$emit('toggle-hidden')"
    >
      <i class="fa-solid fa-message"></i>
      <span class="tabular-nums">{{ messageCount }}</span>
      <span v-if="hiddenCount" class="flex items-center gap-1 text-warning">
        <i class="fa-solid fa-eye-slash text-xs"></i>
        {{ hiddenCount }}
      </span>
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
    targetProject: { type: Object, default: null }
  },
  emits: [
    'update-name',
    'toggle-hidden',
    'toggle-pinned',
    'select-project',
    'show-settings',
    'show-export',
    'confirm-delete'
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
    }
  }
}
</script>