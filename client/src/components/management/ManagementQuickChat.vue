<script setup>
import Modal from '@/components/Modal.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import AssistantAvatar from './AssistantAvatar.vue'
import ChatInputBox from '@/components/chat/ChatInputBox.vue'
import ChatAttachmentPreview from '@/components/chat/ChatAttachmentPreview.vue'
import ChatAttachment from '@/api/model/ChatAttachment.js'
import { findAssistantProfile, loadProjectProfiles } from '@/views/management/useAssistantProfile'
</script>

<template>
  <!--
    Assistant chat of the management dashboard.

    A chat ALWAYS belongs to ONE project, and the dashboard is a multi-project
    view. So the project is never implicit:

      • dashboard filtered to ONE project  → it is preselected (zero clicks),
      • dashboard filtered to SEVERAL      → the project is REQUIRED and the
        action stays disabled until one is chosen (no silent default between
        projects, which is what breaks multi-project views),
      • no project in the filter           → every project is offered, and the
        caption says so.

    The project is always visible and always changeable through the project tree
    selector used by the top bar.
  -->
  <Modal close :fullscreen="isMobile" @close="$emit('close')">
    <template #header>
      <h2 class="min-w-0 flex items-center gap-2 font-semibold text-sm md:text-base">
        <!-- The avatar identifies who answers and is repeated next to the name -->
        <AssistantAvatar :project="avatarProject" :profile-name="wantedAssistant" />

        <span class="shrink-0">Assistant chat</span>

        <span
          class="badge badge-xs badge-primary min-w-0"
          :title="`Assistant: ${assistantName}`"
        >
          <span class="truncate max-w-[9rem]">{{ assistantName }}</span>
        </span>

        <span
          v-if="targetProject && targetProject.project_name"
          class="badge badge-xs badge-ghost gap-1 min-w-0 hidden sm:inline-flex"
        >
          <i class="fa-solid fa-cube text-[8px]"></i>
          <span class="truncate max-w-[10rem]">{{ targetProject.project_name }}</span>
        </span>
      </h2>
    </template>

    <div class="flex flex-col gap-3">
      <!-- ── Project the chat is registered in ─────────────────────────────── -->
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <label class="text-[11px] font-semibold uppercase tracking-wider opacity-50">
            Project
          </label>

          <span v-if="needsProjectChoice" class="badge badge-xs badge-warning gap-1">
            <i class="fa-solid fa-triangle-exclamation text-[8px]"></i> required
          </span>
          <span v-else-if="availableProjects.length > 1" class="badge badge-xs badge-ghost gap-1">
            <i class="fa-solid fa-layer-group text-[8px]"></i>
            {{ availableProjects.length }} in scope
          </span>
          <span v-else class="badge badge-xs badge-ghost gap-1">
            <i class="fa-solid fa-lock text-[8px]"></i> dashboard scope
          </span>
        </div>

        <!-- Same project tree selector as the top bar: it shows the project in
             use and opens the hierarchy (parent / children / others + search) to
             change it. -->
        <ProjectDetailt
          :model-value="targetProject"
          placeholder="Choose a project"
          @update:model-value="onProjectSelected"
        />

        <p
          class="text-[11px] flex items-start gap-1"
          :class="needsProjectChoice ? 'text-warning' : 'opacity-50'"
        >
          <i
            class="text-[10px] mt-0.5 shrink-0"
            :class="needsProjectChoice ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-info'"
          ></i>
          <span>{{ projectHint }}</span>
        </p>
      </div>

      <!-- ── Message ───────────────────────────────────────────────────────── -->
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

      <!-- ── Attachments ───────────────────────────────────────────────────── -->
      <ChatAttachmentPreview
        v-if="attachments.length"
        :attachments="attachments"
        @remove-attachment="removeAttachment"
      />

      <!-- ── Actions ───────────────────────────────────────────────────────── -->
      <div class="flex items-center gap-2">
        <span
          class="mr-auto min-w-0 text-[11px] flex items-center gap-1"
          :class="needsProjectChoice ? 'text-warning' : 'opacity-50'"
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
  </Modal>
</template>

