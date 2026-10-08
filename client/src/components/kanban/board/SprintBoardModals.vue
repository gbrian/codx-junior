<script setup>
import ChatCostSelector from '../../chat/ChatCostSelector.vue'
import ChatInputBox from '../../chat/ChatInputBox.vue'
import ChatIntelliSense from '../../chat/ChatIntelliSense.vue'
import ChatAttachmentPreview from '../../chat/ChatAttachmentPreview.vue'
import ChatModeSelector from '../../chat/ChatModeSelector.vue'
import ProjectDetailt from '../../ProjectDetailt.vue'
import { getCurrentInstance } from 'vue'

const instance = getCurrentInstance()
defineExpose({
  openNewTask: (...args) => instance.proxy.openNewTask(...args),
  openAddExisting: (...args) => instance.proxy.openAddExisting(...args),
})
</script>

<template>
  <div class="sprint-board-modals">

    <!-- ── New Task / Subtask Modal ── -->
    <modal close @close="closeNewTask" v-if="showNewTask">
      <div class="p-1">
        <h2 class="font-bold text-base mb-4 flex items-center gap-2">
          <i class="fa-solid fa-plus text-primary text-sm"></i>
          {{ newTask.parentId ? 'Add Subtask' : 'New Task' }}
        </h2>

        <!-- Project (icon only) · Task name · Mode -->
        <div class="flex items-center gap-2 mb-3">
          <div class="shrink-0">
            <ProjectDetailt
              :iconify="true"
              :model-value="selectedProject"
              @update:model-value="onProjectSelected"
              @select="onProjectSelected"
            />
          </div>
          <input
            ref="taskNameInput"
            v-model="newTask.name"
            type="text"
            placeholder="Describe what needs to be done…"
            class="grow input"
            @keydown.enter="addNewTask"
          />
          <div class="">
            <ChatModeSelector
              :selected-mode="newTask.mode"
              @mode-changed="newTask.mode = $event"
            />
          </div>
        </div>

        <!-- Initial message, files & images -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Initial message</span>
            <span class="label-text-alt text-[10px] text-base-content/40">Optional · type @ to find files</span>
          </label>

          <!-- The chat composer: message, profiles & model selectors, attachments -->
          <div class="relative">
            <ChatInputBox
              ref="composer"
              :selected-model="newTask.llm_model"
              :ai-models="aiModels"
              :profiles="profiles"
              :selected-profiles="selectedProfiles"
              :cursor-word="cursorWord"
              @send="runNewTask"
              @keydown="onComposerKeyDown"
              @paste="onComposerPaste"
              @drop.stop="onComposerDrop"
              @model-changed="onModelChanged"
              @profiles-selected="onProfilesSelected"
              @upload-files="onUploadFiles"
              @update:cursor-word="onCursorWord"
            />

            <!-- File intellisense — same behaviour as the chat composer -->
            <ChatIntelliSense
              ref="intelliSense"
              :suggestions="intelliSenseSuggestions"
              :active-index="intelliSenseIndex"
              :query="intelliSenseQuery"
              :search-controller="searchController"
              :progress="intelliSenseProgress"
              :top="true"
              @select="onIntelliSenseSelect"
              @hover="intelliSenseIndex = $event"
              @accept-multi="onIntelliSenseAcceptMulti"
              @cancel="cancelIntelliSense"
            />
          </div>

          <!-- Uploaded files / images -->
          <ChatAttachmentPreview
            v-if="newTask.attachments.length"
            :attachments="newTask.attachments"
            @remove-attachment="removeAttachment"
          />

          <!-- Project files: dropped on the composer or referenced with @file.py -->
          <div v-if="composerFiles.length" class="flex flex-wrap gap-1 mt-1">
            <span
              v-for="file in composerFiles"
              :key="file"
              class="badge badge-sm badge-ghost gap-1 max-w-full"
              :title="file"
            >
              <i class="fa-solid fa-file text-[10px]"></i>
              <span class="truncate max-w-[12rem]">{{ fileName(file) }}</span>
              <button
                type="button"
                class="hover:text-error"
                :aria-label="`Remove ${fileName(file)}`"
                @click.stop="removeComposerFile(file)"
              >
                <i class="fa-solid fa-xmark text-[10px]"></i>
              </button>
            </span>
          </div>
        </div>

        <!-- Assignees & Deadline -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <!-- Assignees (one or more users) -->
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Assignees</span>
            </label>
            <div class="dropdown">
              <button
                type="button"
                tabindex="0"
                class="btn btn-sm btn-ghost border border-base-100 w-full justify-start gap-1.5"
              >
                <i class="fa-solid fa-user-plus text-xs"></i>
                <span class="text-xs font-medium">
                  {{ newTask.users.length ? `${newTask.users.length} assigned` : 'Assign users' }}
                </span>
              </button>
              <ul
                tabindex="0"
                class="dropdown-content menu bg-base-200 border border-base-100 rounded-box z-40 w-56 max-h-56 overflow-y-auto p-1 mt-1 shadow-lg"
              >
                <li v-for="u in allUsers" :key="u.username">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      class="checkbox checkbox-xs checkbox-primary"
                      :value="u.username"
                      v-model="newTask.users"
                    />
                    <div class="avatar placeholder">
                      <div class="w-5 h-5 rounded-full bg-base-300 text-[9px] text-base-content/60">
                        <img v-if="u.avatar" :src="u.avatar" :alt="u.username" />
                        <span v-else>{{ initial(u) }}</span>
                      </div>
                    </div>
                    <span class="text-xs truncate">{{ u.username }}</span>
                  </label>
                </li>
                <li v-if="!allUsers.length" class="menu-title text-xs opacity-40">No users</li>
              </ul>
            </div>
            <!-- Selected assignees -->
            <div v-if="selectedUsers.length" class="flex items-center -space-x-2 mt-2">
              <div
                v-for="u in selectedUsers"
                :key="u.username"
                class="avatar placeholder tooltip"
                :data-tip="u.username"
              >
                <div class="w-6 h-6 rounded-full ring-1 ring-base-200 bg-base-300 text-[10px] text-base-content/60">
                  <img v-if="u.avatar" :src="u.avatar" :alt="u.username" />
                  <span v-else>{{ initial(u) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Deadline -->
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Deadline</span>
            </label>
            <input
              v-model="newTask.deadline"
              type="date"
              class="input input-bordered input-sm w-full"
            />
            <div class="flex items-center gap-1.5 mt-2">
              <button type="button" class="btn btn-xs btn-ghost" @click="setDeadline('today')">Today</button>
              <button type="button" class="btn btn-xs btn-ghost" @click="setDeadline('tomorrow')">Tomorrow</button>
              <button type="button" class="btn btn-xs btn-ghost" @click="setDeadline('week')">+1 week</button>
              <button
                v-if="newTask.deadline"
                type="button"
                class="btn btn-xs btn-ghost text-error"
                title="Clear deadline"
                aria-label="Clear deadline"
                @click="newTask.deadline = null"
              >
                <i class="fa-solid fa-xmark text-xs"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Cost budget (cxjcoins) — reusable component -->
        <div class="mb-4">
          <ChatCostSelector
            variant="field"
            label="Cost budget"
            hint="Optional · AI stops when reached"
            :cost="0"
            :estimation-cost="newTask.estimation_cost"
            @cost-changed="newTask.estimation_cost = $event"
          />
        </div>

        <!-- Existing subtasks of the parent not yet in this sprint -->
        <!-- Selecting one adds it to the sprint immediately and closes this dialog -->
        <div v-if="newTask.parentId && parentChildren.length" class="form-control mb-4">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">
              Existing subtasks
            </span>
            <span class="label-text-alt text-xs text-base-content/40">
              {{ parentChildren.length }} not in this sprint
            </span>
          </label>
          <div class="flex flex-col gap-1 max-h-40 overflow-y-auto pr-1">
            <button
              v-for="child in parentChildren"
              :key="child.id"
              type="button"
              class="flex items-center gap-2 px-2 py-1.5 rounded-lg border border-transparent cursor-pointer transition-colors text-left hover:bg-base-content/5 hover:border-primary/30"
              @click="selectParentChild(child)"
            >
              <i class="fa-solid fa-plus text-xs w-3 text-center shrink-0 text-base-content/30"></i>
              <i :class="[statusIcon(child.status), 'text-xs w-3 text-center shrink-0']"></i>
              <span class="flex-1 text-sm truncate">{{ child.name || 'Untitled' }}</span>
              <span class="text-[10px] text-base-content/40 shrink-0">{{ statusLabel(child.status) }}</span>
            </button>
          </div>
          <p class="text-[10px] text-base-content/40 mt-1.5 flex items-center gap-1">
            <i class="fa-solid fa-circle-info"></i>
            Selecting a subtask adds it to this sprint and closes this dialog.
          </p>
        </div>

        <!-- Context note -->
        <div class="flex gap-2 items-start p-2.5 rounded-lg bg-info/5 border border-info/15 mb-4">
          <i class="fa-solid fa-circle-info text-info text-xs mt-0.5 shrink-0"></i>
          <span class="text-xs text-base-content/50">
            <template v-if="newTask.parentId">
              Subtask of <b>{{ parentName || 'parent task' }}</b>. It is linked to its parent and added to
              <b>{{ sprintTitle }}</b> in the
              <span :class="newTaskStatus.textColor">{{ newTaskStatus.label }}</span> column.
            </template>
            <template v-else>
              The task is added to <b>{{ sprintTitle }}</b> and starts in the
              <span :class="newTaskStatus.textColor">{{ newTaskStatus.label }}</span> column.
            </template>
          </span>
        </div>

        <!-- Actions -->
        <div class="flex gap-2 justify-end items-center">
          <span v-if="hasInitialContent" class="text-[10px] text-base-content/40 mr-auto flex items-center gap-1">
            <i class="fa-solid fa-play text-[8px]"></i> Run creates the task and starts the agent now
          </span>
          <button
            class="btn btn-outline btn-sm gap-1.5"
            @click="addNewTask"
            :disabled="!newTask.name?.trim() || creating"
          >
            <i class="fa-solid fa-plus text-xs"></i> Add
          </button>
          <button
            class="btn btn-primary btn-sm gap-1.5"
            title="Create the task and process it immediately"
            @click="runNewTask"
            :disabled="!newTask.name?.trim() || !hasInitialContent || creating"
          >
            <span v-if="creating" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-play text-xs"></i>
            Run
          </button>
        </div>
      </div>
    </modal>

    <!-- ── Add existing tasks Modal ── -->
    <modal close @close="closeAddExisting" v-if="showAddExisting">
      <div class="p-1 flex flex-col max-h-[70vh]">
        <h2 class="font-bold text-base mb-3 flex items-center gap-2">
          <i class="fa-solid fa-folder-plus text-primary text-sm"></i>
          Add existing tasks
        </h2>

        <!-- Search -->
        <label class="input input-sm input-bordered flex items-center gap-2 w-full mb-3 shrink-0">
          <i class="fa-solid fa-magnifying-glass text-xs text-base-content/40"></i>
          <input
            v-model="candidateSearch"
            type="text"
            placeholder="Search tasks across boards…"
            class="grow bg-transparent outline-none text-xs min-w-0"
          />
        </label>

        <!-- Candidates -->
        <div class="flex-1 overflow-y-auto pr-1 flex flex-col gap-1 min-h-0">
          <label
            v-for="t in candidateTasks"
            :key="t.id"
            class="flex items-center gap-3 px-2 py-2 rounded-lg cursor-pointer border transition-colors"
            :class="selected.includes(t.id)
              ? 'border-primary/40 bg-primary/10'
              : 'border-transparent hover:bg-base-content/5'"
          >
            <input type="checkbox" class="checkbox checkbox-xs checkbox-primary" :value="t.id" v-model="selected" />
            <i :class="[statusIcon(t.status), 'text-xs w-3 text-center shrink-0']"></i>
            <span class="flex-1 text-sm truncate">{{ t.name || 'Untitled' }}</span>
            <span class="text-[10px] text-base-content/40 shrink-0">
              {{ t.board || t.column || '—' }} · {{ statusLabel(t.status) }}
            </span>
          </label>

          <div
            v-if="!candidateTasks.length"
            class="flex flex-col items-center gap-2 py-10 text-base-content/25"
          >
            <i class="fa-solid fa-inbox text-2xl"></i>
            <span class="text-xs">No tasks available to add</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-between gap-2 pt-3 mt-2 border-t border-base-100 shrink-0">
          <span class="text-xs text-base-content/40">{{ selected.length }} selected</span>
          <div class="flex gap-2">
            <button class="btn btn-ghost btn-sm" @click="closeAddExisting">Cancel</button>
            <button
              class="btn btn-primary btn-sm gap-1.5"
              @click="confirmAddExisting"
              :disabled="!selected.length"
            >
              <i class="fa-solid fa-check text-xs"></i> Add selected
            </button>
          </div>
        </div>
      </div>
    </modal>

  </div>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'

// Attachments travel inline as base64 — keep them reasonably small
const MAX_ATTACHMENT_SIZE_MB = 50

const DEFAULT_NEW_TASK = () => ({
  name: '',
  mode: 'chat',
  status: 'todo',
  parentId: null,
  selectedProfiles: [],
  llm_model: null,
  project_id: null,
  users: [],
  deadline: null,
  estimation_cost: null,
  // Files referenced from the message (dropped on the composer or @filename)
  files: [],
  attachments: []
})

export default {
  name: 'SprintBoardModals',
  props: {
    sprintId: { type: String, default: null },
    sprintTitle: { type: String, default: 'Sprint' }
  },
  emits: ['task-created', 'tasks-added'],
  data() {
    return {
      showNewTask: false,
      showAddExisting: false,
      newTask: DEFAULT_NEW_TASK(),
      candidateSearch: '',
      selected: [],
      // Mirror of the composer text so the "Run" button knows when there is
      // content. Kept in sync through `update:cursor-word`, which the composer
      // emits on every keystroke (no extra events needed).
      composerText: '',
      cursorWord: {},
      creating: false,
      // ── @-mention file intellisense (same shape as the chat composer) ──
      intelliSenseSuggestions: [],
      intelliSenseIndex: 0,
      intelliSenseQuery: '',
      intelliSenseProgress: '',
      intelliSenseDebounce: null,
      intelliSenseDismissed: false,
      searchController: null,
      previousQuery: null
    }
  },
  mounted() {
    // Users are needed by the assignee picker
    if (!this.$storex.users.users?.length) {
      this.$storex.users.loadUsers().catch(() => {})
    }
  },
  unmounted() {
    clearTimeout(this.intelliSenseDebounce)
    this.cancelIntelliSense()
  },
  computed: {
    allChats() {
      return Object.values(this.$storex.chats.chats || {})
    },
    // Chats not already in this sprint (and not templates / channels)
    candidateTasks() {
      const q = this.candidateSearch?.trim().toLowerCase()
      return this.allChats
        .filter(c => c?.id && !c.is_template && c.mode !== 'channel')
        .filter(c => !(c.sprints || []).includes(this.sprintId))
        .filter(c => !q || (c.name || '').toLowerCase().includes(q))
        .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    },
    // Children of the parent task that have NOT been added to this sprint
    parentChildren() {
      const parentId = this.newTask.parentId
      if (!parentId) return []
      return this.allChats
        .filter(c => c?.id && c.parent_id === parentId)
        .filter(c => !(c.sprints || []).includes(this.sprintId))
        .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    },
    parentName() {
      if (!this.newTask.parentId) return null
      return this.$storex.chats.chats?.[this.newTask.parentId]?.name || null
    },
    // Column (status) the new task will be created in — resolved from the
    // canonical status config so the label/colour always match the board.
    newTaskStatus() {
      return this.$storex.chats.statusConfig(this.newTask.status)
    },

    // Currently selected project (null ⇒ ProjectDetailt falls back to $project)
    selectedProject() {
      const id = this.newTask.project_id
      if (!id) return null
      return this.$storex.projects.allProjectsById?.[id] || null
    },
    // Project the composer works against — same resolution as the chat composer
    chatProject() {
      return this.$storex.projects.allProjectsById?.[this.newTask.project_id] || this.$project
    },
    // Profiles & models come from the same sources as the chat composer
    profiles() {
      return this.chatProject?.$state?.profiles || []
    },
    aiModels() {
      return this.$storex.projects.ai.models || []
    },
    // The composer toolbar selects profiles as items, the task stores their names
    selectedProfiles() {
      return this.profiles.filter(p => this.newTask.selectedProfiles.includes(p.name))
    },
    // Files a task can run with: dropped paths + @file references in the message
    composerFiles() {
      return this.resolveFiles(this.composerText)
    },
    // A task can only be run when it carries an initial prompt / file / image
    hasInitialContent() {
      return !!(this.composerText?.trim() || this.composerFiles.length || this.newTask.attachments.length)
    },
    // Users available for assignment
    allUsers() {
      return this.$storex.users.users || []
    },
    selectedUsers() {
      return this.newTask.users.map(name =>
        this.allUsers.find(u => u.username === name) || { username: name, avatar: null }
      )
    }
  },
  watch: {
    // The composer selectors follow the project picked in the dialog
    chatProject(project) {
      if (project && this.showNewTask) this.initComposerProject()
    },
    // Every composer keystroke refreshes the @-mention search
    composerText() {
      this.scheduleIntelliSense()
    }
  },
  methods: {
    statusIcon(status) {
      return this.$storex.chats.statusIcon(status)
    },
    statusLabel(status) {
      return this.$storex.chats.statusLabel(status)
    },
    initial(user) {
      return (user.username || user.name || '?')[0].toUpperCase()
    },
    // Normalize the cost budget draft to a positive number or null (no budget)
    normalizeCost(value) {
      const num = Number(value)
      if (value === '' || value === null || value === undefined || Number.isNaN(num) || num <= 0) {
        return null
      }
      return num
    },
    fileName(path) {
      return path?.split('/').reverse()[0] || path
    },

    // ── Initial message: composer wiring ─────────────────────────────────────
    // The chat composer needs the project's profiles and models to render its
    // selectors — initialize the project exactly like the chat does.
    async initComposerProject() {
      const project = this.chatProject
      if (!project) return
      try {
        await this.$storex.projects.initProjectState(project)
      } catch (error) {
        console.error('[SprintBoardModals] Could not initialize the composer project:', error)
      }
    },
    onCursorWord(wordInfo) {
      this.cursorWord = wordInfo || {}
      this.composerText = this.$refs.composer?.getEditorText() || ''
    },
    onModelChanged(modelName) {
      this.newTask.llm_model = modelName || null
    },
    onProfilesSelected(profiles) {
      this.newTask.selectedProfiles = (profiles || []).map(p => p.name || p)
    },
    // Keys while the mention list is open navigate it; otherwise Ctrl/Cmd+Enter
    // runs the task right away, like the chat composer.
    onComposerKeyDown(event) {
      const hasSuggestions = this.intelliSenseSuggestions.length > 0
      if (hasSuggestions) {
        if (event.key === 'Tab') {
          event.preventDefault(); event.stopPropagation()
          this.onIntelliSenseSelect(this.intelliSenseSuggestions[this.intelliSenseIndex])
          return
        }
        if (event.key === 'Escape') { this.dismissIntelliSense(); return }
        if (event.key === ' ' && event.ctrlKey) {
          event.preventDefault(); event.stopPropagation()
          this.$refs.intelliSense?.toggleSelected(this.intelliSenseSuggestions[this.intelliSenseIndex])
          return
        }
        if (event.key === 'ArrowUp') {
          event.preventDefault()
          this.intelliSenseIndex = Math.max(0, this.intelliSenseIndex - 1)
          return
        }
        if (event.key === 'ArrowDown') {
          event.preventDefault()
          this.intelliSenseIndex = Math.min(this.intelliSenseSuggestions.length - 1, this.intelliSenseIndex + 1)
          return
        }
      }
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey) && !event.shiftKey) {
        event.preventDefault()
        event.stopPropagation()
        this.runNewTask()
      }
    },

    // ── Initial message: file intellisense (@mentions) ───────────────────────
    // Mirrors the chat composer: typing `@` + 3 chars opens the mention search
    // so the user can pick project files to attach to the task.
    scheduleIntelliSense(word = null) {
      if (this.intelliSenseDismissed) {
        const currentWord = word || this.cursorWord.word
        if (currentWord !== this.intelliSenseQuery) this.intelliSenseDismissed = false
      }
      clearTimeout(this.intelliSenseDebounce)
      this.intelliSenseDebounce = setTimeout(() => this.runIntelliSense(word), 220)
    },
    async runIntelliSense(word = null) {
      if (this.intelliSenseDismissed) return
      const searchWord = word || this.cursorWord.word
      if (!searchWord?.startsWith('@')) { this.cancelIntelliSense(); return }
      const rawQuery = searchWord.slice(1)
      if (!rawQuery || rawQuery.trim().length < 3) { this.cancelIntelliSense(); return }
      if (this.previousQuery !== rawQuery && this.searchController) this.cancelIntelliSense()
      this.previousQuery = rawQuery
      this.searchController = await this.$storex.projects.createSearchController()
      this.intelliSenseQuery = rawQuery
      this.intelliSenseIndex = 0
      this.searchController.onProgress = ({ stage, project }) => {
        this.intelliSenseProgress = `${stage}: ${project}`
      }
      try {
        await this.chatProject?.$state?.searchMentions?.({
          query: rawQuery,
          limit: 10,
          controller: this.searchController,
          onResults: (results) => {
            if (!this.searchController?.isCancelled) {
              if (results.length === 1 && results[0].name === rawQuery) {
                this.onIntelliSenseSelect(results[0])
              } else {
                this.intelliSenseSuggestions = results
                this.intelliSenseIndex = 0
              }
            }
          }
        })
      } catch (error) {
        if (error.message !== 'Search cancelled') console.error('[IntelliSense] Search error:', error)
      }
      this.intelliSenseProgress = ''
    },
    cancelIntelliSense() {
      if (this.searchController) { this.searchController.cancel(); this.searchController = null }
      this.intelliSenseSuggestions = []
      this.intelliSenseQuery = ''
      this.previousQuery = null
    },
    onIntelliSenseSelect(suggestion) {
      const { file, name } = suggestion
      const { caretIndex, word } = this.cursorWord
      const text = this.$refs.composer?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      let insert = '@' + name
      // Files are attached to the task instead of inserted as a mention
      if (file) {
        this.addProjectFile(file)
        insert = ''
      }
      this.setComposerText(left + insert + ' ' + right)
      this.dismissIntelliSense()
      this.$nextTick(() => this.$refs.composer?.focusEditor())
    },
    onIntelliSenseAcceptMulti(items) {
      const { caretIndex, word } = this.cursorWord
      const text = this.$refs.composer?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      const mentionInserts = []
      items.forEach(({ file, name }) => {
        if (file) {
          this.addProjectFile(file)
        } else {
          mentionInserts.push('@' + name)
        }
      })
      const insert = mentionInserts.join(' ')
      this.setComposerText(left + insert + (insert ? ' ' : '') + right)
      this.dismissIntelliSense()
      this.$nextTick(() => this.$refs.composer?.focusEditor())
    },
    dismissIntelliSense() {
      this.intelliSenseDismissed = true
    },

    // ── Initial message: attachments ─────────────────────────────────────────
    async onUploadFiles(files) {
      await this.addAttachments(files)
    },
    async onComposerPaste(event) {
      const imageFile = await this.$service.chat.parseImageFromPaste(event)
      if (!imageFile) return
      event.preventDefault()
      await this.addAttachments([imageFile])
    },
    async onComposerDrop(event) {
      const files = Array.from(event.dataTransfer?.files || [])
      if (files.length) await this.addAttachments(files)
      this.addProjectFilesFromDrop(event.dataTransfer)
    },
    async addAttachments(files) {
      for (const file of files || []) {
        const attachment = await this.prepareAttachment(file)
        if (attachment) this.newTask.attachments.push(attachment)
      }
    },
    async prepareAttachment(file) {
      if ((file?.size || 0) > MAX_ATTACHMENT_SIZE_MB * 1024 * 1024) {
        this.$ui?.addNotification?.({
          text: `File exceeds maximum size of ${MAX_ATTACHMENT_SIZE_MB}MB`,
          type: 'error'
        })
        return null
      }
      try {
        return await ChatAttachment.fromFile(file)
      } catch (error) {
        console.error('[SprintBoardModals] Failed to process attachment:', error)
        this.$ui?.addNotification?.({ text: 'Failed to process file', type: 'error' })
        return null
      }
    },
    removeAttachment(index) {
      this.newTask.attachments.splice(index, 1)
    },

    // ── Initial message: project files ───────────────────────────────────────
    // Files referenced from the message as `@file.py`, resolved against the
    // project file list (the same list the chat mention list is built from).
    resolveMentionedFiles(text) {
      const available = this.chatProject?.$state?.files || []
      const tokens = [...(text || '').matchAll(/@([^\s]+)/g)].map(m => m[1])
      if (!tokens.length) return []
      return available.filter(file =>
        tokens.includes(this.fileName(file)) || tokens.includes(file)
      )
    },
    resolveFiles(text) {
      return [...new Set([...this.newTask.files, ...this.resolveMentionedFiles(text)])]
    },
    isProjectFile(path) {
      return !!this.$storex.projects.allProjects.find(p => path?.startsWith(p.abs_project_path))
    },
    addProjectFile(file) {
      const path = file?.trim()
      if (!path || this.newTask.files.includes(path)) return
      this.newTask.files.push(path)
    },
    // A project file dropped on the composer behaves like in the chat: it is
    // attached to the message instead of being uploaded.
    addProjectFilesFromDrop(dataTransfer) {
      if (!dataTransfer) return
      const candidates = []
      const plain = dataTransfer.getData('text/plain')
      if (plain) candidates.push(...decodeURIComponent(plain).split('\n'))
      const urls = dataTransfer.getData('resourceurls')
      if (urls) {
        try {
          JSON.parse(urls).forEach(url => candidates.push(new URL(url).pathname))
        } catch (error) {
          console.error('[SprintBoardModals] Invalid dropped url list:', error)
        }
      }
      const jsonFiles = dataTransfer.getData('application/x-file-list-json')
      if (jsonFiles) {
        try {
          (JSON.parse(jsonFiles).files || []).forEach(f => { if (!f.is_dir) candidates.push(f.path) })
        } catch (error) {
          console.error('[SprintBoardModals] Invalid dropped file list:', error)
        }
      }
      candidates
        .map(path => path?.trim())
        .filter(path => path && this.isProjectFile(path))
        .forEach(path => this.addProjectFile(path))
    },
    removeComposerFile(file) {
      this.newTask.files = this.newTask.files.filter(f => f !== file)
      // The file may also be referenced from the message — drop the reference too
      const name = this.fileName(file)
      const text = this.$refs.composer?.getEditorText() || ''
      if (text.includes(`@${name}`)) {
        this.setComposerText(text.split(`@${name}`).join(''))
      }
    },
    setComposerText(text) {
      this.$refs.composer?.setEditorText(text || '')
      this.composerText = text || ''
      this.cursorWord = this.$refs.composer?.getCaretWordInfo() ?? {}
    },

    // ── New Task / Subtask ───────────────────────────────────────────────────
    // `status` is the target column, forwarded by the board (a column's "+"
    // button passes its own status). Falls back to the default column.
    openNewTask({ parentId, status } = {}) {
      // A subtask inherits its parent's project by default
      const parent = parentId ? this.$storex.chats.chats?.[parentId] : null
      this.newTask = {
        ...DEFAULT_NEW_TASK(),
        parentId: parentId || null,
        status: status || 'todo',
        project_id: parent?.project_id || null
      }
      this.composerText = ''
      this.cursorWord = {}
      this.intelliSenseDismissed = false
      this.cancelIntelliSense()
      this.showNewTask = true
      this.initComposerProject()
      this.$nextTick(() => {
        this.$refs.composer?.setEditorText('')
        this.$refs.taskNameInput?.focus()
      })
    },
    closeNewTask() {
      this.showNewTask = false
      this.composerText = ''
      clearTimeout(this.intelliSenseDebounce)
      this.cancelIntelliSense()
      this.$refs.composer?.setEditorText('')
    },
    addNewTask() {
      return this.submitNewTask(false)
    },
    runNewTask() {
      return this.submitNewTask(true)
    },
    // Create the task, optionally seeding it with the initial message (text,
    // files and attachments) and (when `run` is set) processing it immediately.
    submitNewTask(run) {
      if (!this.newTask.name?.trim() || this.creating) return
      const message = (this.$refs.composer?.getEditorText() || '').trim()
      const files = this.resolveFiles(message)
      const attachments = this.newTask.attachments.map(a => a.toJSON?.() || a)
      const hasContent = !!(message || files.length || attachments.length)
      this.creating = true
      try {
        this.$emit('task-created', {
          name: this.newTask.name.trim(),
          mode: this.newTask.mode,
          status: this.newTask.status || 'todo',
          parentId: this.newTask.parentId || null,
          profiles: [...this.newTask.selectedProfiles],
          llm_model: this.newTask.llm_model || null,
          project_id: this.newTask.project_id || null,
          users: [...this.newTask.users],
          deadline: this.newTask.deadline || null,
          estimation_cost: this.normalizeCost(this.newTask.estimation_cost),
          message,
          files,
          attachments,
          // Run is only meaningful when there is something to send
          run: !!run && hasContent
        })
        this.closeNewTask()
      } finally {
        this.creating = false
      }
    },
    // Selecting an existing child adds it to this sprint and closes the dialog
    selectParentChild(child) {
      if (!child?.id) return
      this.$emit('tasks-added', { taskIds: [child.id] })
      this.closeNewTask()
    },
    // `ProjectDetailt` is a v-model component: the selection is delivered through
    // `update:modelValue` (its canonical event). `@select` is kept as a legacy
    // fallback. Native events that fall through to the root element carry no
    // project id and are ignored.
    onProjectSelected(project) {
      const id = typeof project === 'string'
        ? project
        : (project?.project_id || project?.id || null)
      if (!id) return
      this.newTask.project_id = id
    },
    setDeadline(preset) {
      const date = new Date()
      if (preset === 'tomorrow') date.setDate(date.getDate() + 1)
      if (preset === 'week') date.setDate(date.getDate() + 7)
      // Local YYYY-MM-DD so the native date input reflects the right day
      const iso = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
        .toISOString()
        .split('T')[0]
      this.newTask.deadline = iso
    },

    // ── Add existing ─────────────────────────────────────────────────────────
    openAddExisting() {
      this.selected = []
      this.candidateSearch = ''
      this.showAddExisting = true
    },
    closeAddExisting() {
      this.showAddExisting = false
    },
    confirmAddExisting() {
      if (!this.selected.length) return
      this.$emit('tasks-added', { taskIds: [...this.selected] })
      this.closeAddExisting()
    }
  }
}
</script>