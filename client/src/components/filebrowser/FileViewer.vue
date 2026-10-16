<script setup>
import moment from 'moment'
import hljs from 'highlight.js'
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import Editor from '../monaco/Editor.vue'
import MarkdownViewer from '../MarkdownViewer.vue'
import CanvaEditor from '../canva/CanvaEditor.vue'
import { EXTENSION_LANGUAGE_MAP } from '@/store'
</script>

<template>
  <div class="w-full h-full flex flex-col overflow-hidden">
    <!-- File header -->
    <div class="flex items-center gap-3 px-3 py-2 bg-base-200 border-b border-base-100 flex-shrink-0">
      <i :class="getHeaderIcon()"></i>
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
      <span class="loading loading-spinner loading-xs" title="Saving canvas" v-if="isCanva && saving"></span>
      
      <!-- Unsaved changes indicator -->
      <div class="flex items-center gap-2" v-if="(editMode || isContentMode || isCanvaEditorMode) && hasChanges">
        <div class="flex items-center gap-1 px-2 py-1 bg-warning rounded text-warning-content text-xs">
          <i class="fa-solid fa-circle-exclamation"></i>
          <span>Unsaved changes</span>
        </div>
      </div>

      <div class="grow"></div>

      <!-- Editor / content switcher (files with a dedicated editor, e.g. canva) -->
      <div class="join" v-if="hasAssociatedEditor && !editMode && !loading">
        <button
          class="btn btn-xs join-item"
          :class="viewMode === 'editor' ? 'btn-primary' : 'btn-ghost'"
          title="Show editor"
          @click="setViewMode('editor')"
        >
          <i class="fa-solid fa-palette mr-1"></i> Editor
        </button>
        <button
          class="btn btn-xs join-item"
          :class="viewMode === 'content' ? 'btn-primary' : 'btn-ghost'"
          title="Show raw content"
          @click="setViewMode('content')"
        >
          <i class="fa-solid fa-code mr-1"></i> Content
        </button>
      </div>

      <button class="btn btn-xs btn-ghost" title="Reload file" @click="reloadFile" v-if="!editMode && !loading">
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>
      <a
        class="btn btn-xs btn-ghost"
        title="Download file"
        :href="downloadUrl"
        :download="displayFileName"
        v-if="!editMode && !loading && filePath"
      >
        <i class="fa-solid fa-download"></i>
      </a>
      <button class="btn btn-xs btn-ghost" title="Copy content" @click="copyContent" v-if="!editMode && !isPdf && !isImage && !isVideo && !isMarkdown">
        <i class="fa-solid fa-copy"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Delete file" @click="showDeleteConfirm" v-if="!editMode">
        <i class="fa-solid fa-trash"></i>
      </button>
      <button class="btn btn-xs btn-outline" @click="startEdit" v-if="!editMode && !isBinary && !isCanva">
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
      <template v-if="isContentMode">
        <button 
          class="btn btn-xs btn-ghost" 
          :disabled="!hasChanges"
          @click="discardChanges"
          title="Discard unsaved changes"
        >
          <i class="fa-solid fa-times"></i> Discard
        </button>
        <button class="btn btn-xs btn-success" :disabled="saving || !hasChanges" @click="saveFile">
          <span class="loading loading-spinner loading-xs" v-if="saving"></span>
          <i class="fa-solid fa-floppy-disk" v-else></i> Save
        </button>
      </template>
      <!-- Canvas editor: changes stay in memory until the user saves them -->
      <template v-if="isCanvaEditorMode">
        <button
          class="btn btn-xs btn-ghost"
          :disabled="!hasChanges"
          @click="discardChanges"
          title="Discard unsaved changes"
        >
          <i class="fa-solid fa-times"></i> Discard
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
      <div class="w-full h-full flex items-center justify-center bg-base-300" v-else-if="isPdf">
        <iframe
          :src="pdfPreviewUrl"
          class="w-full h-full"
          title="PDF Viewer"
        ></iframe>
      </div>
      <div class="w-full h-full flex items-center justify-center bg-base-300 p-4" v-else-if="isImage">
        <img
          :src="imageDataUrl"
          :alt="displayFileName"
          class="max-w-full max-h-full object-contain"
        />
      </div>
      <div class="w-full h-full flex items-center justify-center bg-base-300" v-else-if="isVideo">
        <video
          :src="videoPreviewUrl"
          controls
          class="max-w-full max-h-full"
          :title="displayFileName"
        ></video>
      </div>
      <MarkdownViewer
        v-else-if="isMarkdown"
        class="p-2"
        :text="fileContent"
        :document-id="displayFilePath"
        @add-file="handleAddFile"
        @table-updated="handleTableUpdated"
      />
      <template v-else-if="isCanva">
        <!-- Visual editor -->
        <CanvaEditor
          v-if="viewMode === 'editor'"
          class="h-full"
          :modelValue="canvaDefinition"
          @update:modelValue="onCanvaUpdate"
        />
        <!-- Raw editor content (JSON) -->
        <Editor
          v-else
          v-model="editContent"
          language="json"
          :fileName="displayFilePath"
          @save="saveFile"
          class="h-full"
        />
      </template>
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
const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'ico', 'svg']
const VIDEO_EXTENSIONS = ['mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm', 'ogv', 'ts', 'mts', 'vob']
const MARKDOWN_EXTENSIONS = ['md', 'markdown', 'mermaid']
const BINARY_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'ico', 'zip', 'tar', 'gz', 'woff', 'woff2', 'ttf', 'eot']

