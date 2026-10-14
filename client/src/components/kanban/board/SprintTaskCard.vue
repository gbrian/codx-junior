<script setup>
import moment from 'moment'
</script>

<template>
  <article
    class="group/card rounded-xl bg-base-200 border p-2.5 cursor-pointer transition-all duration-150"
    :class="selected
      ? 'border-primary/50 bg-primary/5'
      : hasUnread
        ? 'border-error/30 ring-1 ring-error/20 hover:border-error/70'
        : 'border-base-100 hover:border-primary/40'"
    @click="onCardClick"
  >
    <!-- Title row -->
    <div class="flex items-start gap-2">
      <i :class="[modeIcon, 'text-xs text-base-content/40 mt-0.5 w-3 text-center shrink-0']"></i>
      <!-- Processing spinner: shown while the chat is streaming (same pattern as AppIcon) -->
      <span
        v-if="isProcessing"
        class="loading loading-bars loading-xs text-info shrink-0 mt-0.5"
        role="img"
        title="Processing…"
        aria-label="Processing"
      ></span>
      <span
        class="flex-1 text-sm font-medium leading-tight"
        :class="task.status === 'done' ? 'line-through opacity-60' : ''"
      >{{ task.name || 'Untitled' }}</span>

      <!-- Unread assistant replies: solid badge so unread cards stand out at a glance -->
      <span
        v-if="hasUnread"
        class="badge badge-sm badge-error badge-outline gap-1 shrink-0 font-bold"
        :title="unreadTitle"
        :aria-label="unreadTitle"
      >
        <i class="fa-solid fa-check-double text-[9px]" aria-hidden="true"></i>
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>

      <span
        v-if="priority"
        class="badge badge-xs badge-outline shrink-0"
        :class="priority.badge"
      >{{ priority.label }}</span>
    </div>

    <!-- Sprint membership chips -->
    <div v-if="sprintChips.length" class="flex items-center gap-1 mt-2 flex-wrap">
      <span
        v-for="chip in sprintChips"
        :key="chip.id"
        class="badge badge-xs badge-ghost gap-1"
        :title="chip.title"
      >
        <i class="fa-solid fa-layer-group text-[8px]"></i>{{ chip.short }}
      </span>
    </div>

    <!-- Parent breadcrumb for subtasks -->
    <div
      v-if="parentChat"
      class="text-[10px] text-primary/50 hover:text-primary truncate mt-1"
      @click.stop="$chats.setActiveChat(parentChat)"
    >
      {{ parentChat.name }}
    </div>

    <!-- Meta row: project · assignees · deadline -->
    <div
      v-if="chatProject || assignees.length || deadline"
      class="flex items-center gap-2 mt-2 flex-wrap"
    >
      <!-- Assigned project (only when it differs from the active project) -->
      <span
        v-if="chatProject"
        class="flex items-center gap-1 text-[10px] text-primary/60 min-w-0"
        :title="`Project: ${chatProject.project_name}`"
      >
        <img
          v-if="chatProject.project_icon"
          :src="chatProject.project_icon"
          :alt="chatProject.project_name"
          class="w-3 h-3 rounded shrink-0"
        />
        <i v-else class="fa-solid fa-cube text-[10px] shrink-0"></i>
        <span class="truncate max-w-[7rem]">{{ chatProject.project_name }}</span>
      </span>

      <!-- Assignees -->
      <div
        v-if="assignees.length"
        class="flex items-center -space-x-2 shrink-0"
        :title="assigneeTitle"
        :aria-label="assigneeTitle"
      >
        <div v-for="user in assignees.slice(0, 3)" :key="user.username" class="avatar placeholder">
          <div class="w-4 h-4 rounded-full bg-base-300 ring-1 ring-base-200 text-[8px] text-base-content/60">
            <img v-if="user.avatar" :src="user.avatar" :alt="user.username" />
            <span v-else>{{ initial(user) }}</span>
          </div>
        </div>
        <span v-if="assignees.length > 3" class="badge badge-xs badge-ghost ml-1">
          +{{ assignees.length - 3 }}
        </span>
      </div>

      <!-- Deadline -->
      <span
        v-if="deadline"
        class="badge badge-xs gap-1 shrink-0"
        :class="deadline.badge"
        :title="`Deadline: ${deadline.date}`"
      >
        <i class="fa-regular fa-clock text-[9px]"></i>{{ deadline.label }}
      </span>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between mt-2 gap-1">
      <div class="flex items-center gap-1.5 min-w-0 flex-wrap">
        <!-- Card accumulated cost -->
        <span
          v-if="task.cost > 0"
          class="text-[10px] px-1.5 py-0.5 rounded-full hover:bg-amber-400/10 text-amber-400/60 hover:text-amber-400 flex items-center gap-1 tabular-nums font-semibold shrink-0"
          :title="costTooltip"
        >
          <i class="fa-solid fa-coins text-[9px]"></i>{{ formatCoins(task.cost) }}
        </span>
        <span
          v-if="subTasks.length"
          class="text-[10px] px-1.5 py-0.5 rounded-full bg-warning/15 text-warning flex items-center gap-1 shrink-0"
          :title="`${subTasks.length} subtasks`"
        >
          <i class="fa-regular fa-file-lines"></i>{{ subTasks.length }}
        </span>
        <span v-else class="text-[10px] text-base-content/25 shrink-0">no subtasks</span>

        <!-- Number of messages -->
        <span
          class="text-[10px] text-base-content/40 flex items-center gap-1 shrink-0"
          :title="`${messageCount} messages`"
        >
          <i class="fa-regular fa-comment text-[10px]"></i>{{ messageCount }}
        </span>

        <!-- Pending messages (awaiting an answer / assistant still streaming) -->
        <span
          v-if="pendingCount"
          class="text-[10px] px-1.5 py-0.5 rounded-full bg-info/15 text-info flex items-center gap-1 shrink-0"
          :title="`${pendingCount} pending message${pendingCount === 1 ? '' : 's'}`"
        >
          <i class="fa-solid fa-hourglass-half text-[9px]"></i>{{ pendingCount }}
        </span>

        <!-- Last update (relative) -->
        <span
          v-if="updatedFromNow"
          class="text-[10px] text-base-content/30 shrink-0"
          :title="updatedAtLabel"
        >{{ updatedFromNow }}</span>
      </div>

      <!-- Card actions (revealed on hover / focus-within) -->
      <div
        class="flex items-center gap-0.5 opacity-0 group-hover/card:opacity-100 focus-within:opacity-100 transition-opacity shrink-0"
      >
        <!-- Open in a new window (desktop only) -->
        <button
          v-if="isDesktop"
          class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-primary"
          title="Open in a new window"
          aria-label="Open in a new window"
          @click.stop="$emit('open-window')"
        >
          <i class="fa-solid fa-up-right-from-square text-xs"></i>
        </button>

        <template v-if="showActions">
          <button
            class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-primary"
            title="Create subtask"
            aria-label="Create subtask"
            @click.stop="$emit('add-subtask')"
          >
            <i class="fa-solid fa-plus text-xs"></i>
          </button>
          <button
            class="btn btn-ghost btn-xs rounded-md h-5 min-h-0 px-1 text-base-content/30 hover:text-error"
            title="Remove from sprint"
            aria-label="Remove from sprint"
            @click.stop="$emit('remove')"
          >
            <i class="fa-solid fa-xmark text-xs"></i>
          </button>
        </template>
      </div>
    </div>
  </article>
