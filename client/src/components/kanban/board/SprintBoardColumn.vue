<script setup>
import SprintTaskCard from './SprintTaskCard.vue'
</script>

<template>
  <!--
    Shared board column. Serves both:
      • Sprint status columns (column.status / icon / borderColor / textColor)
      • Kanban custom columns  (column.title / color, editable, reorderable)
    The sprint implementation (latest behaviour) is the base; kanban-only
    affordances are opt-in through props.
  -->
  <div
    class="kanban-board-column flex flex-col rounded-xl border-1 border-base-content/30 w-64 shrink-0 self-start max-h-full transition-colors duration-150"
    :class="columnClasses"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- Column header (drag handle for column reordering when `draggable`) -->
    <div
      class="flex items-center gap-2 px-3 py-2.5 border-b border-base-100 shrink-0"
      :class="[
        column.borderColor ? `border-l-4 rounded-tl-xl ${column.borderColor}` : '',
        draggable ? 'cursor-grab active:cursor-grabbing select-none' : ''
      ]"
      :draggable="draggable"
      @dragstart="draggable ? onColumnDragStart($event) : null"
      @dragend="draggable ? $emit('column-drag-end') : null"
    >
      <i v-if="draggable" class="fa-solid fa-grip-vertical text-xs text-base-content/20 shrink-0"></i>

      <!--
        Column icon — a single rendering for every column: a circle filled with
        the column colour and the icon centred inside. Canonical statuses take
        the colour from the status tokens, custom/kanban columns from the colour
        picked in the column dialog (applied inline below). A column without an
        icon keeps its colour dot, centred in the same circle.
      -->
      <span
        class="relative w-5 h-5 rounded-full flex items-center justify-center shrink-0"
        :class="columnBadgeClass"
      >
        <!-- Explicit colour layer (custom/kanban columns) -->
        <span
          v-if="column.color"
          class="absolute inset-0 rounded-full opacity-20"
          :style="{ backgroundColor: column.color }"
        ></span>

        <!-- Column icon, centred -->
        <i
          v-if="column.icon"
          :class="[column.icon, 'relative text-[10px] leading-none']"
          :style="column.color ? { color: column.color } : null"
        ></i>

        <!-- Colour dot, for columns that define no icon -->
        <span
          v-else
          class="relative w-1.5 h-1.5 rounded-full bg-current"
          :style="column.color ? { backgroundColor: column.color } : null"
        ></span>
      </span>

      <!--
        Column defaults shown right after the status icon:
          • the project tasks created in this column are assigned to — only when
            it is different from the active project (a same-project column needs
            no extra signal);
          • the profiles pre-selected on tasks created in this column, rendered
            as a DaisyUI avatar group (no color-only signalling). Each avatar
            renders the profile's `avatar` image URL; the initial is only a
            fallback for profiles without an avatar (or when the image fails to
            load).
      -->
      <div
        v-if="columnProject || columnProfiles.length"
        class="flex items-center gap-1 shrink-0"
      >
        <!-- Project the tasks of this column belong to -->
        <div
          v-if="columnProject"
          class="avatar placeholder tooltip tooltip-bottom"
          :data-tip="columnProjectTitle"
          :title="columnProjectTitle"
          :aria-label="columnProjectTitle"
        >
          <div
            class="w-5 h-5 rounded-full ring-1 ring-base-100 bg-base-300 overflow-hidden flex items-center justify-center"
          >
            <img
              v-if="columnProject.project_icon"
              :src="columnProject.project_icon"
              :alt="columnProject.project_name"
              class="w-full h-full rounded-full object-cover"
            />
            <i v-else class="fa-solid fa-cube text-[9px] leading-none text-base-content/60"></i>
          </div>
        </div>

        <!-- Profiles pre-selected on tasks created in this column -->
        <div
          v-if="columnProfiles.length"
          class="avatar-group -space-x-2 rtl:space-x-reverse shrink-0"
        >
          <div
            v-for="profile in visibleProfiles"
            :key="profile.name"
            class="avatar placeholder tooltip"
            :data-tip="profileTitle(profile)"
            :title="profileTitle(profile)"
          >
            <div
              class="w-5 h-5 rounded-full ring-1 ring-base-100 bg-base-300 overflow-hidden flex items-center justify-center text-[9px] font-medium text-base-content/60"
              :style="profileAvatarStyle(profile)"
            >
              <!-- Profile avatar image URL (falls back to the initial on error) -->
              <img
                v-if="profileAvatar(profile) && !failedAvatars[profile.name]"
                :src="profileAvatar(profile)"
                :alt="profile.name"
                class="w-full h-full rounded-full object-cover"
                @error="onAvatarError(profile.name)"
              />
              <span v-else>{{ initial(profile.name) }}</span>
            </div>
          </div>

          <!-- Overflow: profiles that do not fit in the group -->
          <div
            v-if="overflowProfiles.length"
            class="avatar placeholder tooltip tooltip-bottom"
            :data-tip="overflowProfilesTitle"
          >
            <div
              class="w-5 h-5 rounded-full ring-1 ring-base-100 bg-base-100 flex items-center justify-center text-[9px] font-semibold text-base-content/50"
            >
              <span>+{{ overflowProfiles.length }}</span>
            </div>
          </div>
        </div>
      </div>

      <span class="text-xs text-base-content/30 bg-base-100 rounded-full px-1.5 shrink-0">
        {{ localTasks.length }}
      </span>
      <span class="text-xs font-semibold text-base-content/70 flex-1 truncate">
        {{ column.title }}
      </span>

      <!-- Accumulated cost of the tasks in this column (sprint) -->
      <span
        v-if="totalCost > 0"
        class="flex items-center gap-0.5 text-xs font-semibold text-amber-400 shrink-0 tabular-nums tooltip tooltip-bottom"
        :data-tip="costTooltip"
      >
        <i class="fa-solid fa-coins text-[10px]"></i>{{ formatCoins(totalCost) }}
      </span>

      <button
        v-if="allowCreate"
        @click.stop="$emit('new-task')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-primary"
        title="Add task"
        draggable="false"
      >
        <i class="fa-solid fa-plus text-xs"></i>
      </button>
      <button
        v-if="allowEdit"
        @click.stop="$emit('edit-column')"
        class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/20 hover:text-base-content/60"
        title="Edit column"
        draggable="false"
      >
        <i class="fa-solid fa-ellipsis text-xs"></i>
      </button>
    </div>

    <!--
      Tasks (sortable when `reorderable`). The list is windowed: a column may
      hold hundreds of tasks and only the cards inside the render window are
      mounted, so a board with many tasks stays responsive. The window grows
      while the user scrolls, keeping every rendered card at its real index
      (drag & drop, drop indicators and reordering keep working unchanged).
    -->
    <div
      ref="taskList"
      class="flex flex-col gap-2 p-2 overflow-y-auto flex-1 min-h-0"
      @scroll.passive="onTaskListScroll"
      @dragover.prevent="onTaskListDragOver"
      @drop.prevent="onTaskListDrop"
    >
      <div
        v-for="(task, taskIndex) in visibleTasks"
        :key="task.id"
        class="group relative cursor-pointer"
        :data-task-id="task.id"
        draggable="true"
        @dragstart="onTaskDragStart($event, task, taskIndex)"
        @dragend="onTaskDragEnd"
        @dragover.prevent.stop="onTaskDragOver($event, taskIndex)"
        @drop.prevent.stop="onTaskDrop($event, taskIndex)"
      >
        <!-- Drop indicator above this task (reorder) -->
        <div
          v-if="reorderable && taskDropIndex === taskIndex && draggingTaskIndex !== taskIndex && draggingTaskIndex !== taskIndex - 1"
          class="h-0.5 bg-primary/60 rounded-full mb-1 mx-1"
        ></div>

        <SprintTaskCard
          :task="task"
          :selected="selectedTaskId === task.id"
          :showActions="allowActions"
          class="transition-all duration-150"
          :class="draggingTaskId === task.id ? 'opacity-40' : ''"
          @open="$emit('open-task', task)"
          @open-window="$emit('open-task-window', task)"
          @add-subtask="$emit('add-subtask', task)"
          @remove="$emit('remove-task', task)"
        />
      </div>

      <!--
        Windowing footer: the cards outside the render window mount on demand
        while scrolling. The button is the keyboard-accessible alternative for
        the same action.
      -->
      <div v-if="hiddenTasksCount" class="flex items-center justify-center pt-0.5">
        <button
          class="btn btn-ghost btn-xs gap-1.5 text-base-content/40 hover:text-primary"
          :title="`Show the remaining ${hiddenTasksCount} tasks`"
          @click="renderMore(hiddenTasksCount)"
        >
          <i class="fa-solid fa-chevron-down text-xs"></i>
          <span class="text-xs">{{ hiddenTasksCount }} more</span>
        </button>
      </div>

      <!-- Empty column drop hint -->
      <div
        v-if="!localTasks.length"
        class="flex items-center justify-center h-20 rounded-lg border-2 border-dashed text-xs transition-colors duration-150"
        :class="isDragOver
          ? 'border-primary/50 text-primary/60 bg-primary/5'
          : 'border-base-100 text-base-content/20'"
      >
        {{ isDragOver ? 'Drop here' : 'No tasks' }}
      </div>
    </div>

    <!-- Footer: Add task -->
    <div v-if="allowCreate" class="shrink-0 p-2 border-t border-base-100">
      <button
        @click="$emit('new-task')"
        class="btn btn-ghost btn-xs w-full gap-1.5 text-base-content/30 hover:text-primary border border-dashed border-base-100 hover:border-primary/30 transition-all"
      >
        <i class="fa-solid fa-plus text-xs"></i> Add task
      </button>
    </div>
  </div>
