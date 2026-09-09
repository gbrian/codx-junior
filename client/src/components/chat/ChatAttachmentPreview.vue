<script setup>
import ChatAttachment from '@/api/model/ChatAttachment.js'
</script>

<template>
  <div class="flex flex-col gap-2 bg-base-200/50 rounded-lg p-3 border border-base-300">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <i class="fa-solid fa-paperclip text-primary text-sm"></i>
        <span class="font-medium text-xs">Attachments</span>
        <span class="badge badge-xs badge-ghost">{{ fileObjects.length }}</span>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="fileObjects.length === 0" class="text-xs text-base-content/50 text-center py-3">
      No attachments
    </div>

    <!-- Thumbnail Grid -->
    <div v-else class="flex gap-2 overflow-x-auto pb-1">
      <div
        v-for="(attachment, idx) in fileObjects"
        :key="idx"
        class="relative group flex-shrink-0 cursor-pointer"
        @click="openPreview(idx)"
      >
        <!-- Thumbnail Container -->
        <div class="w-12 h-12 rounded-lg overflow-hidden border border-base-300 bg-base-100 flex items-center justify-center hover:border-primary transition-colors">
          <!-- Image Thumbnail -->
          <img
            v-if="attachment.isImage()"
            :src="`data:${attachment.file_type};base64,${attachment.base64_data}`"
            :alt="attachment.file_name"
            class="w-full h-full object-cover"
          />

          <!-- File Icon Thumbnail -->
          <div v-else class="w-full h-full bg-gradient-to-br from-base-200 to-base-300 flex flex-col items-center justify-center gap-1">
            <i :class="getFileIcon(attachment)" class="text-3xl opacity-60"></i>
            <span class="text-xs font-medium text-base-content/60">{{ attachment.getExtension().toUpperCase() }}</span>
          </div>
        </div>

        <!-- Tooltip -->
        <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-base-900 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
          {{ attachment.file_name }}
        </div>
      </div>
    </div>

    <!-- Summary -->
    <div v-if="fileObjects.length > 0" class="text-xs text-base-content/60 border-t border-base-300/50 pt-2 mt-1">
      Total: <span class="font-semibold text-base-content">{{ getTotalSize() }}</span>
    </div>
  </div>

  <!-- Preview Modal -->
  <modal
    v-if="selectedIndex !== null && showModal"
    :close="true"
    @close="closePreview"
    class="w-full max-w-2xl"
  >
    <template #title>
      <div class="flex items-center gap-2">
        <i :class="getFileIcon(currentAttachment)" class="text-lg"></i>
        <span>{{ currentAttachment.file_name }}</span>
      </div>
    </template>

    <!-- Preview Content -->
    <div class="flex flex-col gap-4">
      <!-- Image Preview -->
      <img
        v-if="currentAttachment.isImage()"
        :src="`data:${currentAttachment.file_type};base64,${currentAttachment.base64_data}`"
        :alt="currentAttachment.file_name"
        class="w-full h-auto rounded-lg max-h-96 object-contain"
      />

      <!-- File Icon Preview -->
      <div v-else class="w-full h-64 bg-gradient-to-br from-base-200 to-base-300 rounded-lg flex flex-col items-center justify-center gap-3">
        <i :class="getFileIcon(currentAttachment)" class="text-6xl opacity-40"></i>
        <span class="text-sm font-medium text-base-content/60">{{ currentAttachment.getExtension().toUpperCase() }}</span>
      </div>

      <!-- File Info -->
      <div class="grid grid-cols-2 gap-4 p-3 bg-base-200/50 rounded-lg">
        <div>
          <div class="text-xs font-medium text-base-content/60">File Name</div>
          <div class="text-sm font-semibold text-base-content break-all">{{ currentAttachment.file_name }}</div>
        </div>
        <div>
          <div class="text-xs font-medium text-base-content/60">File Size</div>
          <div class="text-sm font-semibold text-base-content">{{ currentAttachment.getFormattedSize() }}</div>
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <template #footer>
      <button
        class="btn btn-sm btn-primary"
        @click="downloadAttachment(currentAttachment)"
      >
        <i class="fa-solid fa-download"></i>
        Download
      </button>
      <button
        class="btn btn-sm btn-error"
        @click="removeAndClose"
      >
        <i class="fa-solid fa-trash"></i>
        Remove
      </button>
    </template>
  </modal>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'

export default {
  name: 'ChatAttachmentPreview',
  props: {
    attachments: {
      type: Array,
      default: () => [],
      validator(value) {
        return Array.isArray(value)
      }
    },
    showSelector: {
      type: Boolean,
      default: false
    }
  },
  emits: ['remove-attachment'],
  data() {
    return {
      fileObjects: [],
      showModal: false,
      selectedIndex: null
    }
  },
  computed: {
    currentAttachment() {
      return this.selectedIndex !== null ? this.fileObjects[this.selectedIndex] : null
    }
  },
  watch: {
    attachments: {
      immediate: true,
      handler(newVal) {
        this.fileObjects = newVal.map(attachment => {
          if (attachment instanceof ChatAttachment) {
            return attachment
          }
          return ChatAttachment.fromJSON(attachment)
        })
      }
    }
  },
  methods: {
    openPreview(idx) {
      this.selectedIndex = idx
      this.showModal = true
    },
    closePreview() {
      this.showModal = false
      this.selectedIndex = null
    },
    removeAndClose() {
      this.removeAttachmentItem(this.selectedIndex)
      this.closePreview()
    },
    removeAttachmentItem(idx) {
      this.$emit('remove-attachment', idx)
    },
    getFileIcon(attachment) {
      const ext = attachment.getExtension()
      const iconMap = {
        'pdf': 'fa-solid fa-file-pdf text-red-500',
        'doc': 'fa-solid fa-file-word text-blue-500',
        'docx': 'fa-solid fa-file-word text-blue-500',
        'xls': 'fa-solid fa-file-excel text-green-500',
        'xlsx': 'fa-solid fa-file-excel text-green-500',
        'ppt': 'fa-solid fa-file-powerpoint text-orange-500',
        'pptx': 'fa-solid fa-file-powerpoint text-orange-500',
        'txt': 'fa-solid fa-file-lines text-gray-500',
        'zip': 'fa-solid fa-file-zipper text-yellow-600',
        'json': 'fa-solid fa-file-code text-purple-500',
        'xml': 'fa-solid fa-file-code text-purple-500',
        'png': 'fa-solid fa-image text-cyan-500',
        'jpg': 'fa-solid fa-image text-cyan-500',
        'jpeg': 'fa-solid fa-image text-cyan-500',
        'gif': 'fa-solid fa-image text-cyan-500',
        'svg': 'fa-solid fa-image text-cyan-500'
      }
      return iconMap[ext] || 'fa-solid fa-file text-base-content/40'
    },
    downloadAttachment(attachment) {
      const link = document.createElement('a')
      const dataUrl = `data:${attachment.file_type};base64,${attachment.base64_data}`
      link.href = dataUrl
      link.download = attachment.file_name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    },
    getTotalSize() {
      const total = this.fileObjects.reduce((sum, att) => sum + att.file_size, 0)
      return ChatAttachment.formatSize(total)
    }
  }
}
</script>