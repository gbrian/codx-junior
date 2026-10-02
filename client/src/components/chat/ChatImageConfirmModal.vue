<script setup>
import { onMounted, ref } from 'vue'
</script>

<template>
  <div v-if="show" class="modal modal-open">
    <div class="modal-box w-96 max-w-lg">
      <h3 class="font-bold text-lg mb-4">Add Image</h3>

      <!-- Image Preview -->
      <div class="mb-4 flex justify-center bg-base-200 rounded p-4 max-h-64 overflow-auto">
        <img
          v-if="image?.size"
          :src="`data:${image.type};base64,${image.base64_data}`"
          :alt="image.name"
          class="max-w-sm max-h-56 rounded"
        />
        <img
          v-else-if="typeof image === 'string'"
          :src="image"
          class="max-w-sm max-h-56 rounded"
        />
      </div>

      <!-- Image Info -->
      <div class="mb-4 text-sm space-y-2">
        <div v-if="image?.file_name" class="flex justify-between">
          <span class="font-semibold">Name:</span>
          <span class="text-right break-words">{{ image.file_name }}</span>
        </div>
        <div v-if="image?.file_size" class="flex justify-between">
          <span class="font-semibold">Size:</span>
          <span>{{ formatFileSize(image.file_size) }}</span>
        </div>
        <div v-if="image?.file_type" class="flex justify-between">
          <span class="font-semibold">Type:</span>
          <span>{{ image.file_type }}</span>
        </div>
      </div>

      <!-- Target Selection -->
      <div class="mb-4 flex gap-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            v-model="selectedTarget"
            value="message"
            class="radio radio-sm"
          />
          <span>Add to Message</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            v-model="selectedTarget"
            value="chat"
            class="radio radio-sm"
          />
          <span>Add to Chat</span>
        </label>
      </div>

      <!-- Actions -->
      <div class="modal-action gap-2">
        <button
          @click="onCancel"
          class="btn btn-sm btn-ghost"
        >
          Cancel
        </button>
        <button
          @click="onConfirm"
          class="btn btn-sm btn-primary"
        >
          Add Image
        </button>
      </div>
    </div>
    <div class="modal-backdrop" @click="onCancel"></div>
  </div>
</template>

<script>
export default {
  props: {
    show: {
      type: Boolean,
      default: false
    },
    image: {
      type: [Object, String],
      default: null
    },
    target: {
      type: String,
      default: 'message'
    }
  },
  data() {
    return {
      selectedTarget: this.target || 'message'
    }
  },
  watch: {
    show(newVal) {
      if (newVal) {
        this.selectedTarget = this.target || 'message'
      }
    }
  },
  methods: {
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
    },
    onConfirm() {
      this.$emit('confirm', this.selectedTarget)
    },
    onCancel() {
      this.$emit('cancel')
    }
  }
}
</script>