<script setup>
import ProjectDetailt from '@/components/ProjectDetailt.vue'
</script>

<template>
  <modal close @close="$emit('close')">
    <div class="w-[min(92vw,34rem)] flex flex-col gap-4">

      <!-- ── Header ── -->
      <div class="flex items-center gap-2">
        <span class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
          <i class="fa-solid fa-right-left text-primary text-sm"></i>
        </span>
        <div class="flex flex-col">
          <h2 class="text-base font-semibold text-base-content leading-tight">Board transfer</h2>
          <span class="text-xs text-base-content/40">Export, import, copy or move a board with all its tasks</span>
        </div>
      </div>

      <!-- ── Source board summary (shared by every tab) ── -->
      <div class="flex items-center gap-3 p-3 rounded-lg bg-base-200 border border-base-100">
        <i class="text-sm shrink-0" :class="boardIcon"></i>
        <div class="min-w-0">
          <div class="text-sm font-medium truncate" :title="boardTitle">{{ boardTitle }}</div>
          <div class="text-xs text-base-content/40">{{ boardSubtitle }}</div>
        </div>
      </div>

      <!-- ── Tabs ── -->
      <div role="tablist" class="tabs tabs-boxed tabs-sm bg-base-200">
        <button
          v-for="t in tabs"
          :key="t.id"
          role="tab"
          type="button"
          class="tab gap-1.5"
          :class="tab === t.id ? 'tab-active' : ''"
          :aria-selected="tab === t.id"
          @click="selectTab(t.id)"
        >
          <i :class="t.icon" class="text-xs"></i>
          {{ t.label }}
        </button>
      </div>

      <!-- ══ Export ══ -->
      <div v-if="tab === 'export'" class="flex flex-col gap-3">
        <p class="text-xs text-base-content/60 leading-relaxed">
          Download the board — its columns, tasks and every message — as a
          portable JSON file, or copy it straight to the clipboard. Import it
          later into any project and the tasks will be adapted automatically.
        </p>

        <!-- Error -->
        <div v-if="exportError" class="text-xs text-error flex items-start gap-1.5">
          <i class="fa-solid fa-triangle-exclamation mt-0.5 shrink-0"></i>
          <span>{{ exportError }}</span>
        </div>

        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-ghost btn-sm" @click="$emit('close')">Cancel</button>
          <button
            type="button"
            class="btn btn-outline btn-primary btn-sm gap-1.5"
            :disabled="!canExportBoard || exporting || copying"
            @click="copyToClipboard"
          >
            <span v-if="copying" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-regular fa-clipboard text-xs"></i>
            Copy to clipboard
          </button>
          <button
            type="button"
            class="btn btn-primary btn-sm gap-1.5"
            :disabled="!canExportBoard || exporting || copying"
            @click="startExport"
          >
            <span v-if="exporting" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-download text-xs"></i>
            Download
          </button>
        </div>
      </div>

      <!-- ══ Import ══ -->
      <div v-else-if="tab === 'import'" class="flex flex-col gap-3">
        <p class="text-xs text-base-content/60 leading-relaxed">
          Pick a board file (or paste an exported board) and the project to
          import it into. Task projects, links and file references are rewritten
          for the destination project.
        </p>

        <!-- File picker -->
        <div class="form-control w-full">
          <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-1">
            Board file (.json)
          </span>
          <div class="flex items-center gap-2">
            <input
              type="file"
              accept="application/json,.json"
              class="file-input file-input-bordered file-input-sm flex-1"
              @change="onFileSelected"
            />
            <button
              type="button"
              class="btn btn-ghost btn-sm gap-1.5 text-base-content/60 shrink-0"
              title="Paste an exported board from the clipboard"
              @click="pasteFromClipboard"
            >
              <i class="fa-regular fa-clipboard text-xs"></i>
              <span class="hidden sm:inline text-xs">Paste</span>
            </button>
          </div>
        </div>

        <!-- Preview -->
        <div
          v-if="importDoc"
          class="p-3 rounded-lg bg-base-200 border border-base-100 flex flex-col gap-1"
        >
          <div class="flex items-center gap-2">
            <i
              class="text-sm shrink-0"
              :class="importDoc.board?.type === 'sprint'
                ? 'fa-solid fa-layer-group text-primary'
                : 'fa-brands fa-trello text-primary'"
            ></i>
            <span class="text-sm font-medium truncate" :title="importDoc.board?.title">
              {{ importDoc.board?.title }}
            </span>
            <span class="badge badge-xs badge-ghost shrink-0">
              {{ importDoc.board?.type === 'sprint' ? 'sprint' : 'kanban' }}
            </span>
          </div>
          <div class="text-xs text-base-content/50">
            {{ importChatCount }} task{{ importChatCount === 1 ? '' : 's' }}
            <span v-if="importDoc.source?.project_name"> · exported from {{ importDoc.source.project_name }}</span>
          </div>
        </div>

        <!-- Error -->
        <div v-if="importError" class="text-xs text-error flex items-start gap-1.5">
          <i class="fa-solid fa-triangle-exclamation mt-0.5 shrink-0"></i>
          <span>{{ importError }}</span>
        </div>

        <!-- Target project -->
        <div class="form-control w-full">
          <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-1">
            Import into project
          </span>
          <ProjectDetailt
            :model-value="targetProject"
            @update:model-value="onTargetProject"
            @select="onTargetProject"
          />
        </div>

        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-ghost btn-sm" @click="$emit('close')">Cancel</button>
          <button
            type="button"
            class="btn btn-primary btn-sm gap-1.5"
            :disabled="!importDoc || !targetProject || importing"
            @click="startImport"
          >
            <span v-if="importing" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-file-import text-xs"></i>
            Import
          </button>
        </div>
      </div>

      <!-- ══ Copy / Move ══ -->
      <div v-else class="flex flex-col gap-3">
        <p class="text-xs text-base-content/60 leading-relaxed">
          Copy this board — with its tasks and every message — into another
          project. <b>Move</b> additionally removes it from
          <b>{{ activeProject?.project_name }}</b>. Everything project-bound
          (projects, links, file references) is rewritten for the destination.
        </p>

        <!-- Destination project -->
        <div class="form-control w-full">
          <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50 mb-1">
            Destination project
          </span>
          <ProjectDetailt
            :model-value="transferProject"
            @update:model-value="onTransferProject"
            @select="onTransferProject"
          />
        </div>

        <!-- Same-project hint -->
        <div v-if="isSameProject" class="text-xs text-warning flex items-start gap-1.5">
          <i class="fa-solid fa-circle-info mt-0.5 shrink-0"></i>
          <span>Pick a project other than <b>{{ activeProject?.project_name }}</b>.</span>
        </div>

        <!-- Move confirmation hint -->
        <div v-if="moveArmed" class="text-xs text-warning flex items-start gap-1.5">
          <i class="fa-solid fa-arrow-right-from-bracket mt-0.5 shrink-0"></i>
          <span>The board will be removed from <b>{{ activeProject?.project_name }}</b> once it has been copied.</span>
        </div>

        <!-- Error -->
        <div v-if="transferError" class="text-xs text-error flex items-start gap-1.5">
          <i class="fa-solid fa-triangle-exclamation mt-0.5 shrink-0"></i>
          <span>{{ transferError }}</span>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-2">
          <template v-if="!moveArmed">
            <button type="button" class="btn btn-ghost btn-sm" @click="$emit('close')">Cancel</button>
            <button
              type="button"
              class="btn btn-outline btn-primary btn-sm gap-1.5"
              :disabled="!canTransfer || copying || transferring"
              @click="startCopy"
            >
              <span v-if="copying" class="loading loading-spinner loading-xs"></span>
              <i v-else class="fa-regular fa-copy text-xs"></i>
              Copy
            </button>
            <button
              type="button"
              class="btn btn-warning btn-sm gap-1.5"
              :disabled="!canTransfer || copying || transferring"
              @click="moveArmed = true"
            >
              <i class="fa-solid fa-truck-fast text-xs"></i>
              Move
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn btn-ghost btn-sm" @click="moveArmed = false">Back</button>
            <button
              type="button"
              class="btn btn-warning btn-sm gap-1.5"
              :disabled="transferring"
              @click="startMove"
            >
              <span v-if="transferring" class="loading loading-spinner loading-xs"></span>
              <i v-else class="fa-solid fa-check text-xs"></i>
              Confirm move
            </button>
          </template>
        </div>
      </div>
    </div>
  </modal>
