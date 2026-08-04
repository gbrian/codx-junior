<script setup>
import moment from 'moment'
import hljs from 'highlight.js'
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import Editor from '../monaco/Editor.vue'
import { EXTENSION_LANGUAGE_MAP } from '@/store'
</script>

<template>
  <div class="w-full h-full flex flex-col overflow-hidden">
    <!-- File header -->
    <div class="flex items-center gap-3 px-3 py-2 bg-base-200 border-b border-base-300 flex-shrink-0">
      <i class="fa-regular fa-file text-info"></i>
      <span
        class="text-sm font-mono font-semibold truncate cursor-move hover:opacity-75 transition-opacity"
        :title="displayFilePath"
        draggable="true"
        @dragstart="onDragStart"
        @dragend="onDragEnd"
      >
        {{ displayFileName }}
      </span>
      <span class="text-xs opacity-50" v-if="fileMeta.size !== null">
        {{ formatSize(fileMeta.size) }}
      </span>
      <span class="text-xs opacity-50" v-if="fileMeta.last_modification">
        {{ moment(fileMeta.last_modification).fromNow() }}
      </span>
      
      <!-- Unsaved changes indicator -->
      <div class="flex items-center gap-2" v-if="editMode && hasChanges">
        <div class="flex items-center gap-1 px-2 py-1 bg-warning rounded text-warning-content text-xs">
          <i class="fa-solid fa-circle-exclamation"></i>
          <span>Unsaved changes</span>
        </div>
      </div>

      <div class="grow"></div>

      <button class="btn btn-xs btn-ghost" title="Reload file" @click="reloadFile" v-if="!editMode && !loading">
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Copy content" @click="copyContent" v-if="!editMode">
        <i class="fa-solid fa-copy"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Delete file" @click="showDeleteConfirm" v-if="!editMode">
        <i class="fa-solid fa-trash"></i>
      </button>
      <button class="btn btn-xs btn-outline" @click="startEdit" v-if="!editMode && !isBinary">
        <i class="fa-solid fa-pen"></i> Edit
      </button>
      <template v-if="editMode">
        <button 
          class="btn btn-xs" 
          :class="showDiff ? 'btn-info' : 'btn-ghost'"
          title="Show diff"
          @click="toggleDiff"
        >
          <i class="fa-solid fa-code-compare"></i> Diff
        </button>
        <button 
          class="btn btn-xs btn-ghost" 
          :disabled="!hasChanges"
          @click="discardChanges"
          title="Discard unsaved changes"
        >
          <i class="fa-solid fa-times"></i> Discard
        </button>
        <button class="btn btn-xs btn-ghost" @click="cancelEdit">
          <i class="fa-solid fa-xmark"></i> Cancel
        </button>
        <button class="btn btn-xs btn-success" :disabled="saving || !hasChanges" @click="saveFile">
          <span class="loading loading-spinner loading-xs" v-if="saving"></span>
          <i class="fa-solid fa-floppy-disk" v-else></i> Save
        </button>
      </template>
    </div>

    <!-- File content -->
    <div class="grow overflow-auto">
      <div class="flex items-center justify-center h-32" v-if="loading">
        <span class="loading loading-spinner loading-md"></span>
      </div>
      <Editor
        v-model="editContent"
        :diff="showDiff"
        :originalCode="fileContent"
        :fileName="displayFilePath"
        @save="saveFile"
        class="h-full"
        v-else-if="editMode"
      />
      <div class="flex items-center justify-center h-32 opacity-50 text-sm" v-else-if="isBinary">
        <i class="fa-regular fa-image mr-2"></i> Preview not available for this file type
      </div>
      <VueCodeHighlighter
        class="h-full"
        :code="fileContent"
        :lang="validatedLanguage"
        :title="displayFileName"
        v-else-if="fileContent"
      />
      <div class="flex items-center justify-center h-32 opacity-50 text-sm" v-else>
        Empty file
      </div>
    </div>

    <!-- Delete confirmation modal -->
    <div class="modal" :class="{ 'modal-open': showDeleteModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Delete file?</h3>
        <p class="py-4 text-sm opacity-75">
          Are you sure you want to delete <span class="font-mono font-semibold">{{ displayFileName }}</span>? This action cannot be undone.
        </p>
        <div class="modal-action">
          <button class="btn btn-ghost" @click="cancelDelete">Cancel</button>
          <button class="btn btn-error" :disabled="deleting" @click="confirmDelete">
            <span class="loading loading-spinner loading-xs" v-if="deleting"></span>
            <i class="fa-solid fa-trash" v-else></i> Delete
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="cancelDelete"></div>
    </div>

    <!-- Discard changes confirmation modal -->
    <div class="modal" :class="{ 'modal-open': showDiscardModal }">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Discard changes?</h3>
        <p class="py-4 text-sm opacity-75">
          You have unsaved changes. Are you sure you want to discard them?
        </p>
        <div class="modal-action">
          <button class="btn btn-ghost" @click="cancelDiscard">Keep editing</button>
          <button class="btn btn-warning" @click="confirmDiscard">
            <i class="fa-solid fa-trash"></i> Discard
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="cancelDiscard"></div>
    </div>
  </div>
