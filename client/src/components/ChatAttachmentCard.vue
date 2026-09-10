<script setup>
import ChatAttachmentPreview from './chat/ChatAttachmentPreview.vue'
</script>

<template>
  <div class="rounded-lg border border-base-300 bg-base-100 overflow-hidden hover:bg-base-200/50 transition-colors">
    <!-- Card header -->
    <button 
      @click="$emit('toggle')"
      class="w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-base-200"
    >
      <i class="fa-solid fa-paperclip text-primary text-lg flex-shrink-0"></i>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-base-content">
          Attachments
        </p>
        <p class="text-xs text-base-content/60">
          {{ attachments.length }} file{{ attachments.length !== 1 ? 's' : '' }}
        </p>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        <span class="badge badge-xs badge-primary">{{ attachments.length }}</span>
        <i :class="isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'" class="fa-solid text-xs text-base-content/50"></i>
      </div>
    </button>

    <!-- Expanded content -->
    <div v-if="isExpanded && attachments.length > 0" class="px-3 py-2 border-t border-base-300 bg-base-100">
      <ChatAttachmentPreview
        :attachments="attachments"
        @remove-attachment="$emit('remove-attachment', $event)"
      />
    </div>

    <!-- Empty state -->
    <div v-if="isExpanded && attachments.length === 0" class="px-3 py-2 border-t border-base-300 bg-base-100 text-center text-xs text-base-content/50">
      No attachments
    </div>
  </div>
</template>

<script>
export default {
  components: {
    ChatAttachmentPreview
  },
  props: {
    attachments: {
      type: Array,
      default: () => [],
      validator(value) {
        return Array.isArray(value)
      }
    },
    isExpanded: {
      type: Boolean,
      default: true
    }
  },
  emits: ['toggle', 'remove-attachment']
}
</script>