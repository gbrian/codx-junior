<template>
  <!--
    Gantt timeline for the sprint board.

    Task chats carry no explicit schedule, so the timeline is derived:
      • start → created_at (fallback: deadline, updated_at, today)
      • end   → deadline, else the completion date (done) or today (ongoing)
      • fill  → progress derived from the column status and its subtasks
    Tasks are grouped by their sprint column (status) so the status is always
    visible both in the left table and in the bar colour.
  -->
  <div class="sprint-gantt flex flex-col h-full min-h-0 bg-base-100">

    <!-- ── Toolbar: legend, overdue, zoom & jump-to-today ── -->
    <div class="shrink-0 flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2 border-b border-base-100">
      <!-- Status legend with task counts -->
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-base-content/60">
        <span v-for="entry in statusLegend" :key="entry.status" class="flex items-center gap-1.5">
          <span class="w-2.5 h-2.5 rounded-sm" :class="entry.fill"></span>
          <span>{{ entry.label }}</span>
          <span class="tabular-nums text-base-content/30">{{ entry.count }}</span>
        </span>
      </div>

      <!-- Overdue warning -->
      <span
        v-if="overdueCount"
        class="badge badge-xs badge-error gap-1 font-semibold"
        :title="`${overdueCount} task${overdueCount === 1 ? '' : 's'} past their deadline`"
      >
        <i class="fa-solid fa-triangle-exclamation text-[8px]"></i>
        {{ overdueCount }} overdue
      </span>

      <div class="grow"></div>

      <!-- Zoom -->
      <div class="join">
        <button
          v-for="z in zoomLevels"
          :key="z.value"
          class="btn btn-xs join-item"
          :class="zoom === z.value ? 'btn-primary' : 'btn-ghost'"
          :title="z.title"
          :aria-pressed="zoom === z.value"
          @click="zoom = z.value"
        >
          <i :class="[z.icon, 'text-xs']"></i>
        </button>
      </div>

      <!-- Jump to today -->
      <button
        class="btn btn-xs btn-ghost gap-1.5 text-base-content/50 hover:text-primary"
        title="Jump to today"
        @click="scrollToToday"
      >
        <i class="fa-solid fa-calendar-day text-xs"></i>
        <span class="hidden sm:inline text-xs">Today</span>
      </button>
    </div>

    <!-- ── Empty state ── -->
    <div v-if="!totalTasks" class="flex-1 flex flex-col items-center justify-center gap-2 text-base-content/30">
      <i class="fa-solid fa-chart-gantt text-4xl"></i>
      <span class="text-sm">No tasks to schedule yet</span>
    </div>

    <!-- ── Chart ── -->
    <div v-else ref="scroller" class="flex-1 min-h-0 overflow-auto">
      <div class="relative min-w-max" :style="{ width: totalWidth + 'px' }">

        <!-- Weekend stripes + day grid behind every row -->
        <div class="pointer-events-none absolute inset-y-0 z-0" :style="backgroundStyle"></div>

        <!-- Today marker -->
        <div
          v-if="todayOffset !== null"
          class="pointer-events-none absolute top-0 bottom-0 z-30 w-px bg-primary/60"
          :style="{ left: (leftWidth + todayOffset) + 'px' }"
        ></div>

        <!-- ── Sticky header ── -->
        <div class="sticky top-0 z-40 flex" :style="{ height: headerHeight + 'px' }">
          <!-- Left header labels -->
          <div
            class="sticky left-0 z-50 bg-base-200 border-r border-b border-base-300 flex items-end gap-2 px-3 pb-1"
            :style="{ width: leftWidth + 'px', height: headerHeight + 'px' }"
          >
            <span class="text-[10px] font-semibold uppercase tracking-wider text-base-content/40 flex-1">Task</span>
            <span class="text-[10px] font-semibold uppercase tracking-wider text-base-content/40 w-16 text-center">Team</span>
            <span class="text-[10px] font-semibold uppercase tracking-wider text-base-content/40 w-7 text-right">%</span>
          </div>

          <!-- Timeline header: months + days -->
          <div class="bg-base-200 border-b border-base-300 overflow-hidden" :style="{ width: timelineWidth + 'px' }">
            <div class="flex h-6">
              <div
                v-for="seg in monthSegments"
                :key="seg.key"
                class="text-[10px] font-semibold text-base-content/50 px-1.5 border-r border-base-300 flex items-center whitespace-nowrap overflow-hidden"
                :style="{ width: (seg.span * dayWidth) + 'px' }"
              >{{ seg.label }}</div>
            </div>
            <div class="flex h-6">
              <div
                v-for="day in days"
                :key="day.key"
                class="flex items-center justify-center text-[9px] border-r border-base-300/40"
                :class="[
                  day.isWeekend ? 'text-base-content/25' : 'text-base-content/50',
                  day.isToday ? 'bg-primary/15 text-primary font-semibold' : ''
                ]"
                :style="{ width: dayWidth + 'px' }"
              >{{ day.dayNumber }}</div>
            </div>
          </div>
        </div>

        <!-- ── Rows ── -->
        <div
          v-for="row in displayRows"
          :key="row.key"
          class="relative z-10 flex border-b border-base-100"
          :style="{ height: rowHeight + 'px' }"
        >
          <!-- Left cell -->
          <div
            class="sticky left-0 z-20 border-r border-base-100 flex items-center"
            :class="[
              row.type === 'group' ? 'bg-base-200/80' : 'bg-base-100',
              row.type === 'task' && row.id === selectedTaskId ? 'ring-1 ring-inset ring-primary/40' : ''
            ]"
            :style="{ width: leftWidth + 'px' }"
            :tabindex="row.type === 'task' ? 0 : null"
            :role="row.type === 'task' ? 'button' : null"
            @click="onRowClick(row, $event)"
            @keydown.enter.prevent="onRowClick(row, $event)"
          >
            <!-- Group row -->
            <div v-if="row.type === 'group'" class="flex items-center gap-2 px-3 w-full min-w-0">
              <span class="w-2 h-2 rounded-full shrink-0" :class="row.meta.fill"></span>
              <span class="text-xs font-bold uppercase tracking-wider text-base-content/70 flex-1 min-w-0 truncate">{{ row.title }}</span>
              <span class="badge badge-xs badge-ghost shrink-0 tabular-nums" :title="`${row.count} tasks`">{{ row.count }}</span>
            </div>

            <!-- Task row -->
            <div v-else class="flex items-center gap-2 px-3 w-full min-w-0">
              <span class="w-2 h-2 rounded-full shrink-0" :class="row.meta.fill" :title="row.meta.label"></span>

              <!-- Name + notes -->
              <div class="flex-1 min-w-0">
                <div
                  class="truncate text-xs font-medium leading-tight"
                  :class="row.status === 'done' ? 'line-through text-base-content/45' : 'text-base-content/90'"
                  :title="row.name"
                >{{ row.name }}</div>
                <div class="flex items-center gap-2 text-[10px] leading-tight text-base-content/40 mt-0.5 min-w-0">
                  <span
                    v-if="row.deadlineLabel"
                    class="flex items-center gap-1 shrink-0"
                    :class="row.overdue ? 'text-error font-semibold' : ''"
                  >
                    <i :class="row.overdue ? 'fa-solid fa-triangle-exclamation' : 'fa-regular fa-clock'" class="text-[9px]"></i>
                    {{ row.deadlineLabel }}
                  </span>
                  <span v-if="row.cost" class="flex items-center gap-0.5 shrink-0 text-amber-400/70">
                    <i class="fa-solid fa-coins text-[9px]"></i>{{ formatCoins(row.cost) }}
                  </span>
                  <span v-if="row.subtasksTotal" class="flex items-center gap-0.5 shrink-0" :title="`${row.subtasksDone} of ${row.subtasksTotal} subtasks done`">
                    <i class="fa-regular fa-file-lines text-[9px]"></i>{{ row.subtasksDone }}/{{ row.subtasksTotal }}
                  </span>
                  <span v-if="!row.deadlineLabel && !row.cost && !row.subtasksTotal" class="text-base-content/25 italic truncate">no schedule</span>
                </div>
              </div>

              <!-- Assignees -->
              <div class="w-16 flex items-center justify-end shrink-0" :title="row.users.join(', ') || 'Unassigned'">
                <div v-if="row.assignees.length" class="flex items-center -space-x-1.5">
                  <span
                    v-for="person in row.assignees.slice(0, 3)"
                    :key="person.name"
                    class="w-5 h-5 rounded-full ring-1 ring-base-100 bg-base-300 overflow-hidden flex items-center justify-center text-[8px] font-medium text-base-content/60"
                  >
                    <img v-if="person.avatar" :src="person.avatar" :alt="person.name" class="w-full h-full object-cover" />
                    <span v-else>{{ person.initial }}</span>
                  </span>
                  <span
                    v-if="row.assignees.length > 3"
                    class="w-5 h-5 rounded-full bg-base-300 ring-1 ring-base-100 flex items-center justify-center text-[8px] font-semibold text-base-content/50"
                  >+{{ row.assignees.length - 3 }}</span>
                </div>
                <i v-else class="fa-regular fa-user text-[10px] text-base-content/20"></i>
              </div>

              <!-- Progress ring -->
              <span class="relative w-7 h-7 shrink-0" :class="row.meta.text" :title="`${row.progress}% done`" :aria-label="`${row.progress}% done`">
                <svg viewBox="0 0 36 36" class="w-7 h-7 -rotate-90">
                  <circle cx="18" cy="18" r="15" fill="none" stroke="currentColor" stroke-width="4" class="opacity-15" />
                  <circle
                    cx="18" cy="18" r="15" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"
                    :stroke-dasharray="progressDash(row.progress) + ' 94.25'"
                  />
                </svg>
                <span class="absolute inset-0 flex items-center justify-center text-[8px] font-semibold tabular-nums">{{ row.progress }}</span>
              </span>
            </div>
          </div>

          <!-- Timeline cell -->
          <div
            class="relative"
            :class="row.type === 'task' ? 'cursor-pointer' : ''"
            :style="{ width: timelineWidth + 'px' }"
            @click="onRowClick(row, $event)"
          >
            <!-- Bar -->
            <template v-if="row.bar && !row.bar.milestone">
              <div
                class="absolute rounded-md overflow-hidden shadow-sm"
                :class="row.id === selectedTaskId ? 'ring-2 ring-primary/60' : ''"
                :style="barStyle(row.bar)"
                :title="row.type === 'group' ? `${row.count} tasks · ${row.progress}% done` : barTooltip(row)"
              >
                <div class="absolute inset-0" :class="row.meta.track"></div>
                <div class="absolute inset-y-0 left-0 transition-all duration-200" :class="row.meta.fill" :style="{ width: row.progress + '%' }"></div>
                <span
                  v-if="row.bar.showLabel"
                  class="absolute inset-0 flex items-center px-1.5 text-[10px] font-medium text-white/95 truncate pointer-events-none [text-shadow:0_1px_2px_rgba(0,0,0,0.45)]"
                >{{ row.type === 'group' ? row.title : row.name }}</span>
              </div>
            </template>

            <!-- Milestone (zero-length task) -->
            <template v-else-if="row.bar && row.bar.milestone">
              <div
                class="absolute rounded-[2px] rotate-45"
                :class="row.meta.fill"
                :style="barStyle(row.bar)"
                :title="barTooltip(row)"
              ></div>
              <span
                class="absolute text-[10px] text-base-content/50 whitespace-nowrap pointer-events-none"
                :style="{ left: (row.bar.left + row.bar.width + 6) + 'px', top: (row.bar.top - 4) + 'px' }"
              >{{ row.name }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// Row / bar metrics (kept uniform so the sticky left table stays aligned with
// the timeline rows and the shared background/grid keeps lining up)
const ROW_H = 44
const HEADER_H = 48
const TASK_BAR_H = 20
const GROUP_BAR_H = 8
const LEFT_WIDTH = 340
// Hard cap on the rendered window so a very old task cannot explode the chart
const MAX_RANGE_DAYS = 180

// Canonical sprint statuses → colour tokens and labels
const STATUS_META = {
  todo:     { label: 'To do',       fill: 'bg-info',    track: 'bg-info/30',    text: 'text-info' },
  doing:    { label: 'In progress', fill: 'bg-primary', track: 'bg-primary/30', text: 'text-primary' },
  onhold:   { label: 'On hold',     fill: 'bg-warning', track: 'bg-warning/30', text: 'text-warning' },
  done:     { label: 'Done',        fill: 'bg-success', track: 'bg-success/30', text: 'text-success' },
  rejected: { label: 'Rejected',    fill: 'bg-error',   track: 'bg-error/30',   text: 'text-error' }
}

const STATUS_ORDER = ['todo', 'doing', 'onhold', 'done', 'rejected']

export default {
  name: 'SprintBoardGantt',
  props: {
    // Same column shape the board canvas receives: { title, status, icon, color, tasks }
    columns: { type: Array, default: () => [] },
    // Task highlighted by the parent selection (opens a ring on its row/bar)
    selectedTaskId: { type: String, default: null }
  },
  emits: ['open-task', 'open-task-window'],
  data() {
    return {
      zoom: 'normal',
      zoomLevels: [
        { value: 'compact', title: 'Compact', icon: 'fa-solid fa-minimize', width: 16 },
        { value: 'normal', title: 'Normal', icon: 'fa-solid fa-equals', width: 30 },
        { value: 'wide', title: 'Wide', icon: 'fa-solid fa-maximize', width: 46 }
      ],
      rowHeight: ROW_H,
      headerHeight: HEADER_H,
      leftWidth: LEFT_WIDTH
    }
  },
  computed: {
    // Stable "today" (computed once, used across all the schedule derivations)
    today() {
      const d = new Date()
      d.setHours(0, 0, 0, 0)
      return d
    },

    // ── Rows ─────────────────────────────────────────────────────────────────
    // One group row per column (status) followed by its task rows
    rows() {
      const out = []
      this.columns.forEach((column, colIndex) => {
        const status = this.normalizeStatus(column.status)
        const meta = this.statusMeta(status)
        const tasks = (column.tasks || []).map(task => this.buildTaskRow(task, column, status, meta, colIndex))
        tasks.sort((a, b) => a.start - b.start || a.name.localeCompare(b.name))

        const doneCount = tasks.filter(r => r.progress >= 100).length
        const groupStart = tasks.length ? tasks.reduce((m, r) => (r.start < m ? r.start : m), tasks[0].start) : this.today
        const groupEnd = tasks.length ? tasks.reduce((m, r) => (r.end > m ? r.end : m), tasks[0].end) : this.today

        out.push({
          key: `group-${colIndex}-${column.id || column.title}`,
          type: 'group',
          title: column.title,
          status,
          meta,
          count: tasks.length,
          doneCount,
          start: groupStart,
          end: groupEnd,
          progress: tasks.length ? Math.round((doneCount / tasks.length) * 100) : 0
        })
        out.push(...tasks)
      })
      return out
    },
    taskRows() {
      return this.rows.filter(r => r.type === 'task')
    },
    totalTasks() {
      return this.taskRows.length
    },
    statusCounts() {
      const counts = { todo: 0, doing: 0, onhold: 0, done: 0, rejected: 0 }
      this.taskRows.forEach(r => {
        if (counts[r.status] != null) counts[r.status] += 1
      })
      return counts
    },
    statusLegend() {
      return STATUS_ORDER.map(status => ({ status, ...STATUS_META[status], count: this.statusCounts[status] }))
    },
    overdueCount() {
      return this.taskRows.filter(r => r.overdue).length
    },

    // ── Timeline range ───────────────────────────────────────────────────────
    // Padded to whole weeks (Monday-based) so the weekend shading stays regular
    timelineRange() {
      if (!this.taskRows.length) {
        const start = this.startOfWeek(this.today)
        return { start, end: this.addDays(start, 27) }
      }
      let min = this.taskRows[0].start
      let max = this.taskRows[0].end
      this.taskRows.forEach(r => {
        if (r.start < min) min = r.start
        if (r.end > max) max = r.end
      })
      let start = this.startOfWeek(this.addDays(min, -2))
      let end = this.endOfWeek(this.addDays(max, 7))
      if (this.daysBetween(start, end) > MAX_RANGE_DAYS) {
        end = this.endOfWeek(max)
        start = this.startOfWeek(this.addDays(end, -MAX_RANGE_DAYS))
      }
      return { start, end }
    },
    rangeStart() {
      return this.timelineRange.start
    },
    rangeEnd() {
      return this.timelineRange.end
    },
    dayWidth() {
      return (this.zoomLevels.find(z => z.value === this.zoom) || this.zoomLevels[1]).width
    },
    days() {
      const out = []
      let cursor = new Date(this.rangeStart)
      while (cursor <= this.rangeEnd && out.length <= MAX_RANGE_DAYS + 14) {
        out.push({
          key: `d-${cursor.getTime()}`,
          dayNumber: cursor.getDate(),
          isWeekend: cursor.getDay() === 0 || cursor.getDay() === 6,
          isToday: this.isSameDay(cursor, this.today)
        })
        cursor = this.addDays(cursor, 1)
      }
      return out
    },
    timelineWidth() {
      return this.days.length * this.dayWidth
    },
    totalWidth() {
      return this.leftWidth + this.timelineWidth
    },
    monthSegments() {
      const segments = []
      let current = null
      this.days.forEach(day => {
        const key = `${day.key.split('-')[1]}-${day.dayNumber}` // not stable across months, replaced below
        void key
      })
      // Group by year-month using the underlying dates
      let cursor = new Date(this.rangeStart)
      while (cursor <= this.rangeEnd) {
        const key = `${cursor.getFullYear()}-${cursor.getMonth()}`
        if (!current || current.key !== key) {
          current = {
            key,
            span: 0,
            label: cursor.toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
          }
          segments.push(current)
        }
        current.span += 1
        cursor = this.addDays(cursor, 1)
      }
      return segments
    },
    todayOffset() {
      const today = this.startOfDay(this.today)
      if (today < this.startOfDay(this.rangeStart) || today > this.startOfDay(this.rangeEnd)) return null
      return this.daysBetween(this.rangeStart, today) * this.dayWidth
    },
    backgroundStyle() {
      return {
        left: this.leftWidth + 'px',
        width: this.timelineWidth + 'px',
        backgroundImage: this.gridGradient
      }
    },
    // Weekend stripes (Monday-based week: Sat+Sun) + 1px day grid lines
    gridGradient() {
      const dw = this.dayWidth
      const weekend = 'rgba(148,163,184,0.07)'
      const grid = 'rgba(148,163,184,0.10)'
      return [
        `repeating-linear-gradient(to right, transparent 0, transparent ${5 * dw}px, ${weekend} ${5 * dw}px, ${weekend} ${7 * dw}px)`,
        `repeating-linear-gradient(to right, transparent 0, transparent ${dw - 1}px, ${grid} ${dw - 1}px, ${grid} ${dw}px)`
      ].join(', ')
    },

    // Rows enriched with their bar geometry (kept out of the template so the
    // dates are computed once per render instead of per binding)
    displayRows() {
      return this.rows.map(row => ({ ...row, bar: this.barGeometry(row) }))
    }
  },
  mounted() {
    this.$nextTick(this.scrollToToday)
  },
  methods: {
    // ── Status helpers ───────────────────────────────────────────────────────
    normalizeStatus(status) {
      return STATUS_META[status] ? status : 'todo'
    },
    statusMeta(status) {
      return STATUS_META[status] || STATUS_META.todo
    },

    // ── Date helpers (all operate on start-of-day dates) ─────────────────────
    startOfDay(date) {
      const d = new Date(date)
      d.setHours(0, 0, 0, 0)
      return d
    },
    addDays(date, amount) {
      const d = new Date(date)
      d.setDate(d.getDate() + amount)
      return this.startOfDay(d)
    },
    daysBetween(from, to) {
      return Math.round((this.startOfDay(to) - this.startOfDay(from)) / 86400000)
    },
    startOfWeek(date) {
      const d = this.startOfDay(date)
      const day = d.getDay() // 0 = Sunday
      const diff = day === 0 ? -6 : 1 - day // shift to Monday
      return this.addDays(d, diff)
    },
    endOfWeek(date) {
      return this.addDays(this.startOfWeek(date), 6)
    },
    isSameDay(a, b) {
      return this.startOfDay(a).getTime() === this.startOfDay(b).getTime()
    },
    parseDate(value) {
      if (!value) return null
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return null
      return this.startOfDay(d)
    },
    formatDate(date) {
      return date ? date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : ''
    },
    formatShort(date) {
      return date ? date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''
    },
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1000000) return (val / 1000000).toFixed(2) + 'M'
      if (val >= 1000) return (val / 1000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    },

    // ── Schedule derivation ──────────────────────────────────────────────────
    resolveStart(task) {
      return this.parseDate(task.created_at)
        || this.parseDate(task.deadline)
        || this.parseDate(task.updated_at)
        || this.startOfDay(this.today)
    },
    resolveEnd(task, start, status) {
      const deadline = this.parseDate(task.deadline)
      if (deadline && deadline >= start) return deadline
      const updated = this.parseDate(task.updated_at)
      if (status === 'done' || status === 'rejected') {
        return updated && updated >= start ? updated : start
      }
      // Ongoing work extends up to today (or a single day when it starts today)
      if (this.today > start) return this.today
      return this.addDays(start, 1)
    },
    resolveProgress(status, children) {
      if (status === 'done' || status === 'rejected') return 100
      if (children.length) {
        const done = children.filter(c => c.status === 'done').length
        if (done) return Math.max(1, Math.round((done / children.length) * 100))
        return 0
      }
      if (status === 'doing') return 50
      if (status === 'onhold') return 20
      return 0
    },
    childrenOf(task) {
      try {
        return this.$storex.chats.chatChildren(task.id) || []
      } catch (error) {
        return []
      }
    },
    resolveAssignees(names) {
      const known = this.$storex.api.userNetwork || []
      return (names || []).map(name => {
        const user = known.find(u => u.username === name)
        return {
          name,
          avatar: user?.avatar || null,
          initial: (name || '?').trim().charAt(0).toUpperCase() || '?'
        }
      })
    },
    buildTaskRow(task, column, status, meta, colIndex) {
      const start = this.resolveStart(task)
      const end = this.resolveEnd(task, start, status)
      const children = this.childrenOf(task)
      const deadline = this.parseDate(task.deadline)
      return {
        key: `task-${colIndex}-${task.id}`,
        type: 'task',
        id: task.id,
        task,
        name: task.name || 'Untitled',
        status,
        meta,
        start,
        end,
        progress: this.resolveProgress(status, children),
        users: task.users || [],
        assignees: this.resolveAssignees(task.users),
        cost: task.cost || 0,
        estimation: task.estimation_cost || 0,
        deadline,
        deadlineLabel: deadline ? this.formatShort(deadline) : null,
        overdue: !!deadline && deadline < this.today && status !== 'done' && status !== 'rejected',
        subtasksTotal: children.length,
        subtasksDone: children.filter(c => c.status === 'done').length,
        milestone: this.daysBetween(start, end) === 0
      }
    },

    // ── Bar geometry ─────────────────────────────────────────────────────────
    barGeometry(row) {
      const dw = this.dayWidth
      const startDay = Math.max(0, this.daysBetween(this.rangeStart, row.start))
      const endDay = Math.min(this.days.length - 1, this.daysBetween(this.rangeStart, row.end))
      const span = Math.max(0, endDay - startDay)

      if (row.type === 'group') {
        if (!row.count) return null
        const width = Math.max(dw, (span + 1) * dw - 2)
        return {
          left: startDay * dw + 1,
          width,
          top: (ROW_H - GROUP_BAR_H) / 2,
          height: GROUP_BAR_H,
          milestone: false,
          showLabel: width > 70
        }
      }

      if (row.milestone) {
        return {
          left: startDay * dw + (dw - 11) / 2,
          width: 11,
          height: 11,
          top: (ROW_H - 11) / 2,
          milestone: true,
          showLabel: false
        }
      }

      const width = Math.max(6, (span + 1) * dw - 4)
      return {
        left: startDay * dw + 2,
        width,
        top: (ROW_H - TASK_BAR_H) / 2,
        height: TASK_BAR_H,
        milestone: false,
        showLabel: width > 84
      }
    },
    barStyle(bar) {
      return {
        left: bar.left + 'px',
        top: bar.top + 'px',
        width: bar.width + 'px',
        height: bar.height + 'px'
      }
    },
    barTooltip(row) {
      if (row.type === 'group') {
        return `${row.title} — ${row.count} tasks · ${row.progress}% done`
      }
      const lines = [
        row.name,
        `${this.formatDate(row.start)} → ${this.formatDate(row.end)}`,
        `Status: ${row.meta.label}`,
        `Progress: ${row.progress}%`
      ]
      if (row.users?.length) lines.push(`Team: ${row.users.join(', ')}`)
      if (row.deadline) lines.push(`Deadline: ${this.formatDate(row.deadline)}${row.overdue ? ' (overdue)' : ''}`)
      if (row.cost) lines.push(`Cost: ${this.formatCoins(row.cost)} cxj`)
      if (row.subtasksTotal) lines.push(`Subtasks: ${row.subtasksDone}/${row.subtasksTotal} done`)
      return lines.join('\n')
    },
    progressDash(progress) {
      const circumference = 2 * Math.PI * 15 // r = 15
      const clamped = Math.max(0, Math.min(100, progress || 0))
      return ((clamped / 100) * circumference).toFixed(2)
    },

    // ── Interaction ──────────────────────────────────────────────────────────
    onRowClick(row, event) {
      if (!row || row.type !== 'task') return
      if (event && (event.ctrlKey || event.metaKey)) {
        this.$emit('open-task-window', row.task)
        return
      }
      this.$emit('open-task', row.task)
    },
    scrollToToday() {
      const el = this.$refs.scroller
      if (!el) return
      const offset = this.todayOffset
      const target = offset === null
        ? 0
        : this.leftWidth + offset - el.clientWidth / 2
      el.scrollTo({ left: Math.max(0, target), behavior: 'smooth' })
    }
  }
}
</script>