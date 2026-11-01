<script setup>
import { defineAsyncComponent } from 'vue'
import moment from 'moment'
import { VueCodeHighlighter } from 'vue-code-highlighter'
import 'vue-code-highlighter/dist/style.css'
import hljs from '@/utils/highlight'
import { EXTENSION_LANGUAGE_MAP } from '@/store'

// Monaco + @git-diff-view are heavy: keep them out of the chunk that renders
// every chat message (same reason CodeViewer loads it lazily).
const DiffViewer = defineAsyncComponent(() => import('../DiffViewer.vue'))
</script>

<template>
  <div class="flex flex-col gap-2 rounded-lg border border-base-content/10 bg-base-200/60 p-2">
    <!-- ── Summary bar ──
         Files mode is a review surface: the counters answer "what am I about to
         write?" before any single file is read. -->
    <div v-if="files.length" class="flex flex-wrap items-center gap-2 px-1">
      <i class="fa-solid fa-folder-tree text-primary text-xs"></i>
      <span class="text-xs font-semibold text-base-content/70 tabular-nums">
        {{ files.length }} file{{ files.length > 1 ? 's' : '' }}
      </span>
      <span v-if="newCount" class="badge badge-xs badge-success gap-1">
        <i class="fa-solid fa-plus text-[8px]"></i>{{ newCount }} new
      </span>
      <span v-if="modifiedCount" class="badge badge-xs badge-warning gap-1">
        <i class="fa-solid fa-pen text-[8px]"></i>{{ modifiedCount }} changed
      </span>
      <span v-if="deletedCount" class="badge badge-xs badge-error gap-1">
        <i class="fa-solid fa-minus text-[8px]"></i>{{ deletedCount }} deleted
      </span>
      <div class="grow"></div>
      <button
        class="btn btn-xs btn-ghost tooltip tooltip-bottom"
        :data-tip="allExpanded ? 'Collapse all' : 'Expand all'"
        :aria-label="allExpanded ? 'Collapse all files' : 'Expand all files'"
        @click="toggleAllExpanded"
      >
        <i class="fa-solid text-[11px]" :class="allExpanded ? 'fa-compress' : 'fa-expand'"></i>
      </button>
    </div>

    <!-- ── File cards ──
         A NEW file shows its content (there is nothing to compare against), an
         existing one shows the diff against what is on disk. -->
    <div
      v-for="entry in files"
      :key="entry.key"
      class="overflow-hidden rounded-box border bg-base-100"
      :class="cardClass(entry)"
    >
      <!-- Header -->
      <div
        class="flex flex-wrap items-center gap-2 px-2 py-1.5 cursor-pointer select-none"
        @click="toggleExpanded(entry)"
      >
        <input
          v-if="isSelectable(entry)"
          type="checkbox"
          class="checkbox checkbox-xs checkbox-primary shrink-0"
          :checked="isSelected(entry)"
          :aria-label="`Select ${entry.name}`"
          @click.stop
          @change="$emit('toggle-select', entry.key)"
        />

        <i :class="statusIcon(entry)" class="text-xs shrink-0"></i>

        <span class="font-mono text-xs font-semibold truncate shrink-0 max-w-[45%] @lg/panel:max-w-none" :title="entry.path">
          {{ entry.name }}
        </span>
        <span class="hidden @lg/panel:inline text-[11px] text-base-content/40 truncate">{{ entry.path }}</span>

        <span v-if="statusLabel(entry)" class="badge badge-xs shrink-0" :class="statusBadge(entry)">
          {{ statusLabel(entry) }}
        </span>

        <span v-if="entry.stats" class="flex items-center gap-1 shrink-0">
          <span class="text-[11px] text-success tabular-nums">+{{ entry.stats.insertions }}</span>
          <span class="text-[11px] text-error tabular-nums">-{{ entry.stats.deletions }}</span>
        </span>

        <span v-if="entry.lastModification" class="hidden @lg/panel:inline text-[11px] text-base-content/30 shrink-0">
          {{ moment(entry.lastModification).fromNow() }}
        </span>

        <div class="grow"></div>

        <!-- Actions -->
        <button
          v-if="canToggleView(entry)"
          class="btn btn-xs btn-ghost tooltip tooltip-bottom shrink-0"
          :class="entry.view === 'diff' ? 'text-warning' : ''"
          :data-tip="entry.view === 'diff' ? 'Show full content' : 'Show changes'"
          :aria-label="entry.view === 'diff' ? 'Show full content' : 'Show changes'"
          @click.stop="toggleView(entry)"
        >
          <i :class="entry.view === 'diff' ? 'fa-solid fa-file-lines' : 'fa-solid fa-code-compare'"></i>
        </button>
        <button
          class="btn btn-xs btn-ghost tooltip tooltip-bottom shrink-0"
          data-tip="Copy content"
          aria-label="Copy content"
          @click.stop="copyContent(entry)"
        >
          <i class="fa-solid fa-copy"></i>
        </button>
        <button
          class="btn btn-xs btn-ghost tooltip tooltip-bottom shrink-0"
          data-tip="Add to chat"
          aria-label="Add to chat"
          @click.stop="$emit('add-file', entry.path)"
        >
          <i class="fa-solid fa-file-circle-plus"></i>
        </button>
        <button
          class="btn btn-xs btn-ghost tooltip tooltip-bottom shrink-0"
          data-tip="Create sub-task"
          aria-label="Create sub-task"
          @click.stop="createSubTask(entry)"
        >
          <i class="fa-brands fa-trello"></i>
        </button>
        <button
          class="btn btn-xs btn-success btn-outline gap-1 shrink-0"
          title="Save to project"
          @click.stop="saveFile(entry)"
        >
          <i class="fa-solid fa-floppy-disk"></i>
          <span class="hidden @lg/panel:inline">Save</span>
        </button>

        <button
          class="btn btn-xs btn-ghost shrink-0"
          :aria-expanded="entry.expanded"
          :aria-label="entry.expanded ? 'Collapse file' : 'Expand file'"
          @click.stop="toggleExpanded(entry)"
        >
          <i
            class="fa-solid text-[10px] opacity-50"
            :class="entry.expanded ? 'fa-chevron-up' : 'fa-chevron-down'"
          ></i>
        </button>
      </div>

      <!-- Body -->
      <div v-show="entry.expanded" class="border-t border-base-content/10">
        <!-- Loading -->
        <div v-if="entry.loading" class="space-y-2 p-3" aria-hidden="true">
          <div class="skeleton h-3 w-full rounded"></div>
          <div class="skeleton h-3 w-4/5 rounded"></div>
          <div class="skeleton h-3 w-2/3 rounded"></div>
        </div>

        <!-- Changed file: diff against the file on disk -->
        <div
          v-else-if="entry.view === 'diff' && entry.originalContent"
          class="max-h-[480px] overflow-auto bg-base-200/40"
        >
          <DiffViewer
            :org-content="entry.originalContent"
            :new-content="entry.content"
            :file="entry.path"
            :language="languageOf(entry)"
          />
        </div>

        <!-- New file (or manual content view): the full content -->
        <div v-else class="max-h-[480px] overflow-auto bg-base-200/40">
          <VueCodeHighlighter
            :key="`${entry.key}:${entry.content?.length || 0}`"
            :code="entry.content"
            :lang="languageOf(entry)"
          />
        </div>
      </div>
    </div>

    <!-- ── Linked files without a code block ── -->
    <div
      v-for="file in linkedFilesNotInBlocks"
      :key="file"
      class="flex items-center gap-2 rounded-md bg-base-100 px-2 py-1 text-xs"
    >
      <button
        class="btn btn-xs btn-ghost tooltip tooltip-left"
        data-tip="Add file to chat"
        aria-label="Add file to chat"
        @click.stop="$emit('add-file', file)"
      >
        <i class="fa-solid fa-plus"></i>
      </button>
      <i class="fa-solid fa-file text-primary"></i>
      <a
        class="flex-1 truncate cursor-pointer hover:underline"
        :title="file"
        @click="$emit('open-file', file)"
      >
        {{ file.split('/').reverse()[0] }}
      </a>
      <button
        class="btn btn-xs btn-ghost text-base-content/40 hover:text-error"
        title="Remove from chat"
        aria-label="Remove from chat"
        @click.stop="$emit('remove-file', file)"
      >
        <i class="fa-regular fa-circle-xmark"></i>
      </button>
    </div>

    <!-- ── Empty state ── -->
    <div
      v-if="!files.length && !linkedFilesNotInBlocks.length"
      class="flex flex-col items-center gap-1 py-6 text-base-content/40"
    >
      <i class="fa-solid fa-inbox text-lg"></i>
      <p class="text-sm">No files to display</p>
    </div>
  </div>
