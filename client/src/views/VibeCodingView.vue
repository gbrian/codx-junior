<script setup>
import VibeCodingHeader from '@/components/vibe/VibeCodingHeader.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import ChatPanel from '@/components/vibe/ChatPanel.vue'
import SubtaskModal from '@/components/vibe/modals/SubtaskModal.vue'
import TagModal from '@/components/vibe/modals/TagModal.vue'
import SubtasksModal from '@/components/vibe/modals/SubtasksModal.vue'
import ChangesPanel from '@/components/vibe/panels/ChangesPanel.vue'
import PreviewPanel from '@/components/vibe/panels/PreviewPanel.vue'

import { v4 as uuidv4 } from 'uuid'
</script>

<template>
  <div class="flex flex-col h-full w-full bg-base-300 overflow-hidden">

    <!-- Main header for Vibe Coding -->
    <VibeCodingHeader
      ref="vibeHeader"
      :chat="activeChat"
      :project-name="$project?.project_name"
      :show-chat="showChat"
      :show-changes="showChanges"
      :show-preview="showPreview"
      :active-child-chat="activeChildChat"
      @toggle-view="toggleView"
      @reload="reloadWorkspace"
      @toggle-kanban="showKanbanPanel = !showKanbanPanel"
      @update:chat="onChatMetaUpdated"
      @navigate-to-board="navigateToBoard"
      @navigate-to-parent="navigateToParent"
      @new-subtask="showSubtaskModal = true"
      @select-child-chat="selectChildChat"
      @set-project="setChatProject"
      @add-profile="onAddProfile"
    />

    <!-- Main layout: Chat panel + Code panels -->
    <VerticalSplitter :panels="splitterConfig">
      <template #left v-if="showChat">
        <ChatPanel
          :chat="activeChildChat || activeChat"
          :show-kanban="showKanbanPanel"
          :kanban-params="kanbanParams"
          :filter="chatSearch"
          @kanban-chat-selected="onKanbanChatSelected"
          @close-kanban="showKanbanPanel = false"
          @reload="reloadActiveChat"
          @new-subtask="showSubtaskModal = true"
          @create-subtasks="showSubtasksModal = true"
          @new-tag="showTagModal = true"
          @update:chat="onChatUpdated"
          @update:search="chatSearch = $event"
          @delete-chat="onDeleteChat"
        />
      </template>

      <template #right v-if="showChanges || showPreview">
        <VerticalSplitter :panels="codePanelsSplitterConfig">
          <template #left v-if="showChanges">
            <ChangesPanel
              :chat="activeChat"
              @refresh="refreshChanges"
              @select-branch="onPRBranchSelected"
              @comment="onPRComment"
              @change-column="onChangeColumnFromPR"
              @new-chat="onNewChatFromChanges"
              @chat-message="onPRChatMessage"
            />
          </template>

          <template #right v-if="showPreview">
            <PreviewPanel
              :selected-app="selectedApp"
              :project-apps="projectApps"
              @app-selected="onAppSelected"
              @reload="reloadPreview"
              @open-fullscreen="openPreviewFullscreen"
            />
          </template>
        </VerticalSplitter>
      </template>
    </VerticalSplitter>

    <!-- Modals -->
    <modal v-if="showSubtaskModal" @close="showSubtaskModal = false">
      <SubtaskModal
        @create="createSubTask"
        @close="showSubtaskModal = false"
      />
    </modal>

    <modal v-if="showTagModal" @close="showTagModal = false">
      <TagModal
        @add="addTag"
        @close="showTagModal = false"
      />
    </modal>

    <modal v-if="showSubtasksModal" @close="showSubtasksModal = false">
      <SubtasksModal
        @create="executeCreateSubtasks"
        @close="showSubtasksModal = false"
      />
    </modal>
  </div>
</template>

