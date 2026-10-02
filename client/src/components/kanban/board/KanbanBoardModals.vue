<script setup>
</script>

<template>
  <div class="kanban-board-modals">

    <!-- ── New Task Modal ── -->
    <modal close="true" @close="closeNewTask" v-if="showNewTask">
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

        <!-- Column selector -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Column</span>
          </label>
          <div class="flex flex-col gap-1.5">
            <label
              v-for="col in columns"
              :key="col.id || col.title"
              class="flex items-center gap-2.5 px-2 py-1.5 rounded-lg border cursor-pointer transition-all duration-150"
              :class="newTask.column === col.title
                ? 'border-primary/40 bg-primary/10'
                : 'border-base-100 hover:border-base-content/20'"
            >
              <input
                type="radio"
                :value="col.title"
                v-model="newTask.column"
                class="radio radio-xs radio-primary"
              />
              <span
                class="w-2 h-2 rounded-full shrink-0"
                :style="col.color ? `background: ${col.color}` : ''"
                :class="!col.color ? 'bg-base-content/20' : ''"
              ></span>
              <span class="text-sm text-base-content/80">{{ col.title }}</span>
            </label>
            <div v-if="!columns.length" class="text-xs text-base-content/30 px-2 py-1 italic">
              No columns yet — task will be added uncategorized
            </div>
          </div>
        </div>

        <!-- Mode selector -->
        <div class="form-control mb-4">
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

        <!-- Subtask info note -->
        <div
          v-if="newTask.parentId"
          class="flex gap-2 items-start p-2.5 rounded-lg bg-primary/5 border border-primary/15 mb-4"
        >
          <i class="fa-solid fa-circle-info text-primary text-xs mt-0.5 shrink-0"></i>
          <span class="text-xs text-base-content/50">
            Subtasks appear as independent cards in the board. No nested hierarchy is shown in the canvas.
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

    <!-- ── New / Edit Column Modal ── -->
    <modal close="true" @close="closeNewColumn" v-if="showNewColumn">
      <div class="p-1">
        <h2 class="font-bold text-base mb-4 flex items-center gap-2">
          <i class="fa-solid fa-table-columns text-primary text-sm"></i>
          {{ editingColumn ? 'Edit Column' : 'New Column' }}
        </h2>

        <!-- Column name -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Column name</span>
          </label>
          <input
            ref="colNameInput"
            v-model="newColumn.title"
            type="text"
            placeholder="e.g. Review, Blocked, Testing…"
            class="input input-bordered input-sm w-full"
            @keydown.enter="confirmNewColumn"
          />
          <label class="label py-0.5" v-if="columnError">
            <span class="label-text-alt text-error">{{ columnError }}</span>
          </label>
        </div>

        <!-- Color picker -->
        <div class="form-control mb-4">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Color</span>
          </label>
          <div class="flex gap-2.5 flex-wrap">
            <span
              v-for="color in columnColors"
              :key="color"
              @click="newColumn.color = color"
              class="w-6 h-6 rounded-full cursor-pointer transition-transform hover:scale-110"
              :style="`background: ${color}`"
              :class="newColumn.color === color ? 'ring-2 ring-offset-2 ring-base-content/50' : ''"
            ></span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost btn-sm" @click="closeNewColumn">Cancel</button>
          <button
            class="btn btn-primary btn-sm gap-1.5"
            @click="confirmNewColumn"
            :disabled="!newColumn.title?.trim()"
          >
            <i class="fa-solid fa-check text-xs"></i>
            {{ editingColumn ? 'Save' : 'Create' }}
          </button>
        </div>
      </div>
    </modal>

    <!-- ── New Board Modal ── -->
    <modal close="true" @close="closeNewBoard" v-if="showNewBoard">
      <div class="p-1">
        <h2 class="font-bold text-base mb-4 flex items-center gap-2">
          <i class="fa-brands fa-trello text-primary text-sm"></i>
          New Board
        </h2>

        <!-- Board name -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">Board name</span>
          </label>
          <input
            ref="boardNameInput"
            v-model="newBoard.title"
            type="text"
            placeholder="e.g. Sprint Q4, Roadmap 2026…"
            class="input input-bordered input-sm w-full"
            @keydown.enter="confirmNewBoard"
          />
        </div>

        <!-- Description -->
        <div class="form-control mb-4">
          <label class="label py-1">
            <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">
              Description <span class="normal-case font-normal opacity-50">(optional)</span>
            </span>
          </label>
          <textarea
            v-model="newBoard.description"
            rows="2"
            placeholder="What is this board for?"
            class="textarea textarea-bordered textarea-sm w-full resize-none"
          ></textarea>
        </div>

        <!-- Actions -->
        <div class="flex gap-2 justify-end">
          <button class="btn btn-ghost btn-sm" @click="closeNewBoard">Cancel</button>
          <button
            class="btn btn-primary btn-sm gap-1.5"
            @click="confirmNewBoard"
            :disabled="!newBoard.title?.trim()"
          >
            <i class="fa-solid fa-plus text-xs"></i> Create Board
          </button>
        </div>
      </div>
    </modal>

  </div>
