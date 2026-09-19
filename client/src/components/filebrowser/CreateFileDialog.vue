<script setup>
</script>

<template>
  <div v-if="isVisible" class="modal modal-open">
    <div class="modal-box">
      <h3 class="font-bold text-lg">{{ isDir ? 'Create Folder' : 'Create File' }}</h3>
      
      <div class="py-4 flex flex-col gap-3">
        <div class="form-control">
          <label class="label">
            <span class="label-text">{{ isDir ? 'Folder name' : 'File name' }}</span>
          </label>
          <input
            v-model="fileName"
            type="text"
            placeholder="Enter name"
            class="input input-bordered"
            @keydown.enter="onSubmit"
            @keydown.escape="onCancel"
            ref="inputRef"
          />
        </div>
        
        <div v-if="!isDir" class="form-control">
          <label class="label">
            <span class="label-text">Extension (optional)</span>
          </label>
          <input
            v-model="fileExtension"
            type="text"
            placeholder="e.g., js, md, txt"
            class="input input-bordered"
            @keydown.enter="onSubmit"
            @keydown.escape="onCancel"
          />
        </div>

        <div v-if="error" class="alert alert-error py-2">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span class="text-sm">{{ error }}</span>
        </div>
      </div>

      <div class="modal-action">
        <button class="btn btn-ghost" @click="onCancel">Cancel</button>
        <button class="btn btn-primary" @click="onSubmit" :disabled="!fileName.trim()">
          {{ isDir ? 'Create Folder' : 'Create File' }}
        </button>
      </div>
    </div>
    <div class="modal-backdrop" @click="onCancel"></div>
  </div>
</template>

<script>
export default {
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    isDir: {
      type: Boolean,
      default: false
    }
  },
  emits: ['create', 'cancel'],
  data() {
    return {
      fileName: '',
      fileExtension: '',
      error: null
    }
  },
  watch: {
    isVisible(newVal) {
      if (newVal) {
        this.fileName = ''
        this.fileExtension = ''
        this.error = null
        this.$nextTick(() => this.$refs.inputRef?.focus())
      }
    }
  },
  methods: {
    onSubmit() {
      this.error = null
      
      if (!this.fileName.trim()) {
        this.error = 'Name cannot be empty'
        return
      }

      const name = this.fileName.trim()
      const ext = this.fileExtension.trim()

      if (!this.isDir && name.includes('.')) {
        this.error = 'File name should not include extension in the name field'
        return
      }

      const fullName = ext ? `${name}.${ext}` : name

      this.$emit('create', {
        name: fullName,
        displayName: name
      })

      this.fileName = ''
      this.fileExtension = ''
    },
    onCancel() {
      this.$emit('cancel')
      this.fileName = ''
      this.fileExtension = ''
      this.error = null
    }
  }
}
</script>