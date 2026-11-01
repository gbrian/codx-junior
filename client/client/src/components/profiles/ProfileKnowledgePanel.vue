<script setup>
import ProfileKnowledgeFileEditor from './ProfileKnowledgeFileEditor.vue'
import {
  FILE_TO_RULE,
  RULE_TO_FILE,
  deleteKnowledgeFile,
  deleteProfileRule,
  fetchProfileKnowledge,
  promoteProfileKnowledge,
  readKnowledgeFile,
  saveKnowledgeFile,
  saveProfileRule
} from '../../services/profileKnowledgeApi'
</script>

<template>
  <section class="bg-[#1a1a1a] border border-white/5 rounded-lg overflow-hidden">
    <!-- Header -->
    <header class="flex flex-wrap items-start justify-between gap-3 px-4 py-3 border-b border-white/5">
      <div class="min-w-0">
        <h2 class="flex items-center gap-2 text-sm font-semibold text-white">
          <i class="fas fa-brain text-primary text-xs" aria-hidden="true"></i>
          What this profile has learned
          <span
            v-if="profileName"
            class="badge badge-sm bg-primary/20 border-0 text-primary"
          >{{ profileName }}</span>
        </h2>
        <p class="mt-1 text-xs text-white/50">
          Rules are injected in every prompt · Files are indexed and retrieved on demand
        </p>
      </div>
      <div class="flex items-center gap-2">
        <span
          v-if="!canWrite"
          class="inline-flex items-center gap-1 text-[11px] text-white/40"
          title="Project admin or knowledge admin rights are required to edit"
        >
          <i class="fas fa-lock" aria-hidden="true"></i> read-only
        </span>
        <button
          type="button"
          class="btn btn-sm btn-ghost text-white/60 hover:text-white transition-colors duration-150"
          :disabled="loading || !profileName"
          @click="load"
        >
          <i class="fas fa-rotate-right mr-1" :class="{ 'fa-spin': loading }" aria-hidden="true"></i>
          Refresh
        </button>
      </div>
    </header>

    <div class="px-4 py-3 space-y-3">
      <!-- Feedback -->
      <div v-if="error" class="alert alert-error py-2 px-3 text-xs" role="alert">
        <span class="flex-1">{{ error }}</span>
        <button type="button" class="btn btn-xs btn-ghost" @click="dismissError">
          <i class="fas fa-xmark" aria-hidden="true"></i>
          <span class="sr-only">Dismiss error</span>
        </button>
      </div>
      <div v-if="notice" class="alert alert-success py-2 px-3 text-xs" role="status">
        <span class="flex-1">{{ notice }}</span>
        <button type="button" class="btn btn-xs btn-ghost" @click="dismissNotice">
          <i class="fas fa-xmark" aria-hidden="true"></i>
          <span class="sr-only">Dismiss message</span>
        </button>
      </div>

      <!-- Tabs -->
      <div
        class="inline-flex items-center gap-1 p-1 bg-white/5 border border-white/10 rounded-md"
        role="tablist"
        aria-label="Profile knowledge stores"
      >
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          role="tab"
          :id="`pk-tab-${tab.id}`"
          :aria-selected="activeTab === tab.id"
          :aria-controls="`pk-panel-${tab.id}`"
          class="px-3 py-1.5 text-xs font-medium rounded transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
          :class="activeTab === tab.id
            ? 'bg-primary/15 text-primary'
            : 'text-white/60 hover:text-white hover:bg-white/5'"
          @click="setTab(tab.id)"
        >
          {{ tab.label }}
          <span class="ml-1 text-[11px] text-white/40">{{ tab.count }}</span>
        </button>
      </div>

      <!-- RULES -->
      <div
        v-if="activeTab === 'rules'"
        :id="'pk-panel-rules'"
        role="tabpanel"
        :aria-labelledby="'pk-tab-rules'"
        class="space-y-3"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="h-1.5 w-40 bg-white/5 rounded-full overflow-hidden" aria-hidden="true">
              <div
                class="h-full rounded-full transition-all duration-200"
                :class="rulesBudgetClass"
                :style="{ width: rulesBudgetPercent + '%' }"
              ></div>
            </div>
            <p class="mt-1 text-[11px] text-white/40">
              {{ overview.rules_count }} / {{ limits.max_rules }} rules ·
              {{ overview.rules_chars }} chars ·
              max {{ limits.max_rule_chars }} chars per rule
            </p>
          </div>
          <button
            v-if="canWrite"
            type="button"
            class="btn btn-sm btn-primary"
            @click="openRuleForm(null)"
          >
            <i class="fas fa-plus mr-1" aria-hidden="true"></i>
            New rule
          </button>
        </div>

        <!-- Rule form -->
        <form
          v-if="ruleForm.open"
          class="bg-[#1f1f1f] border border-primary/30 rounded-md p-3 space-y-2"
          @submit.prevent="submitRule"
        >
          <div>
            <label for="pk-rule-title" class="block text-[11px] font-medium text-white/60 mb-1">
              Title (identifier used to update or forget the rule)
            </label>
            <input
              id="pk-rule-title"
              ref="ruleTitleInput"
              v-model="ruleForm.title"
              type="text"
              :readonly="!!ruleForm.originalTitle"
              class="input input-sm w-full bg-white/5 border-white/10 rounded text-sm text-white placeholder:text-white/25 outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-colors duration-150"
              placeholder="Angular conventions"
            />
          </div>
          <div>
            <label for="pk-rule-content" class="block text-[11px] font-medium text-white/60 mb-1">
              Instruction (Markdown, short and imperative)
            </label>
            <textarea
              id="pk-rule-content"
              v-model="ruleForm.content"
              rows="6"
              class="textarea w-full bg-white/5 border border-white/10 rounded text-xs font-mono leading-relaxed text-white placeholder:text-white/25 outline-none resize-y focus:border-primary/50 focus:bg-white/[0.08] transition-colors duration-150"
              placeholder="Always use standalone components..."
            ></textarea>
            <p
              class="mt-1 text-[11px]"
              :class="ruleCharsLeft < 0 ? 'text-error' : 'text-white/40'"
            >
              {{ ruleForm.content.length }} / {{ limits.max_rule_chars }} chars
              <span v-if="ruleCharsLeft < 0">· too long, store it as a knowledge file</span>
            </p>
          </div>
          <div class="flex items-center justify-end gap-2">
            <button
              type="button"
              class="btn btn-sm bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
              @click="closeRuleForm"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn btn-sm btn-primary"
              :disabled="ruleSaving || !ruleForm.title.trim() || !ruleForm.content.trim() || ruleCharsLeft < 0"
            >
              <span v-if="ruleSaving" class="loading loading-spinner loading-xs mr-1"></span>
              {{ ruleForm.originalTitle ? 'Update rule' : 'Learn rule' }}
            </button>
          </div>
        </form>

        <!-- Rule list -->
        <ul v-if="rules.length" class="space-y-2">
          <li
            v-for="rule in rules"
            :key="rule.title"
            class="bg-[#1f1f1f] border border-white/5 rounded-md p-3 hover:border-white/10 transition-colors duration-150"
          >
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-sm font-medium text-white min-w-0 truncate">{{ rule.title }}</h3>
              <span
                class="badge badge-sm border-0"
                :class="rule.editable
                  ? 'bg-primary/20 text-primary'
                  : 'bg-white/10 text-white/60'"
              >
                {{ rule.editable ? 'this project' : 'inherited: ' + rule.source }}
              </span>
              <span class="text-[11px] text-white/40 ml-auto">{{ rule.content.length }} chars</span>
            </div>
            <p class="mt-1.5 text-xs text-white/70 leading-relaxed line-clamp-4 whitespace-pre-wrap">{{ rule.content }}</p>
            <div v-if="rule.editable && canWrite" class="mt-2 flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                class="btn btn-xs bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                @click="openRuleForm(rule)"
              >
                <i class="fas fa-pen mr-1" aria-hidden="true"></i> Edit
              </button>
              <button
                type="button"
                class="btn btn-xs bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                @click="askPromoteRule(rule)"
              >
                <i class="fas fa-arrow-down mr-1" aria-hidden="true"></i> Move to file
              </button>
              <button
                type="button"
                class="btn btn-xs btn-ghost text-error hover:bg-error/10"
                @click="askDeleteRule(rule)"
              >
                <i class="fas fa-trash mr-1" aria-hidden="true"></i> Forget
              </button>
            </div>
          </li>
        </ul>
        <p
          v-else
          class="px-3 py-6 text-center text-xs text-white/40 bg-white/[0.02] border border-dashed border-white/10 rounded-md"
        >
          No rules yet. A rule is a short instruction the profile must follow in every chat.
        </p>
      </div>

      <!-- FILES -->
      <div
        v-else
        :id="'pk-panel-files'"
        role="tabpanel"
        :aria-labelledby="'pk-tab-files'"
        class="grid grid-cols-1 lg:grid-cols-[minmax(0,18rem)_minmax(0,1fr)] gap-3"
      >
        <div class="space-y-2 min-w-0">
          <button
            v-if="canWrite"
            type="button"
            class="btn btn-sm btn-primary w-full"
            @click="startNewFile"
          >
            <i class="fas fa-plus mr-1" aria-hidden="true"></i>
            New knowledge file
          </button>
          <ul v-if="files.length" class="space-y-1.5 max-h-96 overflow-auto pr-1">
            <li v-for="entry in files" :key="entry.path">
              <button
                type="button"
                class="w-full text-left px-3 py-2 rounded-md border transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
                :class="isSelected(entry)
                  ? 'bg-primary/15 border-primary/40'
                  : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06] hover:border-white/10'"
                :aria-current="isSelected(entry) ? 'true' : undefined"
                @click="selectFile(entry)"
              >
                <span class="flex items-center justify-between gap-2">
                  <span class="truncate text-xs font-mono text-white/90">{{ entry.file }}</span>
                  <span class="badge badge-xs border-0 bg-white/10 text-white/60 shrink-0">{{ entry.source }}</span>
                </span>
                <span class="block mt-0.5 text-[11px] text-white/40">{{ formatSize(entry.size) }}</span>
              </button>
            </li>
          </ul>
          <p
            v-else
            class="px-3 py-6 text-center text-xs text-white/40 bg-white/[0.02] border border-dashed border-white/10 rounded-md"
          >
            No knowledge files yet. Use one for long material (guidelines, docs, examples).
          </p>
        </div>

        <div class="min-w-0">
          <ProfileKnowledgeFileEditor
            v-if="editorOpen"
            :file="selectedFile"
            :content="fileContent"
            :can-write="canWrite"
            :saving="fileSaving"
            :error="fileError"
            @save="onFileSave"
            @delete="askDeleteFile"
            @promote="askPromoteFile"
            @cancel="closeFile"
          />
          <div
            v-else
            class="flex items-center justify-center h-full min-h-[16rem] px-4 text-center text-xs text-white/35 bg-white/[0.02] border border-dashed border-white/10 rounded-md"
          >
            Select a knowledge file to edit it, or create a new one.
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm dialog -->
    <div
      v-if="pendingAction"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pk-confirm-title"
      @click.self="pendingAction = null"
    >
      <div class="w-full max-w-md bg-[#1a1a1a] border border-white/10 rounded-xl shadow-2xl">
        <h3 id="pk-confirm-title" class="px-6 pt-4 text-sm font-semibold text-white">
          {{ pendingAction.title }}
        </h3>
        <p class="px-6 py-3 text-sm text-white/70 leading-relaxed">{{ pendingAction.message }}</p>
        <div class="flex gap-3 px-6 py-4 border-t border-white/5">
          <button
            type="button"
            class="btn btn-sm flex-1 bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
            @click="pendingAction = null"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-sm flex-1 btn-error"
            @click="runPendingAction"
          >
            {{ pendingAction.confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
const EMPTY_OVERVIEW = {
  rules: [],
  knowledge_files: [],
  rules_count: 0,
  rules_chars: 0,
  limits: { max_rule_chars: 4000, max_rules: 40 }
}

export default {
  props: {
    // Profile to inspect. Needs `name` and `project_id` (see ProfileManager.load_profile).
    profile: {
      type: Object,
      default: null
    }
  },
  emits: ['changed'],
  data() {
    return {
      loading: false,
      error: '',
      notice: '',
      activeTab: 'rules',
      overview: { ...EMPTY_OVERVIEW },
      canWrite: false,
      ruleForm: { open: false, originalTitle: '', title: '', content: '' },
      ruleSaving: false,
      selectedFile: null,
      creatingFile: false,
      fileContent: '',
      fileLoading: false,
      fileSaving: false,
      fileError: '',
      pendingAction: null
    }
  },
  computed: {
    profileName() {
      return (this.profile && this.profile.name) || ''
    },
    projectId() {
      return (this.profile && this.profile.project_id) || ''
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
    tabs() {
      return [
        { id: 'rules', label: 'Rules', count: this.rules.length },
        { id: 'files', label: 'Knowledge files', count: this.files.length }
      ]
    },
    editorOpen() {
      return !!(this.selectedFile || this.creatingFile)
    },
    rulesBudgetPercent() {
      const max = this.limits.max_rules || 1
      return Math.min(100, Math.round((this.overview.rules_count / max) * 100))
    },
    rulesBudgetClass() {
      if (this.rulesBudgetPercent >= 100) {
        return 'bg-error'
      }
      if (this.rulesBudgetPercent >= 80) {
        return 'bg-warning'
      }
      return 'bg-primary'
    },
    ruleCharsLeft() {
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
    window.addEventListener('keydown', this.onKeydown)
    this.load()
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    // ── Data ────────────────────────────────────────────────────────────────
    async load() {
      if (!this.profileName || !this.projectId) {
        return
      }
      this.loading = true
      this.error = ''
      try {
        const payload = await fetchProfileKnowledge({
          profileName: this.profileName,
          projectId: this.projectId
        })
        this.overview = { ...EMPTY_OVERVIEW, ...payload }
        this.canWrite = !!payload.can_write
        if (this.selectedFile && !this.files.some((file) => file.file === this.selectedFile.file)) {
          this.closeFile()
        }
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.loading = false
      }
    },
    reset() {
      this.overview = { ...EMPTY_OVERVIEW }
      this.canWrite = false
      this.error = ''
      this.notice = ''
      this.activeTab = 'rules'
      this.closeRuleForm()
      this.closeFile()
    },
    async refreshAfterWrite(message) {
      this.notice = message
      await this.load()
      this.$emit('changed')
    },
    errorMessage(ex) {
      return (ex && ex.message) || 'Unexpected error'
    },
    dismissError() {
      this.error = ''
    },
    dismissNotice() {
      this.notice = ''
    },
    setTab(tab) {
      this.activeTab = tab
    },
    onKeydown(event) {
      if (event.key !== 'Escape') {
        return
      }
      if (this.pendingAction) {
        this.pendingAction = null
      } else if (this.ruleForm.open) {
        this.closeRuleForm()
      }
    },
    formatSize(size) {
      const bytes = Number(size) || 0
      if (bytes < 1024) {
        return `${bytes} B`
      }
      return `${(bytes / 1024).toFixed(1)} KB`
    },

    // ── Rules ───────────────────────────────────────────────────────────────
    openRuleForm(rule) {
      this.ruleForm = {
        open: true,
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
    closeRuleForm() {
      this.ruleForm = { open: false, originalTitle: '', title: '', content: '' }
    },
    async submitRule() {
      if (!this.ruleForm.title.trim() || !this.ruleForm.content.trim()) {
        return
      }
      this.ruleSaving = true
      this.error = ''
      try {
        const result = await saveProfileRule({
          profileName: this.profileName,
          projectId: this.projectId,
          title: this.ruleForm.title,
          content: this.ruleForm.content
        })
        this.closeRuleForm()
        await this.refreshAfterWrite(
          result.created
            ? `Rule "${result.title}" learned`
            : `Rule "${result.title}" updated`
        )
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.ruleSaving = false
      }
    },
    askDeleteRule(rule) {
      this.pendingAction = {
        type: 'delete-rule',
        title: 'Forget rule',
        message: `The rule "${rule.title}" will be removed from this project. The profile will stop receiving it in future chats.`,
        confirmLabel: 'Forget rule',
        title_: rule.title
      }
    },
    askPromoteRule(rule) {
      this.pendingAction = {
        type: 'promote-rule-to-file',
        title: 'Move rule to knowledge file',
        message: `The rule "${rule.title}" will be written as an indexed knowledge file and removed from the prompt. It will be retrieved only when relevant.`,
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
      this.fileContent = ''
      this.fileError = ''
      this.fileLoading = true
      try {
        const payload = await readKnowledgeFile({
          profileName: this.profileName,
          projectId: this.projectId,
          fileName: entry.file
        })
        this.fileContent = payload.content || ''
      } catch (ex) {
        this.fileError = this.errorMessage(ex)
      } finally {
        this.fileLoading = false
      }
    },
    startNewFile() {
      this.selectedFile = null
      this.creatingFile = true
      this.fileContent = ''
      this.fileError = ''
    },
    closeFile() {
      this.selectedFile = null
      this.creatingFile = false
      this.fileContent = ''
      this.fileError = ''
    },
    async onFileSave({ fileName, content, overwrite }) {
      this.fileSaving = true
      this.fileError = ''
      try {
        await saveKnowledgeFile({
          profileName: this.profileName,
          projectId: this.projectId,
          fileName,
          content,
          overwrite
        })
        this.creatingFile = false
        await this.refreshAfterWrite(`Knowledge file "${fileName}" saved`)
        const saved = this.files.find((entry) => entry.file === fileName)
        if (saved) {
          await this.selectFile(saved)
        }
      } catch (ex) {
        this.fileError = this.errorMessage(ex)
      } finally {
        this.fileSaving = false
      }
    },
    askDeleteFile() {
      if (!this.selectedFile) {
        return
      }
      this.pendingAction = {
        type: 'delete-file',
        title: 'Delete knowledge file',
        message: `"${this.selectedFile.file}" will be deleted from this project. Files inherited from a parent project or the base profile are read-only.`,
        confirmLabel: 'Delete file',
        fileName: this.selectedFile.file
      }
    },
    askPromoteFile() {
      if (!this.selectedFile) {
        return
      }
      this.pendingAction = {
        type: 'promote-file-to-rule',
        title: 'Move knowledge file to rule',
        message: `"${this.selectedFile.file}" will become a rule injected in every chat and the file will be deleted. Keep it short (max ${this.limits.max_rule_chars} chars) or summarise it first.`,
        confirmLabel: 'Move to rule',
        fileName: this.selectedFile.file
      }
    },

    // ── Confirmations ───────────────────────────────────────────────────────
    async runPendingAction() {
      const action = this.pendingAction
      if (!action) {
        return
      }
      this.pendingAction = null
      this.error = ''
      try {
        if (action.type === 'delete-rule') {
          await deleteProfileRule({
            profileName: this.profileName,
            projectId: this.projectId,
            title: action.title_
          })
          await this.refreshAfterWrite(`Rule "${action.title_}" forgotten`)
        } else if (action.type === 'delete-file') {
          await deleteKnowledgeFile({
            profileName: this.profileName,
            projectId: this.projectId,
            fileName: action.fileName
          })
          this.closeFile()
          await this.refreshAfterWrite(`Knowledge file "${action.fileName}" deleted`)
        } else if (action.type === 'promote-rule-to-file') {
          await promoteProfileKnowledge({
            profileName: this.profileName,
            projectId: this.projectId,
            direction: RULE_TO_FILE,
            title: action.ruleTitle
          })
          await this.refreshAfterWrite(`Rule "${action.ruleTitle}" moved to a knowledge file`)
        } else if (action.type === 'promote-file-to-rule') {
          await promoteProfileKnowledge({
            profileName: this.profileName,
            projectId: this.projectId,
            direction: FILE_TO_RULE,
            fileName: action.fileName
          })
          this.closeFile()
          await this.refreshAfterWrite(`File "${action.fileName}" moved to a rule`)
        }
      } catch (ex) {
        this.error = this.errorMessage(ex)
      }
    }
  }
}
</script>