const EXTENSION_ICON_MAP = {
  // Code files
  'js': 'fa-brands fa-js text-yellow-500',
  'ts': 'fa-brands fa-js text-blue-500',
  'jsx': 'fa-brands fa-react text-blue-400',
  'tsx': 'fa-brands fa-react text-blue-400',
  'vue': 'fa-brands fa-vuejs text-green-500',
  'py': 'fa-brands fa-python text-blue-600',
  'java': 'fa-brands fa-java text-red-600',
  'cpp': 'fa-regular fa-file-code text-blue-600',
  'c': 'fa-regular fa-file-code text-blue-600',
  'cs': 'fa-brands fa-microsoft text-purple-600',
  'rb': 'fa-brands fa-gem text-red-700',
  'php': 'fa-brands fa-php text-indigo-600',
  'go': 'fa-regular fa-file-code text-cyan-500',
  'rs': 'fa-regular fa-file-code text-orange-600',
  'swift': 'fa-brands fa-swift text-orange-500',
  'kt': 'fa-regular fa-file-code text-purple-600',
  // Markup & Style
  'html': 'fa-brands fa-html5 text-orange-600',
  'css': 'fa-brands fa-css3-alt text-blue-500',
  'scss': 'fa-brands fa-sass text-pink-600',
  'sass': 'fa-brands fa-sass text-pink-600',
  'less': 'fa-regular fa-file-code text-blue-400',
  'xml': 'fa-regular fa-file-code text-orange-600',
  'json': 'fa-regular fa-file-code text-yellow-600',
  'yaml': 'fa-regular fa-file-code text-red-600',
  'yml': 'fa-regular fa-file-code text-red-600',
  'toml': 'fa-regular fa-file-code text-orange-700',
  'svg': 'fa-regular fa-file-image text-orange-400',
  // Templates
  'ejs': 'fa-regular fa-file-code text-yellow-600',
  'hbs': 'fa-regular fa-file-code text-orange-700',
  'pug': 'fa-regular fa-file-code text-brown-600',
  // Databases
  'sql': 'fa-solid fa-database text-blue-600',
  'db': 'fa-solid fa-database text-slate-600',
  'sqlite': 'fa-solid fa-database text-blue-400',
  // Documents
  'md': 'fa-brands fa-markdown text-slate-600',
  'txt': 'fa-regular fa-file-lines text-slate-500',
  'pdf': 'fa-solid fa-file-pdf text-red-600',
  'doc': 'fa-solid fa-file-word text-blue-600',
  'docx': 'fa-solid fa-file-word text-blue-600',
  'xls': 'fa-solid fa-file-excel text-green-600',
  'xlsx': 'fa-solid fa-file-excel text-green-600',
  'ppt': 'fa-solid fa-file-powerpoint text-orange-600',
  'pptx': 'fa-solid fa-file-powerpoint text-orange-600',
  // Media
  'png': 'fa-regular fa-file-image text-pink-500',
  'jpg': 'fa-regular fa-file-image text-pink-500',
  'jpeg': 'fa-regular fa-file-image text-pink-500',
  'gif': 'fa-regular fa-file-image text-pink-500',
  'webp': 'fa-regular fa-file-image text-pink-500',
  'ico': 'fa-regular fa-file-image text-slate-500',
  'svg': 'fa-regular fa-file-image text-orange-400',
  'mp4': 'fa-regular fa-file-video text-red-500',
  'avi': 'fa-regular fa-file-video text-red-500',
  'mov': 'fa-regular fa-file-video text-red-500',
  'mkv': 'fa-regular fa-file-video text-red-500',
  'flv': 'fa-regular fa-file-video text-red-500',
  'wmv': 'fa-regular fa-file-video text-red-500',
  'webm': 'fa-regular fa-file-video text-red-500',
  'ogv': 'fa-regular fa-file-video text-red-500',
  'ts': 'fa-regular fa-file-video text-red-500',
  'mts': 'fa-regular fa-file-video text-red-500',
  'vob': 'fa-regular fa-file-video text-red-500',
  'mp3': 'fa-regular fa-file-audio text-purple-500',
  'wav': 'fa-regular fa-file-audio text-purple-500',
  'flac': 'fa-regular fa-file-audio text-purple-500',
  'aac': 'fa-regular fa-file-audio text-purple-500',
  'wma': 'fa-regular fa-file-audio text-purple-500',
  'ogg': 'fa-regular fa-file-audio text-purple-500',
  // Archives
  'zip': 'fa-regular fa-file-zipper text-slate-600',
  'rar': 'fa-regular fa-file-zipper text-slate-600',
  'tar': 'fa-regular fa-file-zipper text-slate-600',
  'gz': 'fa-regular fa-file-zipper text-slate-600',
  '7z': 'fa-regular fa-file-zipper text-slate-600',
  'bz2': 'fa-regular fa-file-zipper text-slate-600',
  // Config
  'env': 'fa-solid fa-gear text-slate-500',
  'config': 'fa-solid fa-gear text-slate-500',
  'conf': 'fa-solid fa-gear text-slate-500',
  'ini': 'fa-solid fa-gear text-slate-500',
  // Shell
  'sh': 'fa-solid fa-terminal text-slate-700',
  'bash': 'fa-solid fa-terminal text-slate-700',
  'zsh': 'fa-solid fa-terminal text-slate-700',
  'fish': 'fa-solid fa-terminal text-slate-700',
  'bat': 'fa-solid fa-terminal text-slate-700',
  // Version Control
  'git': 'fa-brands fa-git-alt text-orange-600',
  'gitignore': 'fa-brands fa-git-alt text-orange-600',
  // Canvas
  'canva': 'fa-solid fa-palette text-primary',
  // Other
  'lock': 'fa-solid fa-lock text-amber-600',
  'key': 'fa-solid fa-key text-yellow-600'
}

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
      showDiscardModal: false,
      // Local snapshot of the canvas definition consumed by <CanvaEditor>.
      // Kept as data (not derived from fileContent) so persisting edits never
      // re-triggers the editor's modelValue watcher and wipes the canvas.
      canvaDefinition: [],
      // Active view for files with a dedicated editor: 'editor' | 'content'
      viewMode: 'editor'
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
    isPdf() {
      return this.fileExtension === 'pdf'
    },
    isImage() {
      return IMAGE_EXTENSIONS.includes(this.fileExtension)
    },
    isVideo() {
      return VIDEO_EXTENSIONS.includes(this.fileExtension)
    },
    isMarkdown() {
      return MARKDOWN_EXTENSIONS.includes(this.fileExtension)
    },
    isCanva() {
      return this.fileExtension === 'canva'
    },
    // Files that expose a dedicated visual editor + a raw content editor.
    // Extend this list when new editor types are added.
    hasAssociatedEditor() {
      return this.isCanva
    },
    // True when the raw editor content is currently displayed
    isContentMode() {
      return this.hasAssociatedEditor && this.viewMode === 'content'
    },
    // True when the dedicated visual editor is currently displayed
    isCanvaEditorMode() {
      return this.isCanva && this.viewMode === 'editor'
    },
    isBinary() {
      return BINARY_EXTENSIONS.includes(this.fileExtension) || this.isVideo
    },
    pdfPreviewUrl() {
      if (!this.isPdf) return ''
      return this.$api.files.getFilePreviewUrl(this.filePath)
    },
    imageDataUrl() {
      if (!this.fileContent || !this.isImage) return ''
      const mimeType = this.getMimeType(this.fileExtension)
      return `data:${mimeType};base64,${this.fileContent}`
    },
    videoPreviewUrl() {
      if (!this.isVideo) return ''
      return this.$api.files.getFilePreviewUrl(this.filePath)
    },
    downloadUrl() {
      if (!this.filePath) return ''
      return this.$api.files.getFileDownloadUrl(this.filePath)
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
    hasChanges() {
      return this.editContent !== this.fileContent
    }
  },
  mounted() {
    this.loadFile()
  },
  methods: {
    getMimeType(extension) {
      const mimeTypes = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'ico': 'image/x-icon',
        'svg': 'image/svg+xml',
        'mp4': 'video/mp4',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'mkv': 'video/x-matroska',
        'flv': 'video/x-flv',
        'wmv': 'video/x-ms-wmv',
        'webm': 'video/webm',
        'ogv': 'video/ogg',
        'ts': 'video/mp2t',
        'mts': 'video/mp2t',
        'vob': 'video/x-ms-vob'
      }
      return mimeTypes[extension] || 'application/octet-stream'
    },
    getHeaderIcon() {
      const ext = this.fileExtension
      return EXTENSION_ICON_MAP[ext] || 'fa-regular fa-file text-info'
    },
    // Parse raw editor content into a node array. Supports both a root array
    // and a { nodes: [...] } envelope. Returns null when the JSON is invalid.
    parseCanvaDefinition(content) {
      try {
        const parsed = JSON.parse(content)
        return Array.isArray(parsed) ? parsed : (parsed.nodes || [])
      } catch (ex) {
        console.warn('Invalid canva definition', ex)
        return null
      }
    },
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
        // Rebuild the visual canvas snapshot whenever the file is (re)loaded.
        // The staged JSON is synced too, so change detection starts clean.
        if (this.isCanva) {
          this.canvaDefinition = this.parseCanvaDefinition(content) || []
          this.editContent = content
        }
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
    // Toggle between the dedicated editor and its raw content representation
    setViewMode(mode) {
      if (mode === this.viewMode) return
      // Seed the raw editor with the current content the first time we show it
      if (mode === 'content' && !this.editContent) {
        this.editContent = this.fileContent
      }
      // Going back to the canvas replays the staged definition, so edits made
      // in the raw editor (or by the canvas itself) are never lost
      if (mode === 'editor' && this.isCanva) {
        const definition = this.parseCanvaDefinition(this.editContent)
        if (definition) {
          this.canvaDefinition = definition
        }
      }
      this.viewMode = mode
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
        // Raw content edits must be pushed back to the visual editor. Canvas
        // edits are already the source of truth and must not be reloaded here.
        if (this.isCanva && this.isContentMode) {
          const definition = this.parseCanvaDefinition(this.editContent)
          if (definition) {
            this.canvaDefinition = definition
          }
        }
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
    // Canvas edits are only staged in memory: they are written to disk when the
    // user presses Save and dropped when the user discards them.
    onCanvaUpdate(nodes) {
      this.editContent = JSON.stringify({ nodes }, null, 2)
    },
    discardChanges() {
      if (this.hasChanges) {
        this.showDiscardModal = true
      }
    },
    cancelDiscard() {
      this.showDiscardModal = false
    },
    async confirmDiscard() {
      this.showDiscardModal = false
      this.showDiff = false
      if (this.isCanva) {
        // Restore the editor state from the file on disk
        await this.loadFile()
      } else {
        this.editContent = this.fileContent
      }
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
    },
    handleAddFile(filePath) {
      this.$emit('add-file', filePath)
    },
    handleTableUpdated(payload) {
      this.$emit('table-updated', payload)
    }
  }
}
</script>