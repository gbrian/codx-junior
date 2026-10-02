<template>
  <div v-if="show" class="modal modal-open">
    <div class="modal-box max-w-md">
      <h3 class="font-bold text-lg mb-4">
        <i class="fa-solid fa-cloud-arrow-up mr-2"></i>
        Confirm File Upload
      </h3>
      
      <div class="mb-4">
        <p class="text-sm text-gray-600 mb-3">
          Upload {{ files.length }} file(s) to <code class="text-xs bg-gray-100 px-2 py-1 rounded">{{ uploadPath }}</code>?
        </p>
        
        <div class="max-h-48 overflow-y-auto bg-gray-50 rounded p-2 border border-gray-200">
          <div v-for="(file, idx) in files" :key="idx" class="text-xs py-1 px-2 flex items-center gap-2">
            <i class="fa-solid fa-file text-gray-400"></i>
            <span class="truncate">{{ file.name }}</span>
            <span class="text-gray-400 ml-auto">{{ formatFileSize(file.size) }}</span>
          </div>
        </div>
      </div>

      <div class="modal-action">
        <button @click="$emit('cancel')" class="btn btn-ghost">
          Cancel
        </button>
        <button @click="$emit('confirm')" class="btn btn-primary">
          <i class="fa-solid fa-check mr-2"></i>
          Upload All
        </button>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button @click="$emit('cancel')"></button>
    </form>
  </div>
</template>

<script>
export default {
  props: {
    show: {
      type: Boolean,
      default: false
    },
    files: {
      type: Array,
      default: () => []
    },
    uploadPath: {
      type: String,
      default: '/upload'
    }
  },
  methods: {
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
  }
}
</script>