<script>
// Attachments travel inline as base64 — keep them reasonably small
const MAX_ATTACHMENT_SIZE_MB = 50

export default {
  name: 'ManagementQuickChat',
  props: {
    // Projects of the dashboard, normalised as `{ id, name, color, icon }`
    projects: { type: Array, default: () => [] },
    // Projects currently selected in the dashboard filter
    selectedProjectIds: { type: Array, default: () => [] },
    // Profile that assists managers — preselected on the new chat
    defaultProfiles: { type: Array, default: () => ['ProjectManager'] }
  },
  emits: ['close', 'created'],
  data() {
    return {
      // Project the user chose (null = no choice made yet)
      selectedProjectId: null,
      profiles: [],
      selectedProfiles: [],
      // Profile that answers the chat (avatar in the header)
      assistantProfile: null,
      model: null,
      attachments: [],
      cursorWord: {},
      creating: false,
      maxAttachmentSizeMB: MAX_ATTACHMENT_SIZE_MB
    }
  },
  created() {
    // A dashboard scoped to a single project needs no decision: preselect it so
    // the chat can be created with one keystroke.
    if (this.availableProjects.length === 1) {
      this.selectedProjectId = this.availableProjects[0].id
    }
    this.loadProfiles()
    this.loadAssistantProfile()
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    // Projects the chat can be registered in. The dashboard filter is the
    // default scope; an empty selection means "nothing filtered", so every
    // project the dashboard knows are offered instead of blocking the chat.
    availableProjects() {
      const all = this.projects || []
      const ids = this.selectedProjectIds || []
      if (!ids.length) return all
      const scoped = all.filter(project => ids.includes(project.id))
      return scoped.length ? scoped : all
    },
    // Several projects in scope and none chosen yet: a decision is required
    needsProjectChoice() {
      return !this.selectedProjectId && this.availableProjects.length > 1
    },
    // Project id the chat is finally registered in
    targetProjectId() {
      if (this.selectedProjectId) return this.selectedProjectId
      if (this.availableProjects.length === 1) return this.availableProjects[0].id
      return null
    },
    // Project the chat is finally registered in, as the store knows it (the
    // selector needs `project_name` / `abs_project_path` to build the tree)
    targetProject() {
      const id = this.targetProjectId
      if (!id) return null
      const live = this.$storex?.projects?.allProjectsById?.[id]
      if (live) return live
      const found = (this.projects || []).find(project => project.id === id)
      if (!found) return null
      return {
        project_id: found.id,
        project_name: found.name,
        project_color: found.color || null,
        project_icon: found.icon || null
      }
    },
    // Project that provides the assistant identity while no project is chosen
    avatarProject() {
      if (this.targetProject) return this.targetProject
      const first = this.availableProjects[0]
      if (!first) return null
      return this.$storex?.projects?.allProjectsById?.[first.id] || first
    },
    // Profile the chat talks to
    wantedAssistant() {
      return (this.defaultProfiles || [])[0] || 'ProjectManager'
    },
    assistantName() {
      return this.assistantProfile?.name || this.wantedAssistant
    },
    aiModels() {
      return this.$storex.projects.ai?.models || []
    },
    // Explains which project the chat goes to and how to change it
    projectHint() {
      if (this.needsProjectChoice) {
        return `This dashboard spans ${this.availableProjects.length} projects — choose where this chat is registered. `
          + 'That project provides its profiles, files and AI model.'
      }
      if (!this.targetProject) {
        return 'No project available — open a project first.'
      }
      const scope = (this.selectedProjectIds || []).length
      if (!scope) {
        return `Nothing filtered in the dashboard — every project is offered. Chat registered in ${this.targetProject.project_name}.`
      }
      return `Registered in ${this.targetProject.project_name} — its profiles, files and AI model. `
        + 'Change it above.'
    },
    hint() {
      if (this.needsProjectChoice) return 'Choose the project to continue'
      if (!this.targetProject) return 'No project available'
      if (this.creating) return 'Creating the chat…'
      return 'Opens the conversation right away'
    },
    canSubmit() {
      return !this.creating && !this.needsProjectChoice && !!this.targetProject?.project_id
    }
  },
  watch: {
    // A different project brings different profiles (and its own ProjectManager)
    targetProjectId() {
      this.loadProfiles()
      this.loadAssistantProfile()
    }
  },
  methods: {
    // ── Project ─────────────────────────────────────────────────────────────
    onProjectSelected(project) {
      const selected = typeof project === 'string'
        ? this.$storex.projects.allProjectsById[project]
        : project
      const id = selected?.project_id || selected?.id
      if (!id) return
      this.selectedProjectId = id
    },
    async loadProfiles() {
      const project = this.targetProject
      if (!project) {
        this.profiles = []
        this.selectedProfiles = []
        return
      }
      const list = await loadProjectProfiles(project)
      // A slower response for a previous project must not overwrite the current
      if ((this.targetProject?.project_id || null) !== (project.project_id || null)) return
      this.profiles = list
      // Preselect the profile that assists management
      this.selectedProfiles = (this.defaultProfiles || [])
        .map(name => findAssistantProfile(list, name))
        .filter(Boolean)
    },
    async loadAssistantProfile() {
      const list = await loadProjectProfiles(this.avatarProject)
      this.assistantProfile = findAssistantProfile(list, this.wantedAssistant)
    },
    onProfilesSelected(profiles) {
      this.selectedProfiles = profiles || []
    },

    // ── Composer ────────────────────────────────────────────────────────────
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
        console.error('[ManagementQuickChat] Failed to process attachment:', error)
        this.$ui?.addNotification?.({ text: 'Failed to process file', type: 'error' })
        return null
      }
    },
    removeAttachment(index) {
      this.attachments.splice(index, 1)
    },

    // ── Create ──────────────────────────────────────────────────────────────
    submit(run) {
      if (this.creating) return
      const message = (this.$refs.composer?.getEditorText() || '').trim()
      if (!message) {
        this.$ui?.addNotification?.({ text: 'Write a message to start the chat', type: 'warning' })
        return
      }
      if (this.needsProjectChoice) {
        this.$ui?.addNotification?.({
          text: 'This dashboard spans several projects — choose one for the chat',
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
    // Same contract as the QuickChat view: the conversation is created in the
    // chosen project (`owner_project_id` + `project_id`) so it belongs to it,
    // and it is filed under the `quick-chat` board so quick conversations stay
    // together instead of polluting the project boards.
    async createChat({ message, run }) {
      const project = this.targetProject
      this.creating = true
      try {
        const profiles = this.selectedProfiles.map(profile => profile.name || profile)
        const userMessage = this.$service.chat.getUserMessage({
          message,
          files: [],
          profiles,
          // `getUserMessage` does not forward attachments: they travel in the
          // message metadata so nothing the user attached is lost.
          metadata: this.attachmentMetadata(),
          user: this.$user?.username
        })

        const chat = await this.$chats.createNewChat({
          name: this.chatName(message),
          mode: 'chat',
          board: 'quick-chat',
          profiles,
          llm_model: this.model || undefined,
          owner_project_id: project.project_id,
          project_id: project.project_id,
          messages: [userMessage]
        })

        if (!chat?.id) {
          this.$ui?.addNotification?.({ text: 'Could not create the chat', type: 'error' })
          return
        }

        // Persist the project/message selection like the QuickChat view does
        await this.$chats.saveChatInfo(chat)

        // "Chat" starts the assistant right away; "Add" only files the chat
        if (run) await this.$storex.projects.chatWihProject(chat)

        this.$refs.composer?.setEditorText('')
        this.attachments = []
        this.$emit('created', chat)

        // Open the conversation (its own panel on desktop, the chat route on
        // mobile) so the manager lands in the answer, not in a closed dialog.
        this.$ui.openChat(chat)
      } catch (error) {
        console.error('[ManagementQuickChat] Could not create the chat:', error)
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
    // Chat name: the beginning of the message, on a single line
    chatName(message) {
      const text = `${message || ''}`.replace(/\s+/g, ' ').trim()
      return text.length > 60 ? `${text.slice(0, 60)}…` : (text || 'Assistant chat')
    }
  }
}
</script>