</template>

<script>
export default {
  name: 'BoardTransferModal',
  props: {
    // Board to export (kanban or sprint). Null disables the export tab actions.
    boardId: { type: String, default: null },
    // Default import target project (falls back to the active project).
    project: { type: Object, default: null }
  },
  emits: ['close', 'imported'],
  data() {
    return {
      tab: 'export',
      tabs: [
        { id: 'export', label: 'Export', icon: 'fa-solid fa-file-export' },
        { id: 'import', label: 'Import', icon: 'fa-solid fa-file-import' },
        { id: 'transfer', label: 'Copy / Move', icon: 'fa-solid fa-right-left' }
      ],
      // Export tab
      exporting: false,
      copying: false,
      exportError: null,
      // Copy / Move tab
      transferring: false,
      transferError: null,
      // Explicit confirmation before the (source-destroying) move
      moveArmed: false,
      // Import tab
      importing: false,
      importDoc: null,
      importError: null,
      // Initialized from the prop only. `this.$storex` is a COMPUTED property
      // (declared in the global mixin) and is NOT available while `data()` runs,
      // so the active-project fallback is resolved in `created` instead.
      targetProject: this.project || null,
      transferProject: null
    }
  },
  created() {
    // Resolve the default import target once computed properties are set up.
    // Accessing `this.$storex` in `data()` would throw (undefined) and prevent
    // the modal from ever mounting — making the Transfer button look dead.
    const activeProject = this.$storex.projects.activeProject || null
    if (!this.targetProject) {
      this.targetProject = activeProject
    }
    // Default the copy/move destination to another project when one exists, so
    // the action is immediately usable (the source project is never a target).
    const projects = this.$storex.projects.allProjects || []
    this.transferProject = projects.find(p => p.project_id !== activeProject?.project_id) ||
      this.project ||
      activeProject
  },
  computed: {
    board() {
      return this.boardId ? this.$storex.kanban.boardById(this.boardId) : null
    },
    activeProject() {
      return this.$storex.projects.activeProject
    },
    // The synthetic "No board" catch-all cannot be exported or moved
    isVirtual() {
      return !!this.board?.virtual
    },
    canExportBoard() {
      return !!this.board && !this.isVirtual
    },
    exportTaskCount() {
      if (!this.board) return 0
      return this.board.type === 'sprint'
        ? this.$storex.kanban.sprintBoardChats(this.board.id).length
        : $storex.kanban.boardChats(this.board.id).length
    },
    boardIcon() {
      if (this.isVirtual) return 'fa-solid fa-ban text-base-content/30'
      if (!this.board) return 'fa-solid fa-ban text-base-content/30'
      return this.board.type === 'sprint'
        ? 'fa-solid fa-layer-group text-primary'
        : 'fa-brands fa-trello text-primary'
    },
    boardTitle() {
      return this.board?.title || 'No board selected'
    },
    boardSubtitle() {
      if (this.isVirtual) return 'This virtual board cannot be transferred'
      if (!this.board) return 'Select a board to transfer'
      const type = this.board.type === 'sprint' ? 'sprint' : 'kanban'
      return `${this.exportTaskCount} task${this.exportTaskCount === 1 ? '' : 's'} · ${type}`
    },
    importChatCount() {
      return this.importDoc?.chats?.length || 0
    },
    // Copying/moving INTO the source project is not a transfer — block it.
    isSameProject() {
      const activeId = this.activeProject?.project_id
      return !!activeId && this.transferProject?.project_id === activeId
    },
    canTransfer() {
      return this.canExportBoard && !!this.transferProject && !this.isSameProject
    }
  },
  watch: {
    tab() {
      this.moveArmed = false
    },
    transferProject() {
      this.moveArmed = false
    }
  },
  methods: {
    selectTab(id) {
      this.tab = id
    },

    // ── Export ──────────────────────────────────────────────────────────────
    // Build the portable document once so download & clipboard stay in sync.
    async buildExportDocument() {
      if (!this.canExportBoard) return null
      const doc = await this.$storex.kanban.exportBoard({ boardId: this.boardId })
      if (!doc) {
        this.exportError = 'Nothing to export'
        return null
      }
      return doc
    },
    async startExport() {
      if (!this.canExportBoard || this.exporting || this.copying) return
      this.exporting = true
      this.exportError = null
      try {
        const doc = await this.buildExportDocument()
        if (!doc) return
        this.download(doc)
        this.$ui?.addNotification?.({ text: `Board "${doc.board.title}" exported` })
        this.$emit('close')
      } catch (error) {
        console.error('[BoardTransferModal] Export failed:', error)
        this.exportError = 'Failed to export the board'
      } finally {
        this.exporting = false
      }
    },
    async copyToClipboard() {
      if (!this.canExportBoard || this.exporting || this.copying) return
      this.copying = true
      this.exportError = null
      try {
        const doc = await this.buildExportDocument()
        if (!doc) return
        // Uses the shared helper so the copied text is reported consistently
        // ("Text copied") across the app.
        this.$storex.ui.copyTextToClipboard(JSON.stringify(doc))
        this.$emit('close')
      } catch (error) {
        console.error('[BoardTransferModal] Copy to clipboard failed:', error)
        this.exportError = 'Failed to copy the board to the clipboard'
      } finally {
        this.copying = false
      }
    },
    download(doc) {
      const blob = new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      a.download = `${this.slug(doc.board?.title || 'board')}-${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    },
    slug(text) {
      return (text || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 60) || 'board'
    },

    // ── Import ──────────────────────────────────────────────────────────────
    async onFileSelected(event) {
      this.importError = null
      this.importDoc = null
      const file = event.target.files?.[0]
      if (!file) return
      try {
        const text = await file.text()
        this.loadImportDocument(text)
      } catch (error) {
        console.error('[BoardTransferModal] Invalid board file:', error)
        this.importError = 'Could not read the selected file'
      }
    },
    // Read a board export pasted from the clipboard (mirrors "Copy to clipboard").
    async pasteFromClipboard() {
      this.importError = null
      try {
        const text = await navigator.clipboard.readText()
        this.loadImportDocument(text)
      } catch (error) {
        console.error('[BoardTransferModal] Clipboard read failed:', error)
        this.importError = 'Could not read the clipboard'
      }
    },
    loadImportDocument(text) {
      if (!text) {
        this.importError = 'The clipboard is empty'
        return
      }
      try {
        const doc = JSON.parse(text)
        if (!doc || doc.format !== 'codx-junior-board' || !doc.board) {
          this.importError = 'This is not a codx-junior board export'
          return
        }
        this.importDoc = doc
      } catch (error) {
        console.error('[BoardTransferModal] Invalid board data:', error)
        this.importError = 'Could not read the board data'
      }
    },
    onTargetProject(project) {
      if (project?.project_id) this.targetProject = project
    },
    async startImport() {
      if (!this.importDoc || !this.targetProject || this.importing) return
      this.importing = true
      this.importError = null
      try {
        const result = await this.$storex.kanban.importBoard({
          document: this.importDoc,
          project: this.targetProject
        })
        this.$ui?.addNotification?.({
          text: `Board "${result.boardId}" imported (${this.taskCountLabel(result.importedCount)})`
        })
        this.$emit('imported', result)
        this.$emit('close')
      } catch (error) {
        console.error('[BoardTransferModal] Import failed:', error)
        this.importError = error.message || 'Failed to import board'
      } finally {
        this.importing = false
      }
    },

    // ── Copy / Move to another project ──────────────────────────────────────
    onTransferProject(project) {
      if (project?.project_id) this.transferProject = project
    },
    async startCopy() {
      if (!this.canTransfer || this.copying || this.transferring) return
      this.copying = true
      this.transferError = null
      try {
        const result = await this.$storex.kanban.copyBoardToProject({
          boardId: this.boardId,
          project: this.transferProject
        })
        this.notifyTransfer('copied', result)
        this.$emit('imported', result)
        this.$emit('close')
      } catch (error) {
        console.error('[BoardTransferModal] Copy failed:', error)
        this.transferError = error.message || 'Failed to copy the board'
      } finally {
        this.copying = false
      }
    },
    async startMove() {
      if (!this.canTransfer || this.copying || this.transferring) return
      this.transferring = true
      this.transferError = null
      try {
        const result = await this.$storex.kanban.moveBoardToProject({
          boardId: this.boardId,
          project: this.transferProject
        })
        this.notifyTransfer('moved', result)
        this.$emit('imported', result)
        this.$emit('close')
      } catch (error) {
        console.error('[BoardTransferModal] Move failed:', error)
        this.transferError = error.message || 'Failed to move the board'
      } finally {
        this.transferring = false
      }
    },
    notifyTransfer(verb, result) {
      this.$ui?.addNotification?.({
        text: `Board "${result.boardId}" ${verb} to ${this.transferProject?.project_name} ` +
          `(${this.taskCountLabel(result.importedCount)})`
      })
    },
    taskCountLabel(count) {
      return `${count || 0} task${count === 1 ? '' : 's'}`
    }
  }
}
</script>