</template>

<script>
export default {
  props: ['codeBlocks', 'linkedFiles', 'chat', 'message', 'project', 'selectionKeys', 'selectedKeys', 'savingSelection'],
  emits: ['save-file', 'add-file', 'open-file', 'sub-task', 'remove-file', 'toggle-select'],
  data() {
    return {
      // One entry per code block: { key, path, content, status, view, ... }
      files: []
    }
  },
  computed: {
    // Project the rendered message belongs to. A message can target another
    // project than the chat's (`Message.project_id`), and every block path is
    // relative to THAT project, so it must win over the chat's project.
    messageProject() {
      const projectId = this.message?.project_id
      if (!projectId) return null
      return this.$storex.projects.allProjectsById?.[projectId]
        || (this.$storex.projects.allProjects || []).find(p => p.project_id === projectId)
        || null
    },
    chatProject() {
      const projectId = this.chat?.project_id || this.chat?.owner_project_id
      if (!projectId) return null
      return this.$storex.projects.allProjectsById?.[projectId] || null
    },
    writeProject() {
      return this.project || this.messageProject || this.chatProject || null
    },
    api() {
      return this.writeProject?.$api
        || this.$storex.projects?.activeProject?.$api
        || this.$storex.api
    },
    newCount() {
      return this.files.filter(entry => entry.status === 'new').length
    },
    modifiedCount() {
      return this.files.filter(entry => entry.status === 'modified').length
    },
    deletedCount() {
      return this.files.filter(entry => entry.status === 'deleted').length
    },
    allExpanded() {
      return this.files.length > 0 && this.files.every(entry => entry.expanded)
    },
    linkedFilesNotInBlocks() {
      return this.linkedFiles || []
    }
  },
  watch: {
    codeBlocks: {
      immediate: true,
      handler() {
        this.buildFiles()
      }
    },
    // Files stay unresolved while a message streams: resolve them once it ends.
    'message.done'(done) {
      if (done) this.retryUnresolvedFiles()
    }
  },
  methods: {
    // ─────────────────────────────────────────────────────────────
    // Entries
    // ─────────────────────────────────────────────────────────────
    // Entries are keyed by `${path}#${index}`, the same key the parent uses for
    // bulk selection, so rebuilding (streaming) keeps selections and loaded state.
    buildFiles() {
      const previous = new Map((this.files || []).map(entry => [entry.key, entry]))

      this.files = (this.codeBlocks || []).map((block, index) => {
        const path = block?.filePath || block?.file_path || block?.path || ''
        const key = `${path}#${index}`
        const content = block?.content ?? block?.code ?? ''
        const existing = previous.get(key)

        if (existing) {
          existing.content = content
          return existing
        }

        return {
          key,
          index,
          path,
          name: path ? path.split('/').reverse()[0] : 'Snippet',
          language: block?.language || '',
          changeType: (block?.changeType || block?.change_type || '').toLowerCase(),
          content,
          // 'unknown' | 'draft' | 'new' | 'modified' | 'deleted'
          status: 'unknown',
          // 'content' | 'diff'
          view: 'content',
          viewTouched: false,
          expanded: true,
          loading: true,
          requested: false,
          originalContent: null,
          stats: null,
          lastModification: null
        }
      })

      this.files.forEach(entry => this.loadFileState(entry.key))
    },
    // Decides whether the block creates a file or changes an existing one:
    // - `change_type` from a <file_change> envelope is authoritative
    // - a file that cannot be read (or is empty) is being created
    // - a readable file is compared against its on-disk content
    async loadFileState(key) {
      const entry = this.files.find(item => item.key === key)
      if (!entry || entry.requested) return

      entry.requested = true
      entry.loading = true

      if (entry.changeType === 'new') {
        this.applyFileState(key, { status: 'new' })
        return
      }
      if (entry.changeType === 'delete' || entry.changeType === 'deleted') {
        this.applyFileState(key, { status: 'deleted' })
        return
      }
      // A streaming message has not finished writing the file yet
      if (this.message && this.message.done === false) {
        this.applyFileState(key, { status: 'draft' })
        return
      }
      if (!entry.path || !this.api?.files) {
        this.applyFileState(key, { status: 'draft' })
        return
      }

      let originalContent = ''
      let lastModification = null

      try {
        const res = await this.api.files.read(entry.path)
        originalContent = typeof res === 'string'
          ? res
          : (res?.content ?? res?.page_content ?? '')
        lastModification = res?.last_modification || null
      } catch (ex) {
        // The file does not exist yet: this block creates it
        originalContent = ''
      }

      if (!originalContent) {
        this.applyFileState(key, { status: 'new' })
        return
      }

      let stats = null
      try {
        const res = await this.api.files.diff({ path: entry.path, content: entry.content })
        stats = this.parseStats(res?.stats)
        lastModification = res?.last_modification || lastModification
      } catch (ex) {
        console.error(`[MessageFileView] Failed to load diff for ${entry.path}`, ex)
      }

      this.applyFileState(key, {
        status: 'modified',
        originalContent,
        stats,
        lastModification
      })
    },
    applyFileState(key, patch) {
      const entry = this.files.find(item => item.key === key)
      if (!entry) return

      Object.assign(entry, patch)
      entry.loading = false

      // Default view: content for new files, diff for changed ones.
      // A manual toggle always wins.
      if (!entry.viewTouched) {
        entry.view = entry.status === 'modified' && entry.originalContent ? 'diff' : 'content'
      }
    },
    retryUnresolvedFiles() {
      this.files
        .filter(entry => entry.status === 'draft' || entry.status === 'unknown')
        .forEach(entry => {
          entry.requested = false
          this.loadFileState(entry.key)
        })
    },
    // "3 deletions, 2 insertions" -> { deletions: 3, insertions: 2 }
    parseStats(stats) {
      if (!stats || typeof stats !== 'string') return null
      const deletions = Number((stats.match(/(\d+)\s+deletion/) || [])[1] || 0)
      const insertions = Number((stats.match(/(\d+)\s+insertion/) || [])[1] || 0)
      if (!deletions && !insertions) return null
      return { deletions, insertions }
    },

    // ─────────────────────────────────────────────────────────────
    // Presentation
    // ─────────────────────────────────────────────────────────────
    languageOf(entry) {
      const language = entry.language
      if (language && hljs.getLanguage(language)) return language

      const extension = entry.path?.split('.').reverse()[0]?.toLowerCase()
      const mapped = extension ? EXTENSION_LANGUAGE_MAP[extension] || extension : null
      if (mapped && hljs.getLanguage(mapped)) return mapped

      return 'plaintext'
    },
    statusLabel(entry) {
      const labels = { new: 'New', modified: 'Changed', deleted: 'Deleted' }
      return labels[entry.status] || ''
    },
    statusBadge(entry) {
      const badges = {
        new: 'badge-success',
        modified: 'badge-warning',
        deleted: 'badge-error'
      }
      return badges[entry.status] || 'badge-ghost'
    },
    statusIcon(entry) {
      const icons = {
        new: 'fa-solid fa-file-circle-plus text-success',
        modified: 'fa-solid fa-file-pen text-warning',
        deleted: 'fa-solid fa-file-circle-minus text-error'
      }
      return icons[entry.status] || 'fa-solid fa-file text-base-content/40'
    },
    cardClass(entry) {
      const borders = {
        new: 'border-success/40',
        modified: 'border-warning/40',
        deleted: 'border-error/40'
      }
      return borders[entry.status] || 'border-base-content/10'
    },
    canToggleView(entry) {
      return entry.status === 'modified' && !!entry.originalContent
    },

    // ─────────────────────────────────────────────────────────────
    // Actions
    // ─────────────────────────────────────────────────────────────
    isSelectable(entry) {
      return (this.selectionKeys || []).includes(entry.key)
    },
    isSelected(entry) {
      return (this.selectedKeys || []).includes(entry.key)
    },
    toggleExpanded(entry) {
      entry.expanded = !entry.expanded
    },
    toggleAllExpanded() {
      const expanded = !this.allExpanded
      this.files.forEach(entry => { entry.expanded = expanded })
    },
    toggleView(entry) {
      entry.viewTouched = true
      entry.view = entry.view === 'diff' ? 'content' : 'diff'
    },
    copyContent(entry) {
      this.$ui.copyTextToClipboard(entry.content)
    },
    saveFile(entry) {
      // Same payload as CodeViewer: blocks belong to THIS block's project, not
      // necessarily to the chat's one.
      this.$emit('save-file', {
        file: entry.path,
        content: entry.content,
        project: this.writeProject
      })
    },
    createSubTask(entry) {
      const content = [
        '```' + this.languageOf(entry) + ' ' + entry.path,
        entry.content,
        '```'
      ].join('\n')
      this.$emit('sub-task', { file: entry.path, content })
    }
  }
}
</script>
