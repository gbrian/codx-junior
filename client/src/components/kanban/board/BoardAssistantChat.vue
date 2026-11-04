<script setup>
import BoardQuickChat from './BoardQuickChat.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="shrink-0 dropdown dropdown-end">
    <!-- Trigger: the avatar identifies WHO answers this board -->
    <button
      tabindex="0"
      role="button"
      class="btn btn-sm btn-ghost gap-2 border border-base-100"
      :class="assignedName ? 'text-primary' : 'text-base-content/60'"
      :title="triggerTitle"
      :aria-label="triggerTitle"
    >
      <span
        v-if="assistantAvatar"
        class="w-5 h-5 rounded-full overflow-hidden bg-base-300 shrink-0"
      >
        <img :src="assistantAvatar" :alt="assistantName" class="w-full h-full object-cover" />
      </span>
      <i v-else class="fa-solid fa-user-tie text-xs"></i>

      <span class="hidden sm:inline text-xs font-medium max-w-[8rem] truncate">
        {{ assistantName }}
      </span>

      <i class="fa-solid fa-chevron-down text-[10px] opacity-50"></i>
    </button>

    <div
      tabindex="0"
      class="dropdown-content z-40 mt-1 w-80 rounded-box border border-base-100 bg-base-200 shadow-xl"
    >
      <!-- Who answers + which board -->
      <div class="flex items-start gap-2 px-3 py-2.5 border-b border-base-100">
        <div class="w-8 h-8 rounded-full overflow-hidden bg-base-300 shrink-0 flex items-center justify-center">
          <img
            v-if="assistantAvatar"
            :src="assistantAvatar"
            :alt="assistantName"
            class="w-full h-full object-cover"
          />
          <i v-else class="fa-solid fa-user-tie text-xs text-base-content/60"></i>
        </div>
        <div class="flex flex-col min-w-0">
          <span class="text-sm font-semibold truncate">{{ assistantName }}</span>
          <span class="text-[11px] text-base-content/50 truncate">
            {{ assignedName ? 'Board assistant' : 'Default assistant' }}
            <template v-if="boardName"> · {{ boardName }}</template>
          </span>
        </div>
        <span
          class="badge badge-xs shrink-0 ml-auto"
          :class="assignedName ? 'badge-primary' : 'badge-ghost text-base-content/50'"
        >
          {{ assignedName ? 'assigned' : 'default' }}
        </span>
      </div>

      <div class="p-2 flex flex-col gap-2">
        <!-- Start a conversation: the card is created ON the board -->
        <button
          type="button"
          class="btn btn-primary btn-sm gap-2 justify-start"
          :disabled="readOnly"
          :title="readOnly ? 'This board is read-only' : `Start a new chat with ${assistantName}`"
          @click="startNewChat(null)"
        >
          <i class="fa-solid fa-comment-dots text-xs"></i>
          New chat
        </button>

        <!-- Typical support-bot asks (seeded into the composer) -->
        <div class="flex flex-wrap gap-1">
          <button
            v-for="prompt in quickPrompts"
            :key="prompt.label"
            type="button"
            class="btn btn-xs btn-ghost border border-base-100 gap-1 normal-case"
            :disabled="readOnly"
            :title="prompt.message"
            @click="startNewChat(prompt.message)"
          >
            <i :class="prompt.icon" class="text-[10px]"></i>
            {{ prompt.label }}
          </button>
        </div>

        <!-- Continue an existing board conversation -->
        <div class="flex items-center gap-2 mt-1">
          <span class="text-[10px] uppercase tracking-wider text-base-content/40">Continue</span>
          <div class="grow h-px bg-base-100"></div>
          <span v-if="hasSupportChats" class="badge badge-xs badge-ghost">{{ supportChats.length }}</span>
        </div>

        <div v-if="hasSupportChats" class="flex flex-col gap-0.5 max-h-56 overflow-y-auto pr-0.5">
          <button
            v-for="chat in supportChats"
            :key="chat.id"
            type="button"
            class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-base-content/10 focus:bg-base-content/10 outline-none transition-colors"
            :title="chat.name"
            @click="openChat(chat)"
          >
            <ChatIcon :mode="chat.mode" class="text-xs shrink-0 text-base-content/50" />
            <span class="flex-1 min-w-0">
              <span class="block text-xs truncate">{{ chat.name || 'Untitled chat' }}</span>
              <span class="block text-[10px] text-base-content/40">{{ whenLabel(chat.updated_at) }}</span>
            </span>
            <i class="fa-solid fa-arrow-right text-[10px] text-base-content/30 shrink-0"></i>
          </button>
        </div>

        <p v-else class="text-[11px] text-base-content/30 italic px-1">
          No conversations yet — start the first one.
        </p>

        <!-- Who answers is a board setting -->
        <button
          type="button"
          class="btn btn-ghost btn-xs gap-1.5 justify-start text-base-content/40 hover:text-primary mt-1"
          @click="onEditBoard"
        >
          <i class="fa-solid fa-user-gear text-[10px]"></i>
          Change the board assistant
        </button>
      </div>
    </div>

    <!-- New chat: created ON the board (its first column), so it can be
         continued from the board itself -->
    <BoardQuickChat
      v-if="showQuickChat"
      :boardId="boardId"
      :boardType="boardType"
      :boardName="boardName"
      :columns="columns"
      :defaultProfiles="newChatProfiles"
      :initialMessage="initialMessage"
      @close="showQuickChat = false"
      @created="onCreated"
    />
  </div>
