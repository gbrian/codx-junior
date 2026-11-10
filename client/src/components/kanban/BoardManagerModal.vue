<script setup>
import ChatProfileSelector from '@/components/chat/ChatProfileSelector.vue'
</script>

<template>
  <modal close @close="$emit('close')">
    <template #header>
      <div class="flex items-center gap-2 min-w-0">
        <i class="fa-solid fa-user-tie text-sm text-primary"></i>
        <div class="min-w-0">
          <h2 class="text-sm font-semibold truncate">Board manager</h2>
          <p class="text-[10px] text-base-content/40 truncate">{{ board?.title || 'Board' }}</p>
        </div>
        <span
          class="badge badge-xs ml-2 shrink-0"
          :class="statusBadgeClass"
        >{{ statusLabel }}</span>
      </div>
    </template>

    <div class="flex flex-col gap-4">
      <!-- What it does -->
      <p class="text-xs text-base-content/55 leading-relaxed">
        A profile reviews this board in the background and keeps it healthy: it can move
        cards to another column, comment, close finished tasks and adjust priority or due
        dates. Every change is validated against this board before it is applied.
      </p>

      <!-- Configuration -->
      <div class="rounded-lg border border-base-content/10 bg-base-200/40 p-3 flex flex-col gap-3">
        <div class="flex items-center justify-between gap-3">
          <div class="min-w-0">
            <span class="text-xs font-semibold">Enable automatic reviews</span>
            <p class="text-[10px] text-base-content/40 mt-0.5">
              The worker only reviews boards with this switch on.
            </p>
          </div>
          <input v-model="config.enabled" type="checkbox" class="toggle toggle-primary toggle-sm" />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Manager profile</span>
            <ChatProfileSelector
              :project="boardProject || $project"
              single
              allow-deselect
              label="Manager"
              icon="fa-solid fa-user-tie"
              empty-label="Board assistant (or ProjectManager)"
              :selected-profiles="managerProfileSelection"
              @update:selected-profiles="onProfileSelected"
            />
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Mode</span>
            <select v-model="config.mode" class="select select-sm select-bordered">
              <option value="apply">Apply changes</option>
              <option value="suggest">Suggest only</option>
            </select>
            <span class="text-[10px] text-base-content/40">
              Suggest only records the proposed actions in the report.
            </span>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Review every</span>
            <div class="join">
              <input
                v-model.number="config.interval_minutes"
                type="number"
                min="5"
                max="10080"
                class="input input-sm input-bordered join-item w-full"
              />
              <span class="btn btn-sm join-item pointer-events-none text-xs">min</span>
            </div>
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Max actions per review</span>
            <input
              v-model.number="config.max_actions"
              type="number"
              min="1"
              max="20"
              class="input input-sm input-bordered"
            />
          </label>

          <label class="flex flex-col gap-1">
            <span class="text-[10px] uppercase tracking-wider text-base-content/40">Tasks per review</span>
            <input
              v-model.number="config.max_tasks"
              type="number"
              min="1"
              max="200"
              class="input input-sm input-bordered"
            />
            <span class="text-[10px] text-base-content/40">
              Open, recently updated tasks are included first.
            </span>
          </label>
        </div>

        <label class="flex items-center gap-2 text-xs text-base-content/60 cursor-pointer">
          <input v-model="config.include_done" type="checkbox" class="checkbox checkbox-xs" />
          Include done tasks in the review (they are context only, never modified)
        </label>

        <label class="flex flex-col gap-1">
          <span class="text-[10px] uppercase tracking-wider text-base-content/40">
            Instructions <span class="normal-case text-base-content/30">(optional policy for this board)</span>
          </span>
          <textarea
            v-model="config.instructions"
            rows="4"
            class="textarea textarea-bordered textarea-sm w-full resize-y"
            placeholder="Examples: close tasks completed more than 7 days ago; move blocked cards to On hold; keep at most 3 tasks in Doing…"
          ></textarea>
        </label>
      </div>

      <!-- Runtime status -->
      <div class="rounded-lg border border-base-content/10 p-3 flex flex-col gap-2">
        <div class="flex items-center gap-2">
          <span class="text-xs font-semibold">Status</span>
          <span class="badge badge-xs" :class="statusBadgeClass">{{ statusLabel }}</span>
          <span
            v-if="workerPresent === false"
            class="badge badge-xs badge-warning badge-outline ml-auto"
            title="The background worker is not running; Run now will be queued but not executed"
          >
            <i class="fa-solid fa-triangle-exclamation text-[9px]"></i> worker offline
          </span>
          <span v-else class="text-[10px] text-base-content/35 ml-auto">background worker online</span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
          <div class="flex flex-col">
            <span class="text-base-content/40">Last run</span>
            <span class="font-medium">{{ state.last_finished_at ? when(state.last_finished_at) : 'Never' }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-base-content/40">Next run</span>
            <span class="font-medium">{{ config.enabled ? (nextRunAt ? when(nextRunAt) : 'pending') : 'disabled' }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-base-content/40">Runs</span>
            <span class="font-medium tabular-nums">{{ state.runs || 0 }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-base-content/40">Cost</span>
            <span class="font-medium tabular-nums">{{ formatCost(state.total_cost) }} cxj</span>
          </div>
        </div>

        <div v-if="state.last_error" class="text-[11px] text-error flex items-start gap-1">
          <i class="fa-solid fa-circle-exclamation text-[10px] mt-0.5 shrink-0"></i>
          <span class="break-words">{{ state.last_error }}</span>
        </div>

        <div
          v-if="state.last_report"
          class="mt-1 rounded-md bg-base-200/60 p-2.5 text-[11px] text-base-content/65 whitespace-pre-wrap max-h-56 overflow-y-auto"
        >{{ state.last_report }}</div>
        <p v-else class="text-[11px] text-base-content/35 italic">
          No review has run yet. Save the configuration and press Run now.
        </p>

        <div v-if="state.last_actions?.length" class="mt-1">
          <div class="text-[10px] uppercase tracking-wider text-base-content/40 mb-1">Last actions</div>
          <ul class="flex flex-col gap-1 max-h-40 overflow-y-auto">
            <li
              v-for="(action, index) in state.last_actions"
              :key="index"
              class="flex items-start gap-1.5 text-[11px]"
            >
              <i
                :class="action.error
                  ? 'fa-solid fa-circle-exclamation text-error'
                  : (action.applied ? 'fa-solid fa-circle-check text-success' : 'fa-solid fa-lightbulb text-warning')"
                class="text-[9px] mt-0.5 shrink-0"
              ></i>
              <span class="min-w-0">
                <span class="font-medium">{{ action.task_name || action.task_id || action.type }}</span>
                <span class="text-base-content/50"> — {{ action.summary || action.error }}</span>
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center gap-2 w-full">
        <button
          type="button"
          class="btn btn-sm btn-ghost gap-1.5"
          :disabled="!config.enabled || state.running || state.wake_requested"
          :title="!config.enabled ? 'Enable the manager first' : 'Queue an immediate review'"
          @click="runNow"
        >
          <i
            class="text-xs"
            :class="state.running || state.wake_requested
              ? 'fa-solid fa-spinner animate-spin'
              : 'fa-solid fa-play'"
          ></i>
          {{ state.running ? 'Running…' : (state.wake_requested ? 'Queued…' : 'Run now') }}
        </button>
        <span class="grow"></span>
        <button type="button" class="btn btn-sm btn-ghost" @click="$emit('close')">Cancel</button>
        <button type="button" class="btn btn-sm btn-primary gap-1.5" @click="save">
          <i class="fa-solid fa-save text-xs"></i> Save
        </button>
      </div>
    </template>
  </modal>
</template>

<script>
import moment from 'moment'

const DEFAULT_CONFIG = () => ({
  enabled: false,
  profile: '',
  mode: 'apply',
  interval_minutes: 60,
  max_actions: 5,
  max_tasks: 80,
  include_done: false,
  instructions: ''
})

const DEFAULT_STATE = () => ({
  running: false,
  wake_requested: false,
  runs: 0,
  last_run_at: '',
  last_finished_at: '',
  last_status: '',
  last_error: '',
  last_summary: '',
  last_report: '',
  last_cost: 0,
  total_cost: 0,
  last_actions: []
})

export default {
  name: 'BoardManagerModal',
  props: {
    board: { type: Object, required: true },
    project: { type: Object, default: null }
  },
  emits: ['close', 'save'],
  data() {
    return {
      config: { ...DEFAULT_CONFIG(), ...(this.board?.manager || {}) },
      state: DEFAULT_STATE(),
      nextRunAt: '',
      workerPresent: true,
      loading: false,
      saving: false,
      pollHandle: null,
      pollTries: 0,
      // The status response may carry a normalized config; it is only used when
      // the board document has no manager block yet, never after the user has
      // started editing.
      configInitialized: !!this.board?.manager
    }
  },
  computed: {
    api() {
      return this.project?.$api || this.$project?.$api || null
    },
    boardProject() {
      return this.$storex.projects.allProjectsById?.[this.board?.project_id] || null
    },
    managerProfileSelection() {
      const name = this.config.profile || this.board?.assignee
      return name ? [{ name }] : []
    },
    statusLabel() {
      if (!this.config.enabled) return 'disabled'
      if (this.state.running) return 'running'
      if (this.state.wake_requested) return 'queued'
      if (this.state.last_status === 'error') return 'error'
      if (this.state.last_status === 'suggested') return 'suggested'
      if (this.state.last_status === 'no_actions') return 'healthy'
      if (this.state.last_status === 'no_tasks') return 'no tasks'
      if (this.state.last_status === 'ok') return 'active'
      return 'idle'
    },
    statusBadgeClass() {
      const label = this.statusLabel
      if (label === 'running' || label === 'queued') return 'badge-primary badge-outline'
      if (label === 'error') return 'badge-error badge-outline'
      if (label === 'suggested') return 'badge-warning badge-outline'
      if (label === 'active' || label === 'healthy') return 'badge-success badge-outline'
      return 'badge-ghost text-base-content/50'
    }
  },
  mounted() {
    this.refreshStatus()
  },
  beforeUnmount() {
    clearInterval(this.pollHandle)
  },
  methods: {
    onProfileSelected(profiles) {
      this.config.profile = profiles?.[0]?.name || ''
    },
    save() {
      const profile = this.config.profile || this.board?.assignee || ''
      this.$emit('save', {
        board: this.board,
        manager: {
          ...this.config,
          profile,
          interval_minutes: Math.max(5, Math.min(10080, Number(this.config.interval_minutes) || 60)),
          max_actions: Math.max(1, Math.min(20, Number(this.config.max_actions) || 5)),
          max_tasks: Math.max(1, Math.min(200, Number(this.config.max_tasks) || 80))
        }
      })
    },
    async refreshStatus() {
      if (!this.api?.kanban?.manager?.status) return
      this.loading = true
      try {
        const response = await this.api.kanban.manager.status()
        const entry = (response?.boards || []).find(item =>
          item.board === this.board?.title || item.board_id === this.board?.id
        )
        if (!entry) return
        this.workerPresent = response.worker_present
        this.nextRunAt = entry.next_run_at || ''
        this.state = { ...DEFAULT_STATE(), ...(entry.state || {}) }
        if (!this.configInitialized && entry.config) {
          this.config = { ...DEFAULT_CONFIG(), ...entry.config }
          this.configInitialized = true
        }
      } catch (error) {
        console.error('[BoardManagerModal] Could not load the manager status:', error)
      } finally {
        this.loading = false
      }
    },
    async runNow() {
      if (!this.api?.kanban?.manager?.run) return
      this.pollTries = 0
      try {
        const response = await this.api.kanban.manager.run(this.board.title)
        if (response?.state) this.state = { ...DEFAULT_STATE(), ...response.state }
        this.workerPresent = response?.worker_present ?? this.workerPresent
        this.$ui?.addNotification?.({
          text: this.workerPresent
            ? 'Board manager review queued'
            : 'Review queued, but the background worker is not running'
        })
        this.poll()
      } catch (error) {
        this.$ui?.addNotification?.({ text: error?.message || 'Could not queue the review', type: 'error' })
      }
    },
    poll() {
      clearInterval(this.pollHandle)
      this.pollHandle = setInterval(async () => {
        this.pollTries += 1
        await this.refreshStatus()
        // Keep polling while a review is running (it can take a few minutes);
        // a queued review that never starts is abandoned after ~60s.
        if (!this.state.running && !this.state.wake_requested) {
          clearInterval(this.pollHandle)
          this.pollHandle = null
        } else if (!this.state.running && this.pollTries >= 24) {
          clearInterval(this.pollHandle)
          this.pollHandle = null
        }
      }, 2500)
    },
    when(value) {
      if (!value) return ''
      const date = moment(value)
      return date.isValid() ? date.fromNow() : ''
    },
    formatCost(value) {
      const number = Number(value || 0)
      if (!number) return '0'
      return number < 0.01 ? number.toFixed(4) : number.toFixed(2)
    }
  }
}
</script>
