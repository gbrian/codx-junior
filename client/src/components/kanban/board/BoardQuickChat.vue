<script setup>
import ChatInputBox from '@/components/chat/ChatInputBox.vue'
import ChatAttachmentPreview from '@/components/chat/ChatAttachmentPreview.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
</script>

<template>
  <modal close :fullscreen="isMobile" @close="$emit('close')">
    <template #header>
      <h2 class="min-w-0 flex items-center gap-2 font-semibold text-sm md:text-base">
        <i class="fa-solid fa-comment-dots text-primary text-xs"></i>
        <span class="shrink-0">Quick chat</span>
        <span v-if="boardName" class="badge badge-xs badge-ghost gap-1 min-w-0">
          <i class="fa-solid fa-table-columns text-[8px]"></i>
          <span class="truncate max-w-[12rem]">{{ boardName }}</span>
        </span>
      </h2>
    </template>

    <div class="p-1 flex flex-col gap-3">
      <!-- ── Project the chat is registered in ─────────────────────────────────
           A chat always belongs to ONE project. When the board is scoped to a
           single project it is used silently; when it spans several, the user
           must choose one before the chat can be created. -->
      <div v-if="needsProjectChoice" class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50">
            Project
          </span>
          <span class="badge badge-xs badge-warning gap-1">
            <i class="fa-solid fa-triangle-exclamation text-[8px]"></i> required
          </span>
        </div>

        <ProjectDetailt
          :model-value="selectedProject"
          @update:model-value="onProjectSelected"
          @select="onProjectSelected"
        />

        <p class="text-[11px] text-base-content/40 flex items-start gap-1">
          <i class="fa-solid fa-circle-info text-[10px] mt-0.5 shrink-0"></i>
          <span>
            This board spans {{ scope.length }} projects. Choose where this chat is registered —
            that project provides its profiles, files and AI model.
          </span>
        </p>
      </div>

      <div
        v-else
        class="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-base-200 border border-base-100"
      >
        <img
          v-if="targetProject?.project_icon"
          :src="targetProject.project_icon"
          :alt="targetProject.project_name"
          class="w-5 h-5 rounded-md shrink-0"
        />
        <i v-else class="fa-solid fa-folder text-primary text-xs shrink-0"></i>

        <div class="min-w-0 flex-1 flex flex-col">
          <span class="text-xs font-semibold truncate">
            {{ targetProject?.project_name || 'No project' }}
          </span>
          <span class="text-[10px] text-base-content/40 truncate">
            <template v-if="scope.length">
              The board is scoped to this project — the chat is registered here
            </template>
            <template v-else>
              No project on this board — using the active project
            </template>
          </span>
        </div>

        <i class="fa-solid fa-lock text-[10px] text-base-content/30 shrink-0" aria-hidden="true"></i>
      </div>

      <!-- ── Message ─────────────────────────────────────────────────────────── -->
      <ChatInputBox
        ref="composer"
        :waiting="creating"
        :ai-models="aiModels"
        :profiles="profiles"
        :selected-profiles="selectedProfiles"
        :cursor-word="cursorWord"
        @send="submit(true)"
        @keydown="onKeyDown"
        @paste="onPaste"
        @drop="onDrop"
        @model-changed="model = $event"
        @profiles-selected="onProfilesSelected"
        @upload-files="onUploadFiles"
        @update:cursor-word="cursorWord = $event"
      />

      <!-- ── Attachments ─────────────────────────────────────────────────────── -->
      <ChatAttachmentPreview
        v-if="attachments.length"
        :attachments="attachments"
        @remove-attachment="removeAttachment"
      />

      <!-- ── Actions ─────────────────────────────────────────────────────────── -->
      <div class="flex items-center gap-2">
        <span
          v-if="hint"
          class="mr-auto min-w-0 text-[11px] flex items-center gap-1"
          :class="needsProjectChoice ? 'text-warning' : 'text-base-content/40'"
        >
          <i
            class="text-[10px] shrink-0"
            :class="needsProjectChoice ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-info'"
          ></i>
          <span class="truncate">{{ hint }}</span>
        </span>

        <button type="button" class="btn btn-ghost btn-sm" @click="$emit('close')">
          Cancel
        </button>

        <button
          type="button"
          class="btn btn-outline btn-sm gap-1.5"
          :disabled="!canSubmit"
          title="Create the chat without starting it"
          @click="submit(false)"
        >
          <i class="fa-solid fa-plus text-xs"></i> Add
        </button>

        <button
          type="button"
          class="btn btn-primary btn-sm gap-1.5"
          :disabled="!canSubmit"
          title="Create the chat and start it now"
          @click="submit(true)"
        >
          <span v-if="creating" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-solid fa-paper-plane text-xs"></i>
          Chat
        </button>
      </div>
    </div>
  </modal>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'