</template>

<script>
// Circle colours of the canonical sprint statuses. They mirror the shared chat
// status config (todo / doing / onhold / done / rejected) so the column badge
// matches the status colours used everywhere else in the app.
const STATUS_BADGE_CLASSES = {
  todo: 'bg-info/20 text-info',
  doing: 'bg-primary/20 text-primary',
  onhold: 'bg-warning/20 text-warning',
  done: 'bg-success/20 text-success',
  rejected: 'bg-error/20 text-error'
}

// Maximum number of profiles rendered before the "+N" overflow avatar
const MAX_VISIBLE_PROFILES = 4

// Windowing of the task list: cards mounted on first paint and cards added per
// scroll step. Keeps the DOM of a column bounded when a board holds hundreds of
// tasks (mounting every card is what makes big boards slow).
const INITIAL_RENDER_TASKS = 20
const RENDER_CHUNK_TASKS = 20
// Distance (px) from the bottom of the list that triggers the next chunk, so
// cards are mounted slightly before they enter the viewport
const SCROLL_LOAD_THRESHOLD_PX = 320

// `profiles.list()` returns the same list for every column of a board, so a
// board with many columns would otherwise fire one request per column. Share
// and cache the lookup (scoped to the project, refreshed after a short time).
const PROFILES_CACHE_MS = 30000
let profilesCache = { key: null, at: 0, promise: null }