</template>

<script>
export default {
  name: 'SprintTaskCard',
  props: {
    task: { type: Object, required: true },
    selected: { type: Boolean, default: false },
    // Kanban hides the sprint-specific hover actions (add subtask / remove from sprint)
    showActions: { type: Boolean, default: true }
  },
  emits: ['open', 'open-window', 'add-subtask', 'remove'],
  computed: {
    // The "open in a new window" affordance is desktop-only
    isDesktop() {
      return !this.$ui.isMobile
    },
    modeIcon() {
      return this.$storex.chats.chatModeIcon(this.task.mode) || 'fa-solid fa-message'
    },
    // True while the chat is streaming an answer (same source AppIcon uses)
    isProcessing() {
      return !!this.task.id && this.$storex.chats.isChatUpdating(this.task.id)
    },
    priority() {
      const value = this.task.priority
      return value ? this.$storex.planning.priorityConfig(value) : null
    },
    subTasks() {
      return this.$storex.chats.chatChildren(this.task.id) || []
    },
    parentChat() {
      return this.task.parent_id ? this.$storex.chats.chats?.[this.task.parent_id] : null
    },
    sprintChips() {
      const boards = this.$storex.kanban.allBoards
      return (this.task.sprints || []).map(id => {
        const board = boards.find(b => b.id === id)
        const title = board?.title || id
        return { id, title, short: title.split('·')[0].trim() }
      })
    },
    costTooltip() {
      const spent = this.formatCoins(this.task?.cost || 0)
      if (this.task?.estimation_cost) {
        return `Cost: ${spent} of ${this.formatCoins(this.task.estimation_cost)} cxj`
      }
      return `Cost: ${spent} cxj`
    },

    // ── Card info ────────────────────────────────────────────────────────────
    // NOTE: chats coming from `chats.list()` carry only the last message until
    // fully loaded, so this count can be optimistic (1) on first paint.
    messageCount() {
      return (this.task.messages || []).length
    },
    // Messages awaiting an answer: not-done messages, or the chat is streaming
    pendingCount() {
      const notDone = (this.task.messages || []).filter(m => m.done === false).length
      if (notDone > 0) return notDone
      return this.isProcessing ? 1 : 0
    },
    // Unread assistant replies addressed to the current user — same rule the
    // chat sidebar uses: assistant message, not authored by me, not flagged as
    // read by me, not hidden, AND already finished (done !== false). Messages
    // that are still being processed must not count as unread: the badge (and
    // the unread card highlight) may only appear once the reply is done.
    unreadCount() {
      const currentUsername = this.$user?.username
      if (!currentUsername) return 0
      return (this.task.messages || []).filter(msg => {
        const isAssistantMsg = msg.role === 'assistant'
        const isOtherUser = msg.user !== currentUsername
        const isUnread = !msg.read_by || !msg.read_by.includes(currentUsername)
        // Skip messages still not done (streaming / pending)
        const isDone = msg.done !== false
        return isAssistantMsg && isOtherUser && isUnread && isDone && !msg.hide
      }).length
    },
    hasUnread() {
      return this.unreadCount > 0
    },
    unreadTitle() {
      const count = this.unreadCount
      return `${count} unread message${count === 1 ? '' : 's'}`
    },
    updatedFromNow() {
      const ts = this.task.updated_at || this.task.lastMessageAt
      return ts ? moment(ts).fromNow() : ''
    },
    updatedAtLabel() {
      const ts = this.task.updated_at || this.task.lastMessageAt
      return ts ? moment(ts).format('MMM DD, YYYY HH:mm') : ''
    },
    // Assigned project — only shown when it differs from the active project
    chatProject() {
      const id = this.task.project_id
      if (!id || id === this.$project?.project_id) return null
      return this.$storex.projects.allProjectsById?.[id] || null
    },
    // Assignees resolved from the usernames stored on the task
    assignees() {
      const names = this.task.users || []
      const known = this.$storex.api.userNetwork || this.$storex.users.users || []
      return names.map(name =>
        known.find(u => u.username === name) || { username: name, avatar: null }
      )
    },
    assigneeTitle() {
      return (this.task.users || []).join(', ')
    },
    deadline() {
      if (!this.task.deadline) return null
      const date = moment(this.task.deadline)
      if (!date.isValid()) return null
      const today = moment().startOf('day')
      let badge = 'badge-ghost'
      if (date.isBefore(today)) badge = 'badge-error'
      else if (date.diff(today, 'days') <= 1) badge = 'badge-warning'
      else badge = 'badge-success'
      return {
        date: date.format('MMM DD, YYYY'),
        label: date.fromNow(),
        badge
      }
    }
  },
  methods: {
    // Plain click opens the task inline (right pane); Ctrl/Cmd+click keeps the
    // original behaviour and opens it in its own window.
    onCardClick(event) {
      if (event?.ctrlKey || event?.metaKey) {
        this.$emit('open-window')
        return
      }
      this.$emit('open')
    },
    initial(user) {
      return (user.name || user.username || '?')[0].toUpperCase()
    },
    formatCoins(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(2) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(2) + 'K'
      return Number(val).toFixed(2)
    }
  }
}
</script>