// Attachments travel inline as base64 — keep them reasonably small
const MAX_ATTACHMENT_SIZE_MB = 50

export default {
  name: 'BoardQuickChat',
  props: {
    // Board the chat is created on (column / sprint membership)
    boardId: { type: String, required: true },
    // 'kanban' | 'sprint' — decides where the new card lands
    boardType: { type: String, default: 'kanban' },
    // Display name of the board (shown in the dialog header)
    boardName: { type: String, default: null },
    // Columns of the board (kanban only): the first real one receives the chat
    columns: { type: Array, default: () => [] },
    // Optional project scope override. When omitted the scope is derived from
    // the board itself (board, its columns and the projects of its tasks).
    projects: { type: Array, default: null },
    // Profiles pre-selected on the new chat. Managers are assisted by the
    // ProjectManager profile, so that is the default.
    defaultProfiles: { type: Array, default: () => ['ProjectManager'] }
  },
  emits: ['close', 'created'],
  data() {
    return {
      selectedProject: null,
      profiles: [],
      selectedProfiles: [],
      // Project whose profiles are loaded (avoids loading them twice)
      profilesProjectId: null,
      model: null,
      attachments: [],
      cursorWord: {},
      creating: false,
      maxAttachmentSizeMB: MAX_ATTACHMENT_SIZE_MB
    }
  },
  created() {
    // A board scoped to a single project needs no decision: preselect it so the
    // chat can be created in one keystroke.
    this.selectedProject = this.scope.length === 1 ? this.scope[0] : null
    this.loadProfiles()
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    // Projects the board is scoped to: the board itself, the projects its
    // columns define and the projects of the tasks already on it.
    scope() {
      if (this.projects) return this.projects.filter(project => !!project?.project_id)

      const board = this.$storex.kanban.boardById(this.boardId)
      if (!board) return []

      const ids = new Set()
      if (board.project_id) ids.add(board.project_id)

      const columns = board.columns || []
      columns.forEach(column => {
        if (column.project_id) ids.add(column.project_id)
      })

      const tasks = this.boardType === 'sprint'
        ? this.$storex.kanban.sprintBoardChats(this.boardId)
        : this.$storex.kanban.boardChats(this.boardId)
      const list = tasks || []
      list.forEach(task => {
        if (task.project_id) ids.add(task.project_id)
      })

      return [...ids]
        .map(id => this.$storex.projects.allProjectsById[id])
        .filter(Boolean)
    },
    // Several projects in the board: the user has to pick one before chatting
    needsProjectChoice() {
      return this.scope.length > 1 && !this.selectedProject
    },
    // Project the chat is finally registered in
    targetProject() {
      return this.selectedProject || this.scope[0] || this.$project
    },
    aiModels() {
      return this.$storex.projects.ai?.models || []
    },
    // Column the chat lands in (kanban). Sprint boards resolve it themselves.
    destinationColumn() {
      const column = (this.columns || []).find(col => !col.virtual)
      return column?.value || column?.title || null
    },
    hint() {
      if (this.needsProjectChoice) return 'Choose the project this chat belongs to'
      if (!this.targetProject?.project_id) return 'No project available — open a project first'
      if (this.creating) return 'Creating the chat…'
      return 'The chat is added to this board'
    },
    canSubmit() {
      return !this.creating && !this.needsProjectChoice && !!this.targetProject?.project_id
    }
  },
  watch: {
    // A different project brings different profiles (and its ProjectManager)
    targetProject() {
      this.loadProfiles()
    }
  },
  methods: {
    // ── Project ───────────────────────────────────────────────────────────────
    onProjectSelected(project) {
      const selected = typeof project === 'string'
        ? this.$storex.projects.allProjectsById[project]
        : project
      if (!selected?.project_id) return
      this.selectedProject = selected
    },
    async loadProfiles() {
      const project = this.targetProject
      if (!project?.$api) return
      if (this.profilesProjectId === project.project_id) return
      this.profilesProjectId = project.project_id
      try {
        const list = await project.$api.profiles.list()
        this.profiles = (list || []).sort((a, b) => (a.name > b.name ? 1 : -1))
        // Preselect the profiles that assist this kind of user
        this.selectedProfiles = (this.defaultProfiles || [])
          .map(name => this.profiles.find(profile => profile.name === name))
          .filter(Boolean)
      } catch (error) {
        console.error('[BoardQuickChat] Could not load profiles:', error)
        this.profiles = []
        this.selectedProfiles = []
      }
    },
    onProfilesSelected(profiles) {
      this.selectedProfiles = profiles || []
    },

    // ── Composer ──────────────────────────────────────────────────────────────
    // Enter sends (shift+Enter adds a newline), like the chat composer
    onKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.submit(true)
      }
    },
    async onUploadFiles(files) {
      await this.addAttachments(files)
    },
    async onPaste(event) {
      const imageFile = await this.$service.chat.parseImageFromPaste(event)
      if (!imageFile) return
      event.preventDefault()
      await this.addAttachments([imageFile])
    },
    async onDrop(event) {
      const files = Array.from(event.dataTransfer?.files || [])
      if (files.length) await this.addAttachments(files)
    },
    async addAttachments(files) {
      for (const file of files || []) {
        const attachment = await this.prepareAttachment(file)
        if (attachment) this.attachments.push(attachment)
      }
    },
    async prepareAttachment(file) {
      if ((file?.size || 0) > this.maxAttachmentSizeMB * 1024 * 1024) {
        this.$ui?.addNotification?.({
          text: `File exceeds maximum size of ${this.maxAttachmentSizeMB}MB`,
          type: 'error'
        })
        return null
      }
      try {
        return await ChatAttachment.fromFile(file)
      } catch (error) {
        console.error('[BoardQuickChat] Failed to process attachment:', error)
        this.$ui?.addNotification?.({ text: 'Failed to process file', type: 'error' })
        return null
      }
    },
    removeAttachment(index) {
      this.attachments.splice(index, 1)
    },

    // ── Create ────────────────────────────────────────────────────────────────
    submit(run) {
      if (this.creating) return
      const message = (this.$refs.composer?.getEditorText() || '').trim()
      if (!message) {
        this.$ui?.addNotification?.({ text: 'Write a message to start the chat', type: 'warning' })
        return
      }
      if (!this.targetProject?.project_id) {
        this.$ui?.addNotification?.({ text: 'No project selected for this chat', type: 'warning' })
        return
      }
      if (this.needsProjectChoice) {
        this.$ui?.addNotification?.({
          text: 'This board spans several projects — choose one for the chat',
          type: 'warning'
        })
        return
      }
      this.createChat({ message, run })
    },
    // The chat is created ON the board and only then tagged with its project:
    // the chat stays owned by the current project (it lives in this board) while
    // `project_id` records the project the work belongs to — the same contract
    // the board already uses for tasks assigned to another project.
    async createChat({ message, run }) {
      this.creating = true
      try {
        const profiles = this.selectedProfiles.map(profile => profile.name || profile)
        const name = this.chatName(message)

        let chat = null
        if (this.boardType === 'sprint') {
          chat = await this.$storex.kanban.newSprintTask({
            name,
            mode: 'chat',
            profiles,
            sprintId: this.boardId
          })
        } else {
          chat = await this.$storex.kanban.newTask({
            name,
            mode: 'chat',
            profiles,
            board: this.boardId,
            column: this.destinationColumn
          })
        }

        if (!chat?.id) {
          this.$ui?.addNotification?.({ text: 'Could not create the chat', type: 'error' })
          return
        }

        const updates = { project_id: this.targetProject.project_id }
        if (this.model) updates.llm_model = this.model
        await this.$storex.chats.updateChatInfo({ chat, updates })

        const userMessage = this.$service.chat.getUserMessage({
          message,
          files: [],
          profiles,
          // `getUserMessage` does not forward attachments: they travel in the
          // message metadata so nothing the user attached is lost.
          metadata: this.attachmentMetadata(),
          user: this.$user?.username
        })
        await this.$storex.chats.addMessage({ chat, message: userMessage })

        // "Chat" starts the agent right away; "Add" only files the card
        if (run) await this.$storex.projects.chatWihProject(chat)

        this.$refs.composer?.setEditorText('')
        this.attachments = []
        this.$emit('created', chat)
      } catch (error) {
        console.error('[BoardQuickChat] Could not create the chat:', error)
        this.$ui?.addNotification?.({ text: 'Could not create the chat', type: 'error' })
      } finally {
        this.creating = false
      }
    },
    attachmentMetadata() {
      if (!this.attachments.length) return undefined
      return {
        attachments: this.attachments.map(attachment => (
          attachment.toJSON ? attachment.toJSON() : attachment
        ))
      }
    },
    // Card name: the beginning of the message, on a single line
    chatName(message) {
      const text = `${message || ''}`.replace(/\s+/g, ' ').trim()
      return text.length > 60 ? `${text.slice(0, 60)}…` : (text || 'Quick chat')
    }
  }
}
</script>
