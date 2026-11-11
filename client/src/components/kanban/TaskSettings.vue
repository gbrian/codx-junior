<script setup>
import ProfileSelector from '../profile/ProfileSelector.vue'
</script>

<template>
  <!-- ── Properties dialog ──
       The fields of a chat/task, grouped in the three decisions the user actually
       makes: WHAT it is (identity), WHERE it lives (organization) and WHO works
       on it (assistant). One column, one label style, one control height — the
       previous flat list of nine identical blocks gave every field the same
       weight, so nothing guided the eye.
       `isEmbedded` keeps the panel usable inside a host pane: no header, no
       footer, no danger zone (the host owns those). -->
  <div class="flex flex-col gap-4 w-full">

    <!-- Header (dialog mode) — the modal can render its own (`hideHeader`) -->
    <header v-if="!isEmbedded && !hideHeader" class="flex items-start gap-3 pb-3 border-b border-base-content/10">
      <div class="w-9 h-9 rounded-lg bg-primary/15 text-primary grid place-items-center shrink-0">
        <i class="fa-solid fa-sliders" aria-hidden="true"></i>
      </div>
      <div class="min-w-0 flex-1">
        <h3 class="text-sm font-semibold text-base-content truncate">{{ title }}</h3>
        <p class="text-[11px] text-base-content/50 truncate font-mono">
          {{ taskData.board || '—' }}
          <span class="mx-1 opacity-50">/</span>{{ taskData.column || 'unassigned' }}
          <template v-if="shortId">
            <span class="mx-1 opacity-50">·</span>{{ shortId }}
          </template>
        </p>
      </div>
      <button
        type="button"
        class="btn btn-xs btn-ghost shrink-0"
        aria-label="Close properties"
        title="Close"
        @click="$emit('close')"
      >
        <i class="fa-solid fa-xmark" aria-hidden="true"></i>
      </button>
    </header>

    <div class="space-y-5" :class="!isEmbedded && 'py-1'">

      <!-- ── Identity ── -->
      <section>
        <h4 class="text-[10px] font-semibold uppercase tracking-[0.08em] text-base-content/45 mb-2">Identity</h4>
        <div class="space-y-3">

          <label class="block">
            <span class="block text-[11px] font-medium text-base-content/60 mb-1">Name</span>
            <input
              v-model="taskData.name"
              type="text"
              placeholder="Chat name"
              class="input input-sm input-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
              :class="!hasName && 'input-error'"
            />
            <span v-if="!hasName" class="block mt-1 text-[11px] text-error">
              A name is required to save.
            </span>
          </label>

          <label class="block">
            <span class="block text-[11px] font-medium text-base-content/60 mb-1">Project</span>
            <select
              v-model="taskData.project_id"
              class="select select-sm select-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
            >
              <option :value="null">{{ $project.project_name }}</option>
              <option v-for="project in projects" :key="project.project_id" :value="project.project_id">
                {{ project.project_name }}
              </option>
            </select>
          </label>

          <label class="block">
            <span class="block text-[11px] font-medium text-base-content/60 mb-1">Mode</span>
            <select
              v-model="taskData.mode"
              class="select select-sm select-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
            >
              <option v-for="mode in modeOptions" :key="mode.value" :value="mode.value">
                {{ mode.label }}
              </option>
            </select>
          </label>
        </div>
      </section>

      <!-- ── Organization ── -->
      <section>
        <h4 class="text-[10px] font-semibold uppercase tracking-[0.08em] text-base-content/45 mb-2">Organization</h4>
        <div class="space-y-3">

          <div class="grid grid-cols-2 gap-2">
            <label class="block">
              <span class="block text-[11px] font-medium text-base-content/60 mb-1">Board</span>
              <select
                v-model="taskData.board"
                class="select select-sm select-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
                :class="!hasBoard && 'select-error'"
              >
                <option v-for="board in boards" :key="board" :value="board">{{ board }}</option>
              </select>
            </label>

            <label class="block">
              <span class="block text-[11px] font-medium text-base-content/60 mb-1">Column</span>
              <select
                v-model="taskData.column"
                class="select select-sm select-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
                :class="!hasColumn && 'select-error'"
              >
                <option v-for="column in columns" :key="column.title" :value="column.title">
                  {{ column.title }}
                </option>
              </select>
            </label>
          </div>
          <p v-if="!hasBoard || !hasColumn" class="text-[11px] text-error">
            Pick a board and a column to save.
          </p>

          <label class="block">
            <span class="block text-[11px] font-medium text-base-content/60 mb-1">Parent chat</span>
            <select
              v-model="taskData.parent_id"
              class="select select-sm select-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
            >
              <option :value="null">None — top level</option>
              <option v-for="chat in orderedChats" :key="chat.id" :value="chat.id">{{ chat.name }}</option>
            </select>
          </label>
        </div>
      </section>

      <!-- ── Assistant ── -->
      <section>
        <h4 class="text-[10px] font-semibold uppercase tracking-[0.08em] text-base-content/45 mb-2">Assistant</h4>
        <div class="space-y-3">

          <!-- Profiles: removable chips, add lives next to the label -->
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[11px] font-medium text-base-content/60">Profiles</span>
              <span class="text-[10px] text-base-content/40 tabular-nums">{{ profileNames.length }}</span>
              <div class="grow"></div>
              <button
                type="button"
                class="btn btn-xs btn-ghost gap-1"
                title="Add profile"
                @click="showProfileSelector = true"
              >
                <i class="fa-solid fa-plus text-[10px]" aria-hidden="true"></i> Add
              </button>
            </div>

            <div v-if="profileNames.length" class="flex flex-wrap gap-1">
              <span
                v-for="profile in profileNames"
                :key="profile"
                class="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-md border border-primary/30 bg-primary/10 text-primary text-[11px] font-medium"
              >
                {{ profile }}
                <button
                  type="button"
                  class="w-4 h-4 grid place-items-center rounded text-primary/60 hover:text-error hover:bg-error/10 transition-colors duration-150"
                  :aria-label="`Remove profile ${profile}`"
                  :title="`Remove ${profile}`"
                  @click="removeProfile(profile)"
                >
                  <i class="fa-solid fa-xmark text-[9px]" aria-hidden="true"></i>
                </button>
              </span>
            </div>
            <p v-else class="text-[11px] text-base-content/40">No profile: the chat uses the project defaults.</p>
          </div>

          <label class="block">
            <span class="block text-[11px] font-medium text-base-content/60 mb-1">AI model</span>
            <select
              v-model="taskData.llm_model"
              class="select select-sm select-bordered w-full bg-base-100 focus:border-primary/50 focus:ring-2 focus:ring-primary/40"
            >
              <option value="">Default</option>
              <option v-for="model in aiModels" :key="model.name" :value="model.name">
                {{ model.name }}{{ model.ai_model ? ` (${model.ai_model})` : '' }}
              </option>
            </select>
          </label>
        </div>
      </section>

      <!-- ── Danger zone (dialog mode only) ──
           Two steps instead of a collapsed section: the destructive action is
           visible, but a single misclick cannot delete the conversation. -->
      <section v-if="!isEmbedded" class="rounded-lg border border-error/25 bg-error/5 px-2.5 py-2">
        <div class="flex items-center gap-2">
          <div class="min-w-0 flex-1">
            <p class="text-xs font-medium text-error">Delete this chat</p>
            <p class="text-[11px] text-base-content/50">Removed with its messages. This cannot be undone.</p>
          </div>
          <template v-if="!confirmingDelete">
            <button type="button" class="btn btn-xs btn-outline btn-error shrink-0" @click="confirmingDelete = true">
              Delete
            </button>
          </template>
          <template v-else>
            <button type="button" class="btn btn-xs btn-ghost shrink-0" @click="confirmingDelete = false">Cancel</button>
            <button type="button" class="btn btn-xs btn-error shrink-0" @click="deleteTask">Confirm</button>
          </template>
        </div>
      </section>
    </div>

    <!-- Footer (dialog mode only) — one primary action, unsaved state spelled out -->
    <footer v-if="!isEmbedded" class="flex items-center gap-2 pt-3 border-t border-base-content/10">
      <span v-if="isDirty" class="inline-flex items-center gap-1.5 text-[11px] text-warning">
        <i class="fa-solid fa-circle text-[6px]" aria-hidden="true"></i>
        Unsaved changes
      </span>
      <div class="grow"></div>
      <button type="button" class="btn btn-sm btn-ghost" @click="$emit('close')">Discard</button>
      <button
        type="button"
        class="btn btn-sm btn-primary gap-1"
        :disabled="!canSave"
        @click="saveChanges"
      >
        <i class="fa-solid fa-floppy-disk text-[11px]" aria-hidden="true"></i>
        Save
      </button>
    </footer>

    <modal close="true" @close="showProfileSelector = false" v-if="showProfileSelector">
      <ProfileSelector @select="addProfile($event)" :project="taskProject" />
    </modal>
  </div>
