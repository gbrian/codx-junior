<template>
  <div class="bg-base-300 p-4 rounded-md">
    <!-- Header -->
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="min-w-0">
        <div class="font-semibold flex items-center gap-2">
          <i class="fa-solid fa-brain text-primary text-xs"></i>
          Learned knowledge
          <span v-if="!canWrite && loaded" class="badge badge-xs badge-ghost gap-1" title="Project admin or knowledge admin rights are required to edit">
            <i class="fa-solid fa-lock"></i> read-only
          </span>
        </div>
        <div class="text-xs text-base-content/60 mt-1">
          Rules are injected in every chat · Knowledge files are indexed and retrieved on demand
        </div>
      </div>
      <button
        class="btn btn-xs btn-ghost gap-1"
        :disabled="loading"
        title="Reload what this profile has learned"
        @click="load()"
      >
        <i class="fa-solid fa-rotate-right" :class="{ 'fa-spin': loading }"></i>
        Refresh
      </button>
    </div>

    <!-- Feedback -->
    <div v-if="error" class="alert alert-error mt-3 py-2 text-xs">
      <span class="flex-1">{{ error }}</span>
      <button class="btn btn-xs btn-ghost" title="Dismiss" @click="error = ''">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
    <div v-if="notice" class="alert alert-success mt-3 py-2 text-xs">
      <span class="flex-1">{{ notice }}</span>
      <button class="btn btn-xs btn-ghost" title="Dismiss" @click="notice = ''">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- Tabs -->
    <div role="tablist" class="tabs tabs-boxed tabs-sm mt-3 w-fit">
      <button
        role="tab"
        class="tab gap-1"
        :class="tab === 'rules' && 'tab-active'"
        :aria-selected="tab === 'rules'"
        @click="tab = 'rules'"
      >
        Rules
        <span class="badge badge-xs badge-ghost">{{ rules.length }}</span>
      </button>
      <button
        role="tab"
        class="tab gap-1"
        :class="tab === 'files' && 'tab-active'"
        :aria-selected="tab === 'files'"
        @click="tab = 'files'"
      >
        Knowledge files
        <span class="badge badge-xs badge-ghost">{{ files.length }}</span>
      </button>
    </div>

    <!-- ── RULES ─────────────────────────────────────────────────────────── -->
    <div v-show="tab === 'rules'" class="mt-3 flex flex-col gap-2">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="text-xs text-base-content/60">
          {{ overview.rules_count }} / {{ limits.max_rules }} rules ·
          {{ overview.rules_chars }} chars · max {{ limits.max_rule_chars }} chars per rule
        </div>
        <button v-if="canWrite" class="btn btn-xs btn-primary gap-1" @click="openRuleForm(null)">
          <i class="fa-solid fa-plus"></i> New rule
        </button>
      </div>

      <!-- Rule form -->
      <div v-if="ruleForm" class="bg-base-200 border border-primary/40 rounded-md p-3 flex flex-col gap-2">
        <div class="form-control">
          <label class="label py-1" for="pk-rule-title">
            <span class="label-text text-xs">Title (identifier used to update or forget it)</span>
          </label>
          <input
            id="pk-rule-title"
            ref="ruleTitleInput"
            v-model="ruleForm.title"
            type="text"
            :readonly="!!ruleForm.originalTitle"
            class="input input-bordered input-sm"
            placeholder="Angular conventions"
          />
        </div>
        <div class="form-control">
          <label class="label py-1" for="pk-rule-content">
            <span class="label-text text-xs">Instruction (Markdown, short and imperative)</span>
          </label>
          <textarea
            id="pk-rule-content"
            v-model="ruleForm.content"
            rows="6"
            class="textarea textarea-bordered text-xs font-mono leading-relaxed"
            placeholder="Always use standalone components..."
          ></textarea>
          <label class="label py-1">
            <span class="label-text-alt text-xs" :class="ruleCharsLeft < 0 ? 'text-error' : 'text-base-content/60'">
              {{ ruleForm.content.length }} / {{ limits.max_rule_chars }} chars
              <template v-if="ruleCharsLeft < 0"> · too long, store it as a knowledge file</template>
            </span>
          </label>
        </div>
        <div class="flex justify-end gap-2">
          <button class="btn btn-xs" @click="ruleForm = null">Cancel</button>
          <button
            class="btn btn-xs btn-primary"
            :disabled="ruleSaving || !ruleForm.title.trim() || !ruleForm.content.trim() || ruleCharsLeft < 0"
            @click="saveRule()"
          >
            <i v-if="ruleSaving" class="fa-solid fa-spinner fa-spin"></i>
            {{ ruleForm.originalTitle ? 'Update rule' : 'Learn rule' }}
          </button>
        </div>
      </div>

      <!-- Rule list -->
      <div v-if="rules.length" class="flex flex-col gap-2">
        <div
          v-for="rule in rules"
          :key="rule.title"
          class="bg-base-200 rounded-md p-3"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-semibold text-sm min-w-0 truncate">{{ rule.title }}</span>
            <span
              class="badge badge-xs"
              :class="rule.editable ? 'badge-primary' : 'badge-ghost'"
              :title="rule.editable ? 'Learned by this project' : 'Inherited (read-only)'"
            >
              {{ rule.editable ? 'this project' : 'inherited: ' + rule.source }}
            </span>
            <span class="text-xs text-base-content/50 ml-auto">{{ rule.content.length }} chars</span>
          </div>
          <pre class="mt-2 text-xs whitespace-pre-wrap break-words text-base-content/80 font-sans">{{ rule.content }}</pre>
          <div v-if="rule.editable && canWrite" class="mt-2 flex flex-wrap gap-1">
            <button class="btn btn-xs btn-ghost gap-1" @click="openRuleForm(rule)">
              <i class="fa-solid fa-pen"></i> Edit
            </button>
            <button class="btn btn-xs btn-ghost gap-1" @click="askPromote(rule)">
              <i class="fa-solid fa-arrow-down"></i> Move to file
            </button>
            <button class="btn btn-xs btn-ghost text-error gap-1" @click="askForget(rule)">
              <i class="fa-solid fa-trash"></i> Forget
            </button>
          </div>
        </div>
      </div>
      <div v-else class="text-xs text-base-content/50 border border-dashed border-base-content/20 rounded-md p-6 text-center">
        No rules yet. A rule is a short instruction the profile must follow in every chat.
      </div>
    </div>

    <!-- ── KNOWLEDGE FILES ───────────────────────────────────────────────── -->
    <div v-show="tab === 'files'" class="mt-3 grid grid-cols-1 lg:grid-cols-3 gap-3">
      <!-- File list -->
      <div class="flex flex-col gap-2 min-w-0">
        <button v-if="canWrite" class="btn btn-xs btn-primary gap-1" @click="startNewFile()">
          <i class="fa-solid fa-plus"></i> New knowledge file
        </button>
        <div v-if="files.length" class="flex flex-col gap-1 max-h-96 overflow-auto">
          <button
            v-for="entry in files"
            :key="entry.path"
            class="text-left px-2 py-1.5 rounded-md border transition-colors"
            :class="isSelected(entry)
              ? 'bg-primary/15 border-primary/40'
              : 'bg-base-200 border-base-content/10 hover:bg-base-200/70'"
            @click="selectFile(entry)"
          >
            <span class="flex items-center justify-between gap-2">
              <span class="truncate text-xs font-mono">{{ entry.file }}</span>
              <span class="badge badge-xs badge-ghost shrink-0">{{ entry.source }}</span>
            </span>
            <span class="block text-xs text-base-content/50">{{ formatSize(entry.size) }}</span>
          </button>
        </div>
        <div v-else class="text-xs text-base-content/50 border border-dashed border-base-content/20 rounded-md p-6 text-center">
          No knowledge files yet. Use one for long material (guidelines, docs, examples).
        </div>
      </div>

      <!-- File editor -->
      <div class="lg:col-span-2 min-w-0">
        <div v-if="editorOpen" class="bg-base-200 rounded-md border border-base-content/10 overflow-hidden">
          <div class="flex items-center gap-2 px-2 py-1.5 border-b border-base-content/10">
            <input
              v-model="fileName"
              type="text"
              :readonly="!!selectedFile || !canWrite"
              class="input input-bordered input-xs flex-1 font-mono text-xs"
              placeholder="guidelines/state-management.md"
              aria-label="Knowledge file name"
            />
            <button
              class="btn btn-xs btn-ghost gap-1"
              :title="filePreview ? 'Edit markdown' : 'Preview markdown'"
              @click="filePreview = !filePreview"
            >
              <i class="fa-solid" :class="filePreview ? 'fa-pen' : 'fa-eye'"></i>
            </button>
            <button
              v-if="selectedFile && canWrite"
              class="btn btn-xs btn-ghost gap-1"
              title="Convert this file into a rule"
              @click="askPromoteFile()"
            >
              <i class="fa-solid fa-arrow-up"></i>
            </button>
            <button
              v-if="selectedFile && canWrite"
              class="btn btn-xs btn-ghost text-error"
              title="Delete this file"
              @click="askDeleteFile()"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
            <button class="btn btn-xs btn-ghost" title="Close editor" @click="closeFile()">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="p-2">
            <div v-if="fileLoading" class="text-xs text-base-content/60 p-4 text-center">
              <i class="fa-solid fa-spinner fa-spin mr-1"></i> Loading file...
            </div>
            <textarea
              v-else-if="!filePreview"
              v-model="fileContent"
              :readonly="!canWrite"
              rows="16"
              spellcheck="false"
              class="textarea w-full bg-base-100 font-mono text-xs leading-relaxed"
              placeholder="# Conventions&#10;&#10;- Always use standalone components"
              aria-label="Knowledge file content"
            ></textarea>
            <Markdown
              v-else
              class="p-2 bg-base-100 rounded-md min-h-48"
              :text="fileContent || '> Nothing to preview yet.'"
            />
          </div>
          <div class="flex flex-wrap items-center justify-between gap-2 px-2 py-1.5 border-t border-base-content/10">
            <span class="text-xs text-base-content/50">
              <template v-if="!canWrite">Read-only: project admin or knowledge admin rights required</template>
              <template v-else>{{ normalizedFileName || 'A .md extension is added when none is given' }}</template>
            </span>
            <button
              class="btn btn-xs btn-primary gap-1"
              :disabled="fileSaving || !canWrite || !normalizedFileName || !fileContent.trim()"
              @click="saveFile()"
            >
              <i v-if="fileSaving" class="fa-solid fa-spinner fa-spin"></i>
              <i v-else class="fa-solid fa-floppy-disk"></i>
              {{ selectedFile ? 'Update file' : 'Create file' }}
            </button>
          </div>
        </div>
        <div v-else class="flex items-center justify-center h-full min-h-48 text-xs text-base-content/40 border border-dashed border-base-content/20 rounded-md p-6 text-center">
          Select a knowledge file to edit it, or create a new one.
        </div>
      </div>
    </div>

    <!-- Confirm dialog -->
    <div v-if="confirm" class="modal modal-open" role="dialog" aria-modal="true">
      <div class="modal-box">
        <h3 class="text-base font-bold">{{ confirm.title }}</h3>
        <p class="py-3 text-sm text-base-content/70">{{ confirm.message }}</p>
        <div class="modal-action">
          <button class="btn btn-sm" @click="confirm = null">Cancel</button>
          <button class="btn btn-sm btn-error" @click="runConfirm()">
            {{ confirm.confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { profilesModule, RULE_TO_FILE, FILE_TO_RULE, normalizeFileName } from '@/api/modules/profiles'

const EMPTY_OVERVIEW = {
  rules: [],
  knowledge_files: [],
  rules_count: 0,
  rules_chars: 0,
  limits: { max_rule_chars: 4000, max_rules: 40 }
}

export default {
  props: {
    // Profile being inspected. `name` and (optionally) `project_id` are used.
    profile: {
      type: Object,
      default: null
    },
    // Project-scoped API instance (`$project.$api`). It is the instance whose
    // connection appends the right `codx_path`, so the profile is always read
    // and written in the project that owns it. Falls back to `$project.$api`
    // and finally to the global API when not provided.
    api: {
      type: Object,
      default: null
    }
  },
  emits: ['changed'],
  data() {
    return {
      loaded: false,
      loading: false,
      error: '',
      notice: '',
      tab: 'rules',
      overview: { ...EMPTY_OVERVIEW },
      canWrite: false,
      ruleForm: null,
      ruleSaving: false,
      selectedFile: null,
      creatingFile: false,
      fileContent: '',
      fileName: '',
      fileLoading: false,
      fileSaving: false,
      filePreview: false,
      confirm: null
    }
  },
  computed: {
    profileName() {
      return (this.profile && this.profile.name) || ''
    },
    limits() {
      return this.overview.limits || EMPTY_OVERVIEW.limits
    },
    rules() {
      return this.overview.rules || []
    },
    files() {
      return this.overview.knowledge_files || []
    },
    editorOpen() {
      return !!(this.selectedFile || this.creatingFile)
    },
    normalizedFileName() {
      return normalizeFileName(this.fileName)
    },
    ruleCharsLeft() {
      if (!this.ruleForm) {
        return this.limits.max_rule_chars || 0
      }
      return (this.limits.max_rule_chars || 0) - this.ruleForm.content.length
    }
  },
  watch: {
    'profile.name'() {
      this.reset()
      this.load()
    },
    'profile.project_id'() {
      this.reset()
      this.load()
    }
  },
  mounted() {
    // Capture phase on `document`: an Escape consumed here (closing the confirm
    // dialog or the rule form) must not reach the listeners of the enclosing
    // drawer, which would close the whole panel at the same time.
    document.addEventListener('keydown', this.onKeydown, true)
    this.load()
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.onKeydown, true)
  },
  methods: {
    /**
     * Resolve the profiles API bound to the project that owns the profile.
     *
     * `profilesModule(api)` only wraps the HTTP helpers, so the resulting
     * object always targets the project of the API instance it received:
     * `$project.$api` (appends that project's `codx_path`) or, when the
     * component is used elsewhere, the global API.
     *
     * @returns {Promise<Object>} Profiles API.
     */
    async profilesApi() {
      if (!this._profilesApi) {
        const api = this.api || this.$project?.$api || this.$storex?.api
        if (!api) {
          throw new Error('Profiles API is not available for this project')
        }
        this._profilesApi = profilesModule(api)
      }
      return this._profilesApi
    },

    reset() {
      this._profilesApi = null
      this.loaded = false
      this.overview = { ...EMPTY_OVERVIEW }
      this.canWrite = false
      this.error = ''
      this.notice = ''
      this.ruleForm = null
      this.closeFile()
    },

    async load() {
      if (!this.profileName) {
        return
      }
      this.loading = true
      this.error = ''
      try {
        const api = await this.profilesApi()
        const overview = await api.knowledge(this.profileName)
        this.overview = { ...EMPTY_OVERVIEW, ...overview }
        this.canWrite = !!overview.can_write
        this.loaded = true
        if (this.selectedFile && !this.files.some((f) => f.file === this.selectedFile.file)) {
          this.closeFile()
        }
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.loading = false
      }
    },

    async afterWrite(message) {
      this.notice = message
      await this.load()
      // Rules are composed into the profile content: the owner must reload it.
      this.$emit('changed')
    },

    errorMessage(ex) {
      const detail = ex?.response?.data?.detail
      if (detail) {
        return Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : String(detail)
      }
      return ex?.message || 'Unexpected error'
    },

    onKeydown(event) {
      if (event.key !== 'Escape') {
        return
      }
      if (this.confirm) {
        event.stopPropagation()
        this.confirm = null
        return
      }
      if (this.ruleForm) {
        event.stopPropagation()
        this.ruleForm = null
      }
    },

    formatSize(size) {
      const bytes = Number(size) || 0
      return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`
    },

    // ── Rules ───────────────────────────────────────────────────────────────

    openRuleForm(rule) {
      this.ruleForm = {
        originalTitle: rule ? rule.title : '',
        title: rule ? rule.title : '',
        content: rule ? rule.content : ''
      }
      this.$nextTick(() => {
        const input = this.$refs.ruleTitleInput
        if (input && !rule) {
          input.focus()
        }
      })
    },

    async saveRule() {
      if (!this.ruleForm || !this.ruleForm.title.trim() || !this.ruleForm.content.trim()) {
        return
      }
      this.ruleSaving = true
      this.error = ''
      try {
        const api = await this.profilesApi()
        const result = await api.saveRule(this.profileName, {
          title: this.ruleForm.title,
          content: this.ruleForm.content
        })
        this.ruleForm = null
        await this.afterWrite(
          result.created ? `Rule "${result.title}" learned` : `Rule "${result.title}" updated`
        )
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.ruleSaving = false
      }
    },

    askForget(rule) {
      this.confirm = {
        type: 'forget',
        title: 'Forget rule',
        message: `The rule "${rule.title}" will be removed from this project. The profile stops receiving it in future chats.`,
        confirmLabel: 'Forget rule',
        ruleTitle: rule.title
      }
    },

    askPromote(rule) {
      this.confirm = {
        type: 'rule-to-file',
        title: 'Move rule to knowledge file',
        message: `The rule "${rule.title}" becomes an indexed knowledge file and is removed from the prompt. It is then retrieved only when relevant.`,
        confirmLabel: 'Move to file',
        ruleTitle: rule.title
      }
    },

    // ── Files ───────────────────────────────────────────────────────────────

    isSelected(entry) {
      return !!(this.selectedFile && this.selectedFile.file === entry.file)
    },

    async selectFile(entry) {
      this.selectedFile = entry
      this.creatingFile = false
      this.fileName = entry.file
      this.fileContent = ''
      this.filePreview = false
      this.error = ''
      this.fileLoading = true
      try {
        const api = await this.profilesApi()
        const payload = await api.readKnowledgeFile(this.profileName, entry.file)
        this.fileContent = payload.content || ''
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.fileLoading = false
      }
    },

    startNewFile() {
      this.selectedFile = null
      this.creatingFile = true
      this.fileName = ''
      this.fileContent = ''
      this.filePreview = false
      this.error = ''
    },

    closeFile() {
      this.selectedFile = null
      this.creatingFile = false
      this.fileName = ''
      this.fileContent = ''
      this.filePreview = false
      this.fileLoading = false
    },

    async saveFile() {
      if (!this.normalizedFileName || !this.fileContent.trim()) {
        return
      }
      this.fileSaving = true
      this.error = ''
      try {
        const api = await this.profilesApi()
        await api.saveKnowledgeFile(this.profileName, {
          fileName: this.normalizedFileName,
          content: this.fileContent,
          overwrite: !!this.selectedFile
        })
        this.creatingFile = false
        await this.afterWrite(`Knowledge file "${this.normalizedFileName}" saved`)
        const saved = this.files.find((entry) => entry.file === this.normalizedFileName)
        if (saved) {
          await this.selectFile(saved)
        } else {
          this.closeFile()
        }
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.fileSaving = false
      }
    },

    askDeleteFile() {
      if (!this.selectedFile) {
        return
      }
      this.confirm = {
        type: 'delete-file',
        title: 'Delete knowledge file',
        message: `"${this.selectedFile.file}" will be deleted from this project. Files inherited from a parent project or from the base profile are read-only.`,
        confirmLabel: 'Delete file',
        fileName: this.selectedFile.file
      }
    },

    askPromoteFile() {
      if (!this.selectedFile) {
        return
      }
      this.confirm = {
        type: 'file-to-rule',
        title: 'Move knowledge file to rule',
        message: `"${this.selectedFile.file}" becomes a rule injected in every chat and the file is deleted. Keep it short (max ${this.limits.max_rule_chars} chars) or summarise it first.`,
        confirmLabel: 'Move to rule',
        fileName: this.selectedFile.file
      }
    },

    // ── Confirmations ───────────────────────────────────────────────────────

    async runConfirm() {
      const action = this.confirm
      if (!action) {
        return
      }
      this.confirm = null
      this.error = ''
      try {
        const api = await this.profilesApi()
        if (action.type === 'forget') {
          await api.deleteRule(this.profileName, action.ruleTitle)
          await this.afterWrite(`Rule "${action.ruleTitle}" forgotten`)
        } else if (action.type === 'delete-file') {
          await api.deleteKnowledgeFile(this.profileName, action.fileName)
          this.closeFile()
          await this.afterWrite(`Knowledge file "${action.fileName}" deleted`)
        } else if (action.type === 'rule-to-file') {
          const result = await api.promote(this.profileName, {
            direction: RULE_TO_FILE,
            title: action.ruleTitle
          })
          await this.afterWrite(`Rule "${result.title}" moved to "${result.file}"`)
        } else if (action.type === 'file-to-rule') {
          const result = await api.promote(this.profileName, {
            direction: FILE_TO_RULE,
            fileName: action.fileName
          })
          this.closeFile()
          await this.afterWrite(`File "${action.fileName}" moved to rule "${result.title}"`)
        }
      } catch (ex) {
        this.error = this.errorMessage(ex)
      }
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->