</template>

<script>
// Profile that answers a board which defines no assignee of its own
const DEFAULT_ASSISTANT = 'ProjectManager'

// Typical support-bot asks. They are seeded into the composer of the new chat,
// so the user can send them, edit them or ignore them.
const QUICK_PROMPTS = [
  {
    label: 'Status',
    icon: 'fa-solid fa-list-check',
    message: 'Summarize the status of this board: what is in progress, what is blocked and what is missing to finish it.'
  },
  {
    label: 'Risks',
    icon: 'fa-solid fa-triangle-exclamation',
    message: 'Which tasks on this board look at risk (overdue, unassigned, stalled)? Tell me what you would do about them.'
  },
  {
    label: 'Next steps',
    icon: 'fa-solid fa-route',
    message: 'Review this board and propose the next steps, ordered by priority.'
  }
]

export default {
  name: 'BoardAssistantChat',
  props: {
    // Board the conversations belong to (kept null-safe: the view may have none)
    boardId: { type: String, default: null },
    // 'kanban' | 'sprint' — decides where a new chat card lands
    boardType: { type: String, default: 'kanban' },
    // Display name of the board (shown in the dropdown header)
    boardName: { type: String, default: null },
    // Board columns: the first real one receives the new chat card
    columns: { type: Array, default: () => [] },
    // Project used to resolve the assistant profile (avatar / description)
    project: { type: Object, default: null },
    // The virtual "Unassigned" board cannot create tasks
    readOnly: { type: Boolean, default: false }
  },
  emits: ['open-chat', 'created', 'edit-board'],
  data() {
    return {
      // Resolved profile of the assistant (its avatar is the button icon)
      profile: null,
      // Project + assistant the profile was resolved for (avoids refetching)
      loadedKey: null,
      showQuickChat: false,
      // Prompt seeded into the new chat composer
      initialMessage: null,
      quickPrompts: QUICK_PROMPTS
    }
  },
  created() {
    this.loadAssistant()
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    // Profile the board is assigned to (board settings → board assistant)
    assigned() {
      if (!this.boardId) return null
      return this.$storex.kanban.boardAssignee(this.boardId)
    },
    assignedName() {
      return this.assigned?.name || null
    },
    // Who answers: the board assignee, or the default assistant
    assistantName() {
      return this.assignedName || DEFAULT_ASSISTANT
    },
    // Profiles pre-selected on a chat created from here
    newChatProfiles() {
      return [this.assistantName]
    },
    assistantAvatar() {
      return this.profile?.avatar_url || this.profile?.avatar ||
        this.assigned?.avatar_url || this.assigned?.avatar || null
    },
    // Project the board belongs to (may differ from the active one)
    boardProject() {
      if (!this.boardId) return null
      const board = this.$storex.kanban.boardById(this.boardId)
      return this.$storex.projects.allProjectsById?.[board?.project_id] || null
    },
    triggerTitle() {
      const role = this.assignedName ? 'board assistant' : 'default assistant'
      return `Chat with ${this.assistantName} (${role})`
    },
    // Conversations of this board that talk to a board assistant. They are
    // normal board tasks (mode 'chat'), so they are listed on the board too.
    supportChats() {
      if (!this.boardId) return []
      const tasks = this.boardType === 'sprint'
        ? this.$storex.kanban.sprintBoardChats(this.boardId)
        : this.$storex.kanban.boardChats(this.boardId)
      return (tasks || [])
        .filter(chat => chat?.id && chat.mode === 'chat')
        .filter(chat => (chat.profiles || []).some(name => this.isAssistant(name)))
        .sort((a, b) => (a.updated_at || '') < (b.updated_at || '') ? 1 : -1)
        .slice(0, 6)
    },
    hasSupportChats() {
      return this.supportChats.length > 0
    }
  },
  watch: {
    // Another assignee brings another assistant profile to display
    assistantName() {
      this.loadAssistant()
    },
    // Boards of another project resolve their profiles elsewhere
    boardProject() {
      this.loadAssistant()
    }
  },
  methods: {
    // Profile names are free text: compare them ignoring case ("projectmanager")
    isAssistant(name) {
      const target = `${name || ''}`.trim().toLowerCase()
      return !!target && [this.assistantName, DEFAULT_ASSISTANT]
        .some(known => `${known}`.trim().toLowerCase() === target)
    },
    // Dropdowns close when their trigger loses focus
    closeDropdown() {
      document.activeElement?.blur?.()
    },
    // Resolve the assistant avatar from the project the board belongs to
    async loadAssistant() {
      const project = this.boardProject || this.project || this.$project
      const projectId = project?.project_id || null
      // Without a project the assignee profile (with its own avatar) still works
      if (!projectId) {
        this.profile = this.assigned || null
        return
      }
      const key = `${projectId}:${this.assistantName}`
      if (this.loadedKey === key) return
      this.loadedKey = key
      try {
        const api = project.$api || project.api
        const list = await api?.profiles?.list?.()
        // A slower response for another project/assistant must not win
        if (this.loadedKey !== key) return
        this.profile = (list || []).find(profile => this.isAssistant(profile.name))
          || (this.assignedName ? this.assigned : null)
      } catch (error) {
        console.error('[BoardAssistantChat] Could not load the assistant profile:', error)
        this.profile = this.assignedName ? this.assigned : null
      }
    },
    // Open the "new chat" dialog (optionally seeded with a prompt)
    startNewChat(message) {
      if (this.readOnly) return
      this.closeDropdown()
      this.initialMessage = message || null
      this.showQuickChat = true
    },
    // Continue an existing conversation — opened like any other board task
    openChat(chat) {
      if (!chat?.id) return
      this.closeDropdown()
      this.$emit('open-chat', chat)
    },
    // The chat is already a board card: let the board open it inline
    onCreated(chat) {
      this.showQuickChat = false
      this.initialMessage = null
      this.$emit('created', chat)
    },
    // Assigning the board assistant lives in the board settings dialog
    onEditBoard() {
      this.closeDropdown()
      this.$emit('edit-board')
    },
    // Compact relative timestamp for the conversation list
    whenLabel(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      const minutes = Math.round((Date.now() - date.getTime()) / 60000)
      if (minutes < 1) return 'just now'
      if (minutes < 60) return `${minutes}m ago`
      const hours = Math.round(minutes / 60)
      if (hours < 24) return `${hours}h ago`
      const days = Math.round(hours / 24)
      if (days < 7) return `${days}d ago`
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    }
  }
}
</script>