</template>

<script>
const COLUMN_COLORS = [
  '#6366f1', '#f59e0b', '#10b981', '#ef4444',
  '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'
]

const TASK_MODES = [
  { value: 'chat',    label: 'Chat',       icon: 'fa-solid fa-message' },
  { value: 'task',    label: 'Document',   icon: 'fa-solid fa-file-lines' },
  { value: 'topic',   label: 'Discussion', icon: 'fa-solid fa-comments' },
]

export default {
  props: {
    columns: { type: Array, default: () => [] },
    boards: { type: Array, default: () => [] },
    editingColumn: { type: Object, default: null }
  },
  emits: ['task-created', 'column-created', 'column-updated', 'board-created'],
  data() {
    return {
      showNewTask: false,
      showNewColumn: false,
      showNewBoard: false,
      newTask: { name: '', column: '', mode: 'chat', parentId: null },
      newColumn: { title: '', color: '#6366f1' },
      newBoard: { title: '', description: '' },
      columnError: null,
      columnColors: COLUMN_COLORS,
      taskModes: TASK_MODES
    }
  },
  watch: {
    editingColumn(col) {
      if (col) {
        this.newColumn = { title: col.title, color: col.color || '#6366f1', id: col.id }
      }
    }
  },
  methods: {
    // ── New Task ──────────────────────────────────────────────────────────────
    openNewTask({ column, parentId } = {}) {
      this.newTask = {
        name: '',
        column: column || this.columns[0]?.title || '',
        mode: 'chat',
        parentId: parentId || null
      }
      this.showNewTask = true
      this.$nextTick(() => this.$refs.taskNameInput?.focus())
    },
    closeNewTask() {
      this.showNewTask = false
    },
    confirmNewTask() {
      if (!this.newTask.name?.trim()) return
      this.$emit('task-created', { ...this.newTask })
      this.closeNewTask()
    },

    // ── New Column ────────────────────────────────────────────────────────────
    openNewColumn() {
      if (this.editingColumn) {
        this.newColumn = {
          id: this.editingColumn.id,
          title: this.editingColumn.title,
          color: this.editingColumn.color || '#6366f1'
        }
      } else {
        this.newColumn = { title: '', color: '#6366f1' }
      }
      this.columnError = null
      this.showNewColumn = true
      this.$nextTick(() => this.$refs.colNameInput?.focus())
    },
    closeNewColumn() {
      this.showNewColumn = false
      this.columnError = null
    },
    confirmNewColumn() {
      const title = this.newColumn.title?.trim()
      if (!title) return

      const duplicate = this.columns.find(
        c => c.title === title && c.id !== this.newColumn.id
      )
      if (duplicate) {
        this.columnError = 'A column with this name already exists'
        return
      }

      if (this.editingColumn) {
        this.$emit('column-updated', { ...this.newColumn, title })
      } else {
        this.$emit('column-created', { title, color: this.newColumn.color })
      }
      this.closeNewColumn()
    },

    // ── New Board ─────────────────────────────────────────────────────────────
    openNewBoard() {
      this.newBoard = { title: '', description: '' }
      this.showNewBoard = true
      this.$nextTick(() => this.$refs.boardNameInput?.focus())
    },
    closeNewBoard() {
      this.showNewBoard = false
    },
    confirmNewBoard() {
      if (!this.newBoard.title?.trim()) return
      this.$emit('board-created', { ...this.newBoard })
      this.closeNewBoard()
    }
  }
}
</script>