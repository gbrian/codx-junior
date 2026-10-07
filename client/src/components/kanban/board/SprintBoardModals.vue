<script setup>
import ChatProfileSelector from '../../chat/ChatProfileSelector.vue'
import ChatLLMModelSelector from '../../chat/ChatLLMModelSelector.vue'
import ChatCostSelector from '../../chat/ChatCostSelector.vue'
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

        <!-- Task name -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Task name</span>
          </label>
          <input
            ref="taskNameInput"
            v-model="newTask.name"
            type="text"
            placeholder="Describe what needs to be done…"
            class="input input-bordered input-sm w-full"
            @keydown.enter="confirmNewTask"
          />
        </div>

        <!-- Mode selector -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Type</span>
          </label>
          <div class="flex gap-2">
            <label
              v-for="mode in taskModes"
              :key="mode.value"
              class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border cursor-pointer transition-all text-xs"
              :class="newTask.mode === mode.value
                ? 'border-primary/40 bg-primary/10 text-primary'
                : 'border-base-100 text-base-content/50 hover:border-base-content/20'"
            >
              <input type="radio" :value="mode.value" v-model="newTask.mode" class="hidden" />
              <i :class="mode.icon + ' text-xs'"></i>
              {{ mode.label }}
            </label>
          </div>
        </div>

        <!-- Project -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Project</span>
          </label>
          <ProjectDetailt
            :model-value="selectedProject"
            @select="onProjectSelected"
          />
          <span class="text-[10px] text-base-content/40 mt-1">
            Defaults to the current project. Pick another to run this task against a different codebase.
          </span>
        </div>

        <!-- Profiles & Model -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Profiles & Model</span>
          </label>
          <div class="flex flex-wrap gap-2 items-center">
            <ChatProfileSelector
              :selected-profiles="newTask.selectedProfiles"
              @profiles-changed="onProfilesChanged"
            />
            <ChatLLMModelSelector
              :selected-model="newTask.llm_model"
              @model-changed="onModelChanged"
            />
          </div>

          <!-- Recent profiles quick picker -->
          <div v-if="recentProfiles.length" class="flex items-center gap-2 mt-2">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40 shrink-0">Recent</span>
            <div class="flex items-center gap-1.5 flex-wrap">
              <button
                v-for="p in recentProfiles"
                :key="p.name"
                type="button"
                class="avatar tooltip"
                :data-tip="p.name"
                :aria-label="`Toggle profile ${p.name}`"
                :aria-pressed="isRecentProfileSelected(p)"
                @click="toggleRecentProfile(p)"
              >
                <div
                  class="w-7 h-7 rounded-full ring-2 transition-all"
                  :class="isRecentProfileSelected(p)
                    ? 'ring-primary'
                    : 'ring-transparent opacity-60 hover:opacity-100'"
                >
                  <img :src="recentProfileAvatar(p)" :alt="p.name" />
                </div>
              </button>
            </div>
          </div>

          <div v-if="newTask.selectedProfiles.length" class="flex flex-wrap gap-1 mt-2">
            <span
              v-for="p in newTask.selectedProfiles"
              :key="p.name"
              class="badge badge-sm badge-primary gap-1"
            >
              <i class="fa-solid fa-user text-xs"></i>
              {{ p.name }}
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
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost btn-sm" @click="closeNewTask">Cancel</button>
          <button
            class="btn btn-primary btn-sm gap-1.5"
            @click="confirmNewTask"
            :disabled="!newTask.name?.trim()"
          >
            <i class="fa-solid fa-plus text-xs"></i> Create
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
const TASK_MODES = [
  { value: 'chat',    label: 'Chat',       icon: 'fa-solid fa-message' },
  { value: 'task',    label: 'Document',   icon: 'fa-solid fa-file-lines' },
  { value: 'topic',   label: 'Discussion', icon: 'fa-solid fa-comments' },
]

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
  estimation_cost: null
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
      taskModes: TASK_MODES
    }
  },
  mounted() {
    // Users are needed by the assignee picker
    if (!this.$storex.users.users?.length) {
      this.$storex.users.loadUsers().catch(() => {})
    }
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
    // Users available for assignment
    allUsers() {
      return this.$storex.users.users || []
    },
    selectedUsers() {
      return this.newTask.users.map(name =>
        this.allUsers.find(u => u.username === name) || { username: name, avatar: null }
      )
    },
    // Profiles used by the most recently updated tasks → quick picker
    recentProfiles() {
      const chats = [...(this.$storex.chats.allChats || [])]
        .sort((a, b) => (a.updated_at || '') < (b.updated_at || '') ? 1 : -1)

      const names = []
      for (const chat of chats) {
        for (const name of (chat.profiles || [])) {
          if (!names.includes(name)) names.push(name)
        }
        if (names.length >= 8) break
      }

      const available = this.$storex.projects.profiles || []
      return names.slice(0, 8)
        .map(name => available.find(p => p.name === name) || { name })
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
      this.showNewTask = true
      this.$nextTick(() => this.$refs.taskNameInput?.focus())
    },
    closeNewTask() {
      this.showNewTask = false
    },
    confirmNewTask() {
      if (!this.newTask.name?.trim()) return
      this.$emit('task-created', {
        name: this.newTask.name.trim(),
        mode: this.newTask.mode,
        status: this.newTask.status || 'todo',
        parentId: this.newTask.parentId || null,
        profiles: this.newTask.selectedProfiles.map(p => p.name),
        llm_model: this.newTask.llm_model || null,
        project_id: this.newTask.project_id || null,
        users: [...this.newTask.users],
        deadline: this.newTask.deadline || null,
        estimation_cost: this.normalizeCost(this.newTask.estimation_cost)
      })
      this.closeNewTask()
    },
    // Selecting an existing child adds it to this sprint and closes the dialog
    selectParentChild(child) {
      if (!child?.id) return
      this.$emit('tasks-added', { taskIds: [child.id] })
      this.closeNewTask()
    },
    onProfilesChanged(profiles) {
      this.newTask.selectedProfiles = profiles || []
    },
    onModelChanged(modelName) {
      this.newTask.llm_model = modelName || null
    },
    onProjectSelected(project) {
      this.newTask.project_id = project?.project_id || null
    },
    isRecentProfileSelected(profile) {
      return this.newTask.selectedProfiles.some(p => p.name === profile.name)
    },
    toggleRecentProfile(profile) {
      const ix = this.newTask.selectedProfiles.findIndex(p => p.name === profile.name)
      if (ix > -1) {
        this.newTask.selectedProfiles.splice(ix, 1)
      } else {
        this.newTask.selectedProfiles.push(profile)
      }
    },
    recentProfileAvatar(profile) {
      return profile.avatar ||
        `https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=200&d=robohash&r=${profile.name}`
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