</template>

<script>
export default {
  props: {
    taskData: {
      type: Object,
      required: true
    },
    isEmbedded: {
      type: Boolean,
      default: false
    },
    // Heading used when this component renders its own header
    title: {
      type: String,
      default: 'Task settings'
    },
    // The host dialog already prints a title + close button (ChatView's modal
    // header slot): drop the internal one to avoid a duplicated header bar.
    hideHeader: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      showProfileSelector: false,
      confirmingDelete: false,
      // Snapshot of the editable fields, to tell the user there is nothing to save
      snapshot: null
    }
  },
  created() {
    this.snapshot = this.fieldsSnapshot()
  },
  computed: {
    taskAIModel() {
      return this.aiModels.find(m => m.name === this.taskData.llm_model)
    },
    aiModels() {
      return this.$projects.ai.models
    },
    // Boards are plain strings: the previous comparator read `.title` off a
    // string, so the list was never sorted.
    boards() {
      return Object.keys(this.$projects.kanban.boards || {}).sort((a, b) => a.localeCompare(b))
    },
    columns() {
      return this.$projects.kanban.boards?.[this.taskData.board]?.columns || []
    },
    hasName() {
      return !!this.taskData.name?.trim()
    },
    hasBoard() {
      return !!this.taskData.board
    },
    hasColumn() {
      return !!this.taskData.column
    },
    canSave() {
      return this.hasName && this.hasBoard && this.hasColumn
    },
    // `allProjects` is a store array: sorting it in place reordered every other
    // view that reads it. Sort a copy.
    projects() {
      return [...this.$projects.allProjects]
        .sort((a, b) => a.project_name.toLowerCase().localeCompare(b.project_name.toLowerCase()))
    },
    taskProject() {
      if (this.taskData.project_id) {
        return this.projects.find(p => p.project_id === this.taskData.project_id)
      }
      return this.$project
    },
    allChats() {
      return this.$projects.allChats
    },
    // Chats of the current board first, then the rest
    orderedChats() {
      const boardOf = chat => chat.board || chat.board_id
      return this.allChats
        .filter(chat => boardOf(chat) === this.taskData.board)
        .concat(this.allChats.filter(chat => boardOf(chat) !== this.taskData.board))
    },
    // The store owns the list of modes ('chat', 'task', 'agent', …). Using it
    // keeps this dialog from silently rewriting an unsupported mode to ''
    modeOptions() {
      const modes = this.$storex?.chats?.availableChatModes || [
        { value: 'chat', label: 'Chat' },
        { value: 'task', label: 'Task' }
      ]
      const options = modes.map(mode => ({ value: mode.value, label: mode.label || mode.value }))
      // Never hide the mode the chat already has
      if (this.taskData.mode && !options.some(mode => mode.value === this.taskData.mode)) {
        options.unshift({ value: this.taskData.mode, label: this.taskData.mode })
      }
      return options
    },
    profileNames() {
      return this.taskData.profiles || []
    },
    shortId() {
      return this.taskData.id ? String(this.taskData.id).slice(0, 8) : ''
    },
    isDirty() {
      if (!this.snapshot) return false
      return this.fieldsSnapshot() !== this.snapshot
    }
  },
  watch: {
    taskData: {
      handler() {
        this.confirmingDelete = false
        this.snapshot = this.fieldsSnapshot()
        this.ensureValidColumn()
      }
    },
    // Changing the board swaps the column list: keep a column that exists
    'taskData.board'() {
      this.ensureValidColumn()
    }
  },
  methods: {
    fieldsSnapshot() {
      const data = this.taskData || {}
      return JSON.stringify({
        name: data.name || '',
        project_id: data.project_id || null,
        parent_id: data.parent_id || null,
        board: data.board || '',
        column: data.column || '',
        mode: data.mode || '',
        llm_model: data.llm_model || '',
        profiles: [...(data.profiles || [])].sort()
      })
    },
    ensureValidColumn() {
      const columns = this.columns
      if (!columns.length) return
      if (!columns.find(column => column.title === this.taskData.column)) {
        this.taskData.column = ''
      }
    },
    saveChanges() {
      if (!this.canSave) return
      this.$chats.saveChatInfo(this.taskData)
      this.snapshot = this.fieldsSnapshot()
      this.$emit('close')
    },
    deleteTask() {
      this.confirmingDelete = false
      this.$chats.deleteChat(this.taskData)
      this.$emit('close')
    },
    addProfile(profile) {
      if (!profile?.name) return
      if (!this.taskData.profiles) this.taskData.profiles = []
      if (!this.taskData.profiles.includes(profile.name)) {
        this.taskData.profiles.push(profile.name)
      }
      this.showProfileSelector = false
    },
    removeProfile(profile) {
      this.taskData.profiles = (this.taskData.profiles || []).filter(name => name !== profile)
    }
  }
}
</script>