export default {
  name: 'SprintBoardColumn',
  props: {
    column: { type: Object, required: true },
    selectedTaskId: { type: String, default: null },
    // Creation affordances (header "+" and footer "Add task")
    allowCreate: { type: Boolean, default: true },
    // Kanban: show the per-column edit (ellipsis) button
    allowEdit: { type: Boolean, default: false },
    // Show the card hover actions (add subtask / remove from sprint)
    allowActions: { type: Boolean, default: true },
    // Kanban: allow within-column task reordering
    reorderable: { type: Boolean, default: false },
    // Kanban: the header acts as a drag handle for column reordering
    draggable: { type: Boolean, default: false },
    // Rendering over a board background image
    hasBackground: { type: Boolean, default: false }
  },
  emits: [
    'open-task', 'open-task-window', 'move-task', 'new-task', 'edit-column',
    'reorder-tasks', 'remove-task', 'add-subtask', 'column-drag-start', 'column-drag-end'
  ],
  data() {
    return {
      isDragOver: false,
      draggingTaskId: null,
      draggingTaskIndex: null,
      taskDropIndex: null,
      localTasks: [],
      // Prevents the store-driven watcher from reverting a local reorder while
      // the save round-trip is in flight
      pendingReorder: false,
      maxVisibleProfiles: MAX_VISIBLE_PROFILES,
      // Profiles whose avatar URL failed to load (falls back to the initial)
      failedAvatars: {},
      columnProfiles: [],
      // Number of tasks currently mounted (the render window). Grows while the
      // user scrolls this column, see `onTaskListScroll`.
      renderLimit: INITIAL_RENDER_TASKS,
      // Scroll handler is throttled through requestAnimationFrame
      scrollTicking: false
    }
  },
  computed: {
    tasks() {
      return this.column.tasks || []
    },
    // The mounted slice of the column. Keeping it a prefix means the rendered
    // tasks keep their real index, so drag & drop / reordering are unaffected.
    visibleTasks() {
      return this.localTasks.slice(0, this.renderLimit)
    },
    hiddenTasksCount() {
      return Math.max(0, this.localTasks.length - this.visibleTasks.length)
    },
    columnClasses() {
      const surface = this.hasBackground
        ? 'border-base-100 bg-base-200/80 backdrop-blur-md shadow-xl'
        : 'border-base-100 bg-base-100'
      return this.isDragOver ? 'border-primary/50 bg-primary/5' : surface
    },
    // Background of the column icon badge. A colour picked for the column is
    // applied inline (tint layer + icon colour, see the template); canonical
    // statuses use the shared status tokens; anything else stays neutral.
    columnBadgeClass() {
      if (this.column.color) return ''
      return STATUS_BADGE_CLASSES[this.column.status] || 'bg-base-content/10 text-base-content/60'
    },
    // Project assigned to the tasks of this column. Surfaced in the header only
    // when it differs from the active project, so a column that works inside the
    // open project adds no extra signal. The column object may carry the
    // resolved project (store getters); otherwise it is looked up by id.
    columnProject() {
      const id = this.column.project_id
      if (!id || id === this.$project?.project_id) return null
      return this.column.project
        || this.$storex.projects.allProjectsById?.[id]
        || { project_id: id }
    },
    columnProjectTitle() {
      const name = this.columnProject?.project_name || this.columnProject?.project_id
      return name ? `Tasks are created in project: ${name}` : ''
    },
    visibleProfiles() {
      return this.columnProfiles.slice(0, this.maxVisibleProfiles)
    },
    overflowProfiles() {
      return this.columnProfiles.slice(this.maxVisibleProfiles)
    },
    overflowProfilesTitle() {
      return this.overflowProfiles.map(p => p.name).join(', ')
    },
    // Names of the profiles pre-selected on this column. Used as the watcher
    // source so the avatars are resolved only when the list really changes.
    profilesSignature() {
      return (this.column.profiles || [])
        .map(entry => (entry && typeof entry === 'object' ? entry.name : entry))
        .join('|')
    },

    // Accumulated cost (cxj) of every task in this column
    totalCost() {
      return this.tasks.reduce((sum, t) => sum + (t.cost || 0), 0)
    },
    // Sum of the per-task budgets, when the tasks define one
    totalBudget() {
      return this.tasks.reduce((sum, t) => sum + (t.estimation_cost || 0), 0)
    },
    costTooltip() {
      const count = this.tasks.length
      const label = `${count} task${count === 1 ? '' : 's'}`
      if (this.totalBudget > 0) {
        return `Accumulated cost: ${this.formatCoins(this.totalCost)} of ${this.formatCoins(this.totalBudget)} cxj (${label})`
      }
      return `Accumulated cost: ${this.formatCoins(this.totalCost)} cxj (${label})`
    }
  },
  watch: {
    tasks: {
      immediate: true,
      handler(newTasks) {
        // Skip sync while actively dragging or while a reorder save is pending
        if (this.draggingTaskIndex !== null || this.pendingReorder) return
        const previousCount = this.localTasks.length
        this.localTasks = [...newTasks]
        this.syncRenderLimit(previousCount, newTasks.length)
        this.$nextTick(this.fillViewport)
      }
    },
    // Column profiles change rarely — resolve their avatars only when the list
    // itself changes instead of on every task update of the column
    profilesSignature: {
      immediate: true,
      handler() {
        this.loadColumnProfiles()
      }
    },
    // A task opened from outside (sidebar, search, another panel) must be part
    // of the render window before it gets highlighted
    selectedTaskId: {
      immediate: true,
      handler(taskId) {
        this.revealTask(taskId)
      }
    }
  },
  mounted() {
    this.$nextTick(this.fillViewport)
  },
  methods: {
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    },

    // ── Task list windowing ─────────────────────────────────────────────────
    // Mount more cards when the user approaches the bottom of the list
    onTaskListScroll(event) {
      const el = event.target
      // The handler reads scrollHeight (layout), so coalesce scroll bursts
      if (this.scrollTicking) return
      this.scrollTicking = true
      requestAnimationFrame(() => {
        this.scrollTicking = false
        this.maybeRenderMore(el)
      })
    },
    maybeRenderMore(el) {
      if (this.renderLimit >= this.localTasks.length) return
      const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - SCROLL_LOAD_THRESHOLD_PX
      if (nearBottom) this.renderMore()
    },
    // Extend the render window (scroll step, footer button)
    renderMore(count = RENDER_CHUNK_TASKS) {
      if (this.renderLimit >= this.localTasks.length) return
      this.renderLimit = Math.min(this.localTasks.length, this.renderLimit + count)
      this.$nextTick(this.fillViewport)
    },
    // Keep the window in sync with the task list: start with the initial chunk,
    // keep it open on store updates and reveal cards appended to the column.
    syncRenderLimit(previousCount, nextCount) {
      const initial = Math.min(INITIAL_RENDER_TASKS, nextCount)
      const added = Math.max(0, nextCount - previousCount)
      // First load — or a different set of tasks (a filter/board was toggled):
      // begin with the initial window instead of mounting the whole column
      if (previousCount === 0 || added > RENDER_CHUNK_TASKS) {
        this.renderLimit = initial
        return
      }
      this.renderLimit = Math.min(nextCount, Math.max(this.renderLimit + added, initial))
    },
    // A short column may not fill its own height, so no scroll event would ever
    // reveal the remaining cards. Grow the window until the list overflows.
    fillViewport() {
      const el = this.$refs.taskList
      if (!el || this.renderLimit >= this.localTasks.length) return
      if (el.scrollHeight > el.clientHeight + 8) return
      this.renderLimit = Math.min(this.localTasks.length, this.renderLimit + RENDER_CHUNK_TASKS)
      this.$nextTick(this.fillViewport)
    },
    // Make sure the given task is mounted (and visible) even when it sits below
    // the current window
    revealTask(taskId) {
      if (!taskId) return
      const index = this.localTasks.findIndex(t => t.id === taskId)
      if (index < 0) return
      if (index >= this.renderLimit) {
        this.renderLimit = Math.min(this.localTasks.length, index + RENDER_CHUNK_TASKS)
      }
      this.$nextTick(() => this.scrollTaskIntoView(taskId))
    },
    scrollTaskIntoView(taskId) {
      const nodes = this.$refs.taskList?.querySelectorAll('[data-task-id]') || []
      const node = Array.from(nodes).find(n => n.dataset.taskId === taskId)
      node?.scrollIntoView({ block: 'nearest' })
    },

    // ── Profile avatars ─────────────────────────────────────────────────────
    // Initial shown when a profile defines no avatar image (or it fails to load)
    initial(name) {
      return (name || '?').trim().charAt(0).toUpperCase() || '?'
    },
    // The profile's avatar image URL (`avatar_url` wins, mirroring ProfileAvatar)
    profileAvatar(profile) {
      return profile?.avatar_url || profile?.avatar || null
    },
    // Broken avatar URL → remember it so the initial is rendered instead
    onAvatarError(name) {
      if (!name) return
      this.failedAvatars = { ...this.failedAvatars, [name]: true }
    },
    // Tooltip: the profile name (falls back gracefully for name-only profiles)
    profileTitle(profile) {
      return profile?.name || ''
    },
    // Tint the initial with the profile colour, when it defines one
    profileAvatarStyle(profile) {
      return profile?.color ? { color: profile.color } : null
    },

    // ── Cross-column move (both boards) ─────────────────────────────────────
    // Emits `{ taskId, toColumn, status }` so the sprint view (status) and the
    // kanban view (toColumn) each pick what they need.
    emitMove(taskId) {
      if (!taskId) return
      this.$emit('move-task', {
        taskId,
        toColumn: this.column.title,
        status: this.column.status || null
      })
    },
    onDragOver(event) {
      // Only react to a task being dragged (kanban sets `taskId`, sprint `sprintTaskId`)
      const types = Array.from(event.dataTransfer.types || [])
      if (types.includes('taskid') || types.includes('sprinttaskid')) {
        event.dataTransfer.dropEffect = 'move'
        this.isDragOver = true
      }
    },
    onDragLeave() {
      this.isDragOver = false
      this.taskDropIndex = null
    },
    onDrop(event) {
      const taskId = this.readTaskId(event)
      const fromColumn = event.dataTransfer.getData('fromColumn')
      this.isDragOver = false
      this.draggingTaskId = null
      this.draggingTaskIndex = null
      this.taskDropIndex = null
      // Same-column drop is a no-op here (handled by the task list reorder)
      if (!taskId || fromColumn === this.column.title) return
      this.emitMove(taskId)
    },

    // ── Column drag (canvas reordering) ─────────────────────────────────────
    onColumnDragStart(event) {
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('columnDrag', this.column.title)
      this.$emit('column-drag-start')
    },

    // ── Task drag: cross-column AND within-column reorder ───────────────────
    onTaskDragStart(event, task, taskIndex) {
      this.draggingTaskId = task.id
      this.draggingTaskIndex = taskIndex
      event.dataTransfer.effectAllowed = 'move'
      // Keys understood by both boards (kanban `taskId`, sprint `sprintTaskId`)
      event.dataTransfer.setData('taskId', task.id)
      event.dataTransfer.setData('sprintTaskId', task.id)
      event.dataTransfer.setData('fromColumn', this.column.title)
      event.dataTransfer.setData('text/plain', task.id)
    },
    onTaskDragEnd() {
      this.draggingTaskId = null
      this.draggingTaskIndex = null
      this.taskDropIndex = null
      this.isDragOver = false
    },
    onTaskDragOver(event, taskIndex) {
      // Only handle if dragging a task from this same column
      if (this.draggingTaskIndex === null) return
      this.taskDropIndex = taskIndex
    },
    onTaskDrop(event, targetIndex) {
      const fromIndex = this.draggingTaskIndex
      if (fromIndex === null) {
        this.onTaskDragEnd()
        return
      }

      // Cross-column drop — let the store move it
      const fromColumn = event.dataTransfer.getData('fromColumn')
      if (fromColumn && fromColumn !== this.column.title) {
        const taskId = this.readTaskId(event)
        this.isDragOver = false
        this.draggingTaskId = null
        this.draggingTaskIndex = null
        this.emitMove(taskId)
        return
      }

      // Same-column reorder — kanban only
      if (!this.reorderable || fromIndex === targetIndex) {
        this.onTaskDragEnd()
        return
      }

      const reordered = [...this.localTasks]
      const [moved] = reordered.splice(fromIndex, 1)
      reordered.splice(targetIndex, 0, moved)
      this.localTasks = reordered

      // Mark pending so the watcher doesn't overwrite localTasks while the
      // async save resolves and triggers a store update
      this.pendingReorder = true
      this.$emit('reorder-tasks', { taskIds: reordered.map(t => t.id) })
      setTimeout(() => { this.pendingReorder = false }, 2000)

      this.onTaskDragEnd()
    },
    onTaskListDragOver() {
      // Dragging over the empty area at the bottom of the task list. With a
      // partially rendered list the real end of the column is not visible, so
      // no end-of-list drop target is offered (dropping on a card still works).
      if (this.draggingTaskIndex === null) return
      if (this.hiddenTasksCount) return
      this.taskDropIndex = this.localTasks.length
    },
    onTaskListDrop(event) {
      const fromColumn = event.dataTransfer.getData('fromColumn')
      if (fromColumn && fromColumn !== this.column.title) {
        // Cross-column drop into empty space
        const taskId = this.readTaskId(event)
        this.isDragOver = false
        this.draggingTaskId = null
        this.draggingTaskIndex = null
        this.emitMove(taskId)
        return
      }
      // Same-column drop at the end (reorder)
      if (this.reorderable && this.draggingTaskIndex !== null && this.taskDropIndex === this.localTasks.length) {
        this.onTaskDrop(event, this.localTasks.length)
      }
    },

    // Resolve `column.profiles` to full profile objects. Entries may be names
    // OR objects; either way the resolved object (with its `avatar`) is
    // preferred, and a name-only fallback guarantees something always renders.
    async loadColumnProfiles() {
      const entries = this.column.profiles || []
      const signature = this.profilesSignature
      const profiles = await this.loadAvailableProfiles()
      // Column changed (other board / filtered board) while we waited
      if (signature !== this.profilesSignature) return

      this.columnProfiles = entries.map(entry => {
        const name = entry && typeof entry === 'object' ? entry.name : entry
        return profiles.find(p => p.name === name)
          || (entry && typeof entry === 'object' ? entry : { name })
      })
    },

    // Read a dragged task id from either board's dataTransfer key
    readTaskId(event) {
      return event.dataTransfer.getData('taskId')
        || event.dataTransfer.getData('sprintTaskId')
        || event.dataTransfer.getData('text/plain')
    },
    // ── Column profiles (avatar group in the header) ─────────────────────────
    // Columns store the NAMES of the profiles pre-selected on new tasks; the
    // header resolves them to full profile objects (which carry the `avatar`
    // image URL) to render their avatar. The list is cached per project so a
    // board with many columns does not fire one request per column.
    async loadAvailableProfiles() {
      const key = this.$project?.project_id || ''
      const cached = profilesCache.promise
        && profilesCache.key === key
        && (Date.now() - profilesCache.at) < PROFILES_CACHE_MS
      if (!cached) {
        profilesCache = {
          key,
          at: Date.now(),
          promise: this.$project.$api.profiles.list().catch(() => [])
        }
      }
      return await profilesCache.promise
    }
  }
}
</script>