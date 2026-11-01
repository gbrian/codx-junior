<script setup>
import ChatInputBox from '@/components/chat/ChatInputBox.vue'
import ChatAttachmentPreview from '@/components/chat/ChatAttachmentPreview.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
</script>

<template>
  <modal close :fullscreen="isMobile" @close="$emit('close')">
    <template #header>
      <h2 class="min-w-0 flex items-center gap-2 font-semibold text-sm md:text-base">
        <!-- The avatar identifies who answers the chat: the profile that
             assists managers (ProjectManager), same icon as the entry button -->
        <div class="avatar shrink-0" v-if="assistantAvatar">
          <div class="w-6 rounded-full bg-base-300">
            <img :src="assistantAvatar" :alt="assistantName" />
          </div>
        </div>
        <i v-else class="fa-solid fa-comment-dots text-primary text-xs"></i>

        <span class="shrink-0">Quick chat</span>

        <span
          v-if="assistantName"
          class="badge badge-xs badge-primary gap-1 min-w-0"
          :title="`Assistant: ${assistantName}`"
        >
          <span class="truncate max-w-[9rem]">{{ assistantName }}</span>
        </span>

        <span
          v-if="boardName"
          class="badge badge-xs badge-ghost gap-1 min-w-0 hidden sm:inline-flex"
        >
          <i class="fa-solid fa-table-columns text-[8px]"></i>
          <span class="truncate max-w-[10rem]">{{ boardName }}</span>
        </span>
      </h2>
    </template>

    <div class="p-1 flex flex-col gap-3">
      <!-- ── Project the chat is registered in ─────────────────────────────────
           A chat always belongs to ONE project. The project is ALWAYS visible
           and ALWAYS changeable: it is preselected when the board is scoped to
           a single project, and it must be chosen when the board spans several
           (there is no safe default between them). -->
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-semibold uppercase tracking-wider text-base-content/50">
            Project
          </span>

          <span v-if="needsProjectChoice" class="badge badge-xs badge-warning gap-1">
            <i class="fa-solid fa-triangle-exclamation text-[8px]"></i> required
          </span>
          <span v-else-if="scope.length > 1" class="badge badge-xs badge-ghost gap-1">
            <i class="fa-solid fa-table-columns text-[8px]"></i>
            {{ scope.length }} on this board
          </span>
          <span v-else class="badge badge-xs badge-ghost gap-1">
            <i class="fa-solid fa-lock text-[8px]"></i> board project
          </span>
        </div>

        <!-- Same project tree selector used by the top bar: shows the project
             in use and opens the hierarchy (parent / children / others) to
             change it. -->
        <ProjectDetailt
          :model-value="targetProject"
          placeholder="Choose a project"
          @update:model-value="onProjectSelected"
        />

        <p
          class="text-[11px] flex items-start gap-1"
          :class="needsProjectChoice ? 'text-warning' : 'text-base-content/40'"
        >
          <i
            class="text-[10px] mt-0.5 shrink-0"
            :class="needsProjectChoice ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-info'"
          ></i>
          <span>{{ projectHint }}</span>
        </p>
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
      // Project the user chose (null = no choice made yet)
      selectedProject: null,
      // Profile that answers the chat (avatar in the header, preselected)
      assistantProfile: null,
      profiles: [],
      selectedProfiles: [],
      model: null,
      attachments: [],
      cursorWord: {},
      creating: false,
      maxAttachmentSizeMB: MAX_ATTACHMENT_SIZE_MB
    }
  },
  created() {
    // Profiles already fetched per project id (the assistant and the composer
    // share them, so a project is never listed twice)
    this.profilesCache = {}
    // A board scoped to a single project needs no decision: preselect it so the
    // chat can be created in one keystroke.
    this.selectedProject = this.scope.length === 1 ? this.scope[0] : null
    this.loadProfiles()
    this.loadAssistantProfile()
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
    // Several projects in the board and none chosen yet: a decision is required
    needsProjectChoice() {
      return this.scope.length > 1 && !this.selectedProject
    },
    // Project the chat is finally registered in
    targetProject() {
      if (this.selectedProject) return this.selectedProject
      if (this.scope.length === 1) return this.scope[0]
      // No project on the board: fall back to the active one (stated in the UI)
      if (!this.scope.length) return this.$project || null
      // Several projects, none chosen → nothing to register the chat in
      return null
    },
    // Profile the chat talks to (its avatar is the assistant icon)
    wantedAssistant() {
      return (this.defaultProfiles || [])[0] || 'ProjectManager'
    },
    assistant() {
      return this.assistantProfile || this.selectedProfiles[0] || null
    },
    assistantAvatar() {
      return this.assistant?.avatar_url || this.assistant?.avatar || null
    },
    assistantName() {
      return this.assistant?.name || this.wantedAssistant
    },
    aiModels() {
      return this.$storex.projects.ai?.models || []
    },
    // Column the chat lands in (kanban). Sprint boards resolve it themselves.
    destinationColumn() {
      const column = (this.columns || []).find(col => !col.virtual)
      return column?.value || column?.title || null
    },
    // Explains which project the chat goes to and how to change it
    projectHint() {
      if (this.needsProjectChoice) {
        return `This board spans ${this.scope.length} projects — choose where this chat is registered. `
          + 'That project provides its profiles, files and AI model.'
      }
      if (!this.targetProject?.project_id) {
        return 'No project available — open a project first.'
      }
      if (!this.scope.length) {
        return `No project on this board — using the active project (${this.targetProject.project_name}). `
          + 'Change it above.'
      }
      return `Registered in ${this.targetProject.project_name} — its profiles, files and AI model. `
        + 'Change it above.'
    },
    hint() {
      if (this.needsProjectChoice) return 'Choose the project to continue'
      if (!this.targetProject?.project_id) return 'No project available'
      if (this.creating) return 'Creating the chat…'
      return 'Added to this board'
    },
    canSubmit() {
      return !this.creating && !this.needsProjectChoice && !!this.targetProject?.project_id
    }
  },
  watch: {
    // A different project brings different profiles (and its ProjectManager)
    targetProject() {
      this.loadProfiles()
      this.loadAssistantProfile()
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
    // Profiles of a project, fetched once and shared by the composer and the
    // assistant avatar.
    async profilesFor(project) {
      const id = project?.project_id
      if (!id) return []
      if (this.profilesCache[id]) return this.profilesCache[id]
      const api = project.$api || project.api
      let list = []
      try {
        list = await api?.profiles?.list?.() || []
      } catch (error) {
        console.error('[BoardQuickChat] Could not load profiles:', error)
      }
      this.profilesCache[id] = [...list].sort((a, b) => (a.name > b.name ? 1 : -1))
      return this.profilesCache[id]
    },
    async loadProfiles() {
      const project = this.targetProject
      if (!project?.project_id) return
      const list = await this.profilesFor(project)
      // A slower response for a previous project must not overwrite the current
      if (project.project_id !== this.targetProject?.project_id) return
      this.profiles = list
      // Preselect the profiles that assist this kind of user
      this.selectedProfiles = (this.defaultProfiles || [])
        .map(name => list.find(profile => profile.name === name))
        .filter(Boolean)
    },
    // Avatar of the profile that answers: taken from the project the chat is
    // registered in, or from the active project while no project is chosen.
    async loadAssistantProfile() {
      const project = this.targetProject || this.$project
      const list = await this.profilesFor(project)
      this.assistantProfile = list.find(profile => profile.name === this.wantedAssistant) || null
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
      if (this.needsProjectChoice) {
        this.$ui?.addNotification?.({
          text: 'This board spans several projects — choose one for the chat',
          type: 'warning'
        })
        return
      }
      if (!this.targetProject?.project_id) {
        this.$ui?.addNotification?.({ text: 'No project selected for this chat', type: 'warning' })
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