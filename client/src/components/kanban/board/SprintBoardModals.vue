<script setup>
import ChatProfileSelector from '../../chat/ChatProfileSelector.vue'
import ChatLLMModelSelector from '../../chat/ChatLLMModelSelector.vue'
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

        <!-- Profiles & Model -->
        <div class="form-control mb-4">
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

        <!-- Context note -->
        <div class="flex gap-2 items-start p-2.5 rounded-lg bg-info/5 border border-info/15 mb-4">
          <i class="fa-solid fa-circle-info text-info text-xs mt-0.5 shrink-0"></i>
          <span class="text-xs text-base-content/50">
            <template v-if="newTask.parentId">
              Subtask of <b>{{ parentName || 'parent task' }}</b>. It is linked to its parent and added to
              <b>{{ sprintTitle }}</b> in the <span class="text-info">To Do</span> column.
            </template>
            <template v-else>
              The task is added to <b>{{ sprintTitle }}</b> and starts in the
              <span class="text-info">To Do</span> column.
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
  parentId: null,
  selectedProfiles: [],
  llm_model: null
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
    parentName() {
      if (!this.newTask.parentId) return null
      return this.$storex.chats.chats?.[this.newTask.parentId]?.name || null
    }
  },
  methods: {
    statusIcon(status) {
      return this.$storex.chats.statusIcon(status)
    },
    statusLabel(status) {
      return this.$storex.chats.statusLabel(status)
    },

    // ── New Task / Subtask ───────────────────────────────────────────────────
    openNewTask({ parentId } = {}) {
      this.newTask = { ...DEFAULT_NEW_TASK(), parentId: parentId || null }
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
        status: 'todo',
        parentId: this.newTask.parentId || null,
        profiles: this.newTask.selectedProfiles.map(p => p.name),
        llm_model: this.newTask.llm_model || null
      })
      this.closeNewTask()
    },
    onProfilesChanged(profiles) {
      this.newTask.selectedProfiles = profiles || []
    },
    onModelChanged(modelName) {
      this.newTask.llm_model = modelName || null
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