<script>
export default {
  props: ['chat', 'kanban', 'params'],
  data() {
    return {
      showChat: true,
      showPreview: true,
      showChanges: false,
      showKanbanPanel: false,
      chatSearch: '',
      showSubtaskModal: false,
      showTagModal: false,
      showSubtasksModal: false,
      activeChildChat: null,
      selectedApp: null,
      selectedAppKey: ''
    }
  },
  computed: {
    activeChat() {
      return this.$storex.chats.activeChat
    },
    activeTeam() {
      return this.$storex.teams.activeTeam
    },
    kanbanParams() {
      return this.params || {}
    },
    projectApps() {
      return this.$storex.projects?.projectApps || []
    },
    splitterConfig() {
      return {
        left: { defaultSize: this.$storex.ui.panelWidths.chat, minSize: 15 },
        right: { defaultSize: 100 - this.$storex.ui.panelWidths.chat, minSize: 15 }
      }
    },
    codePanelsSplitterConfig() {
      const changesDefault = this.$storex.ui.panelWidths.changes
      const previewDefault = this.$storex.ui.panelWidths.preview
      const total = changesDefault + previewDefault
      return {
        left: { defaultSize: (changesDefault / total) * 100, minSize: 15 },
        right: { defaultSize: (previewDefault / total) * 100, minSize: 15 }
      }
    }
  },
  watch: {
    '$storex.projects.activeProject'() {
      this.init()
    },
    activeChat(newVal) {
      if (newVal) {
        this.showKanbanPanel = false
        if (newVal !== this.activeChildChat) {
          this.activeChildChat = null
          this.loadChildrenChats()
        }
      }
    },
    projectApps(apps) {
      if (apps?.length && !this.selectedApp) {
        this.autoSelectApp()
      }
    }
  },
  mounted() {
    this.init()
    this.autoSelectApp()
  },
  methods: {
    async init() {
      if (!this.activeChat) {
        this.showKanbanPanel = true
      }
    },
    loadChildrenChats() {
      const children = this.$storex.chats.allChats.filter(c => c.parent_id === this.activeChat.id)
      children.forEach(c => {
        if (!c.messages?.length) {
          this.$storex.chats.loadChat(c)
        }
      })
    },
    toggleView(view) {
      if (view === 'chat') this.showChat = !this.showChat
      else if (view === 'changes') this.showChanges = !this.showChanges
      else if (view === 'preview') this.showPreview = !this.showPreview
    },
    selectChildChat(childChat) {
      this.activeChildChat = childChat
      if (childChat && !childChat.messages?.length) {
        this.$storex.chats.reloadChat(childChat)
      }
    },
    onKanbanChatSelected(chat) {
      if (chat) {
        this.$storex.chats.setActiveChat(chat)
      }
      this.showKanbanPanel = false
    },
    onChatMetaUpdated(updatedChat) {
      if (!updatedChat?.id) return
      Object.assign(this.activeChat, updatedChat)
      this.$storex.chats.saveChat(this.activeChat)
    },
    onChatUpdated(updatedChat) {
      if (!updatedChat?.id) return
      Object.assign(this.activeChat, updatedChat)
      this.$storex.chats.saveChat(this.activeChat)
    },
    onPRBranchSelected({ fromBranch, toBranch, projectId }) {
      if (!this.activeChat || !projectId) return
      const updatedChat = {
        ...this.activeChat,
        meta_data: {
          ...(this.activeChat.meta_data || {}),
          pull_requests: {
            ...(this.activeChat.meta_data?.pull_requests || {}),
            [projectId]: {
              url: '',
              fromBranch,
              toBranch
            }
          }
        }
      }
      Object.assign(this.activeChat, updatedChat)
      this.$storex.chats.saveChat(this.activeChat)
    },
    reloadActiveChat() {
      if (this.activeChat) {
        this.$storex.chats.reloadChat(this.activeChat)
      }
    },
    refreshChanges() {},
    reloadPreview() {},
    openPreviewFullscreen() {},
    reloadWorkspace() {
      this.reloadPreview()
      this.reloadActiveChat()
    },
    navigateToBoard() {
      this.$emit('chats', this.kanban?.title || this.activeChat?.board)
    },
    navigateToParent(parentChat) {
      if (parentChat) {
        this.$storex.chats.setActiveChat(parentChat)
      } else {
        this.navigateToBoard()
      }
    },
    autoSelectApp() {
      if (!this.projectApps?.length) return
      const vncApp = this.projectApps.find(a => a.is_vnc) || this.projectApps[0]
      if (vncApp) {
        this.selectedAppKey = vncApp.key
        this.onAppSelected()
      }
    },
    onAppSelected() {
      const app = this.projectApps.find(a => a.key === this.selectedAppKey)
      this.selectedApp = app ? { app } : null
    },
    createSubTask({ name, mode, description }) {
      if (!name?.trim() || !this.activeChat) return
      this.$storex.chats.createNewChat({
        id: uuidv4(),
        board: this.activeChat.board,
        name,
        mode,
        parent_id: this.activeChat.id,
        project_id: this.activeChat.project_id,
        owner_project_id: this.activeChat.owner_project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        column: this.activeChat.column
      }).then(chat => {
        this.$storex.chats.saveChat(chat)
      })
    },
    addTag(tagName) {
      if (!tagName || !this.activeChat) return
      this.activeChat.tags = [...new Set([...(this.activeChat.tags || []), tagName])]
      this.$storex.chats.saveChat(this.activeChat)
    },
    executeCreateSubtasks(instructions) {
      if (this.activeChat) {
        this.$storex.projects.createSubTasks({
          chat: this.activeChat,
          instructions
        })
      }
    },
    setChatProject(project) {
      if (!this.activeChat) return
      this.activeChat.project_id = project.project_id
      this.$storex.chats.saveChat(this.activeChat)
    },
    onAddProfile(profile) {},
    onPRComment({ chat, title, files, description, profiles, mode, column }) {
      this.$emit('comment', { chat, title, files, description, profiles, mode, column })
    },
    onChangeColumnFromPR({ chats, column }) {
      this.$emit('change-column', { chats, column })
    },
    onNewChatFromChanges(payload) {
      this.$emit('new-chat', payload)
    },
    onPRChatMessage({ file }) {
      if (file.chat?.messages) {
        file.chat.messages.push({})
      }
    },
    async onDeleteChat(chatToDelete) {
      if (!chatToDelete?.id) return
      await this.$storex.chats.deleteChat(chatToDelete)
      if (this.activeChat?.id === chatToDelete.id) {
        const parentChat = this.$storex.chats.chats[chatToDelete.parent_id]
        if (parentChat) {
          await this.$storex.chats.setActiveChat(parentChat)
        } else {
          this.navigateToBoard()
        }
      }
    }
  }
}
</script>