</template>

<script>
const BINARY_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'ico', 'pdf', 'zip', 'tar', 'gz', 'woff', 'woff2', 'ttf', 'eot']

export default {
  name: 'FileViewer',
  props: ['params'],
  data() {
    return {
      fileContent: '',
      fileMeta: {
        size: null,
        last_modification: null
      },
      editMode: false,
      editContent: '',
      saving: false,
      loading: false,
      error: null,
      isDraggingFileName: false,
      showDiff: false,
      showDeleteModal: false,
      deleting: false,
      showDiscardModal: false
    }
  },
  computed: {
    filePath() {
      return this.params?.filePath ||
              this.$app?.params.filePath || ""
    },
    fileName() {
      return this.filePath.split("/").reverse()[0]
    },
    $api() {
      return this.$project.$api
    },
    displayFilePath() {
      return this.filePath
    },
    displayFileName() {
      if (this.fileName) return this.fileName
      return this.displayFilePath.split('/').pop() || 'File'
    },
    fileExtension() {
      return this.displayFileName.split('.').pop()?.toLowerCase()
    },
    isBinary() {
      return BINARY_EXTENSIONS.includes(this.fileExtension)
    },
    validatedLanguage() {
      const lang = EXTENSION_LANGUAGE_MAP[this.fileExtension] || this.fileExtension
      try {
        if (lang && hljs.getLanguage(lang)) return lang
      } catch (ex) {
        console.warn(`Invalid language detected: ${lang}`, ex)
      }
      return 'markdown'
    },
    // Check if current content differs from original file content
    hasChanges() {
      return this.editContent !== this.fileContent
    }
  },
  mounted() {
    this.loadFile()
  },
  methods: {
    async loadFile() {
      if (!this.displayFilePath) {
        this.error = 'No file path provided'
        return
      }
      this.loading = true
      this.error = null
      try {
        const { content, last_modification, size } = await this.$api.files.read(this.filePath)
        this.fileContent = content
        this.fileMeta = { last_modification, size }
      } catch (ex) {
        console.error('Error reading file', ex)
        this.error = `Error reading "${this.displayFilePath}"`
      } finally {
        this.loading = false
      }
    },
    async reloadFile() {
      await this.loadFile()
      this.$ui.addNotification({ text: `${this.displayFileName} reloaded` })
    },
    startEdit() {
      this.editContent = this.fileContent
      this.editMode = true
      this.showDiff = false
    },
    cancelEdit() {
      this.editMode = false
      this.editContent = ''
      this.showDiff = false
    },
    toggleDiff() {
      this.showDiff = !this.showDiff
    },
    async saveFile() {
      this.saving = true
      try {
        await this.$api.files.write(this.displayFilePath, this.editContent)
        this.fileContent = this.editContent
        this.showDiff = false
        this.$ui.addNotification({ text: `${this.displayFileName} saved` })
        const { last_modification, size } = await this.$api.files.read(this.displayFilePath)
        this.fileMeta = { last_modification, size }
      } catch (ex) {
        console.error('Error saving file', ex)
        this.error = `Error saving "${this.displayFilePath}"`
      } finally {
        this.saving = false
      }
    },
    discardChanges() {
      if (this.hasChanges) {
        this.showDiscardModal = true
      }
    },
    cancelDiscard() {
      this.showDiscardModal = false
    },
    confirmDiscard() {
      this.editContent = this.fileContent
      this.showDiscardModal = false
      this.showDiff = false
      this.$ui.addNotification({ text: 'Changes discarded' })
    },
    copyContent() {
      this.$ui.copyTextToClipboard(this.fileContent)
    },
    formatSize(size) {
      if (size === null || size === undefined) return ''
      return size > 1024 ? `${Math.round(size / 1024)} KB` : `${size} B`
    },
    showDeleteConfirm() {
      this.showDeleteModal = true
    },
    cancelDelete() {
      this.showDeleteModal = false
    },
    async confirmDelete() {
      this.deleting = true
      try {
        await this.$api.files.delete(this.displayFilePath)
        this.$ui.addNotification({ text: `${this.displayFileName} deleted` })
        this.showDeleteModal = false
        this.$emit('file-deleted', this.displayFilePath)
      } catch (ex) {
        console.error('Error deleting file', ex)
        this.$ui.addNotification({ 
          text: `Error deleting "${this.displayFileName}"`,
          type: 'error'
        })
      } finally {
        this.deleting = false
      }
    },
    onDragStart(event) {
      this.isDraggingFileName = true
      event.dataTransfer.setData('text/plain', this.filePath)
      const fileData = JSON.stringify({
        files: [{
          path: this.filePath,
          is_dir: false
        }]
      })
      event.dataTransfer.setData('application/x-file-list-json', fileData)
    },
    onDragEnd() {
      this.isDraggingFileName = false
    }
  }
}
</script>