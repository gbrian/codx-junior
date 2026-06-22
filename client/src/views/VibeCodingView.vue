<script setup>
import Chat from '@/components/chat/Chat.vue'
import AppWindow from '@/components/windowManager/AppWindow.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import PRView from '@/components/repo/PRView.vue'
import VibeCodingHeader from '@/components/vibe/VibeCodingHeader.vue'
import KanbanContainer from '@/components/kanban/KanbanContainer.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full bg-base-300 overflow-hidden">

    <VibeCodingHeader
      ref="vibeHeader"
      :chat="activeChat"
      :project-name="$project?.project_name"
      :available-branches="branches"
      :show-chat="showChat"
      :show-changes="showChanges"
      :show-preview="showPreview"
      :active-child-chat="showChildChat"
      :show-hidden-messages="showHidden"
      @toggle-view="toggleView"
      @reload="reloadWorkspace"
      @create-branch="showCreateBranchModal = true"
      @branch-changed="onCurrentBranchChanged"
      @compare-branch-changed="onCompareBranchChanged"
      @update:chat="onChatMetaUpdated"
      @update:search="chatSearch = $event"
      @update:show-hidden="showHidden = $event"
      @navigate-to-board="navigateToBoard"
      @navigate-to-parent="navigateToParent"
      @new-subtask="showSubtaskModal = true"
      @create-subtasks="onCreateSubtasks"
      @new-tag="showTagModal = true"
      @select-child-chat="selectChildChat"
      @set-project="setChatProject"
      @add-profile="onAddProfile"
    />

    <VerticalSplitter v-if="showChat && (showChanges || showPreview)" :panels="splitterConfig">
      <template #left>
        <!-- LEFT: Chat panel -->
        <div class="flex flex-col h-full w-full">
          <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
            <ChatIcon mode="vibe" class="text-sm" />
            <span class="text-sm font-bold truncate grow">{{ workingChat?.name || 'Vibe session' }}</span>
            <button class="btn btn-xs btn-ghost" @click="showKanbanSelector = !showKanbanSelector" title="New session">
              <i class="fa-brands fa-trello"></i> Tasks
            </button>
            <button class="btn btn-xs btn-ghost" @click="showChatPicker = !showChatPicker" title="Switch session">
              Recent <i class="fa-solid fa-chevron-down"></i>
            </button>
          </div>

          <div v-if="showKanbanSelector" class="flex flex-col h-full overflow-hidden bg-base-100">
            <div class="flex items-center gap-2 px-2 py-2 border-b border-base-content/10 shrink-0">
              <span class="text-xs font-semibold">Select task or create new</span>
              <button class="btn btn-xs btn-ghost ml-auto" @click="showKanbanSelector = false">
                <i class="fa-solid fa-times"></i>
              </button>
            </div>
            <div class="grow overflow-hidden">
              <KanbanContainer :params="kanbanParams" />
            </div>
          </div>

          <div v-else-if="showChatPicker" class="bg-base-100 border-b border-base-content/10 max-h-40 overflow-y-auto z-10">
            <div v-for="c in vibeSessions" :key="c.id"
              class="flex items-center gap-2 px-2 py-1.5 text-xs cursor-pointer hover:bg-base-200"
              :class="activeChat?.id === c.id ? 'bg-primary/10 text-primary' : ''"
              @click="selectSession(c)">
              <ChatIcon :mode="c.mode" class="opacity-60" />
              <span class="truncate grow">{{ c.name }}</span>
              <span class="text-base-content/30 shrink-0">{{ formatDate(c.updated_at) }}</span>
            </div>
            <div v-if="!vibeSessions.length" class="px-2 py-2 text-xs text-base-content/40 text-center">
              No vibe sessions yet
            </div>
          </div>

          <div class="flex items-center gap-1 px-2 text-xs text-base-content/50 py-0.5" v-if="showChildChat">
            <button class="hover:underline hover:text-base-content" @click="selectChildChat(null)">
              {{ activeChat?.name }}
            </button>
            <i class="fa-solid fa-chevron-right text-xs"></i>
            <span class="text-warning font-semibold truncate">{{ showChildChat.name }}</span>
          </div>

          <div class="grow min-h-0 overflow-hidden" v-else-if="workingChat">
            <Chat
              :chat="workingChat"
              :showHidden="showHidden"
              :filter="chatSearch"
              class="h-full px-2 pb-2"
              @refresh-chat="reloadActiveChat"
            />
          </div>
        </div>
      </template>

      <template #right>
        <!-- MIDDLE: Changes/PR View & RIGHT: Preview -->
        <VerticalSplitter v-if="showChanges && showPreview" :panels="splitterConfigRight">
          <template #left>
            <div class="flex flex-col h-full w-full">
              <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
                <i class="fa-solid fa-code-compare text-warning text-sm"></i>
                <span class="text-sm font-bold truncate grow">Changes</span>
                <button class="btn btn-xs btn-ghost" @click="refreshChanges" title="Refresh changes">
                  <i class="fa-solid fa-rotate-right"></i>
                </button>
              </div>

              <div class="grow min-h-0 overflow-hidden p-2" v-if="workingChat">
                <PRView
                  ref="prView"
                  :chat="workingChat"
                  :fromBranch="currentBranchFromMeta"
                  :toBranch="compareBranchFromMeta"
                  class="h-full"
                  @select-branch="onPRBranchSelected"
                  @comment="onPRComment"
                  @change-column="onChangeColumnFromPR"
                  @new-chat="onNewChatFromChanges"
                  @chat-message="onPRChatMessage"
                />
              </div>
              <div v-else class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
                <i class="fa-solid fa-inbox text-4xl"></i>
                <span class="text-sm">No active session</span>
              </div>
            </div>
          </template>

          <template #right>
            <div class="flex flex-col h-full w-full">
              <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 border-b border-base-content/10 shrink-0">
                <i class="fa-solid fa-display text-success text-sm"></i>
                <span class="text-sm font-bold grow">Preview</span>
                <select class="select select-xs select-bordered max-w-[180px]"
                  v-model="selectedAppKey"
                  @change="onAppSelected">
                  <option value="">-- Select workspace app --</option>
                  <option v-for="app in projectApps" :key="app.key" :value="app.key">
                    {{ app.workspaceName }} / {{ app.name }}
                  </option>
                </select>
                <button class="btn btn-xs btn-ghost" @click="reloadPreview" title="Reload preview">
                  <i class="fa-solid fa-rotate-right"></i>
                </button>
                <button class="btn btn-xs btn-ghost" @click="openPreviewFullscreen" title="Fullscreen" v-if="selectedApp">
                  <i class="fa-solid fa-expand"></i>
                </button>
              </div>

              <div class="grow min-h-0 relative overflow-hidden bg-base-100" v-if="selectedApp?.app" :key="selectedAppKey">
                <AppWindow
                  :app="selectedApp.app"
                  class="w-full h-full"
                />
              </div>
              <div v-else class="grow flex flex-col items-center justify-center gap-3 text-base-content/30">
                <i class="fa-solid fa-display text-5xl"></i>
                <span class="text-sm">Select a workspace app to preview</span>
              </div>
            </div>
          </template>
        </VerticalSplitter>

        <!-- Only Changes visible -->
        <div v-else-if="showChanges" class="flex flex-col h-full w-full">
          <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
            <i class="fa-solid fa-code-compare text-warning text-sm"></i>
            <span class="text-sm font-bold truncate grow">Changes</span>
            <button class="btn btn-xs btn-ghost" @click="refreshChanges" title="Refresh changes">
              <i class="fa-solid fa-rotate-right"></i>
            </button>
          </div>

          <div class="grow min-h-0 overflow-hidden p-2" v-if="workingChat">
            <PRView
              ref="prView"
              :chat="workingChat"
              :fromBranch="currentBranchFromMeta"
              :toBranch="compareBranchFromMeta"
              class="h-full"
              @select-branch="onPRBranchSelected"
              @comment="onPRComment"
              @change-column="onChangeColumnFromPR"
              @new-chat="onNewChatFromChanges"
              @chat-message="onPRChatMessage"
            />
          </div>
          <div v-else class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
            <i class="fa-solid fa-inbox text-4xl"></i>
            <span class="text-sm">No active session</span>
          </div>
        </div>

        <!-- Only Preview visible -->
        <div v-else-if="showPreview" class="flex flex-col h-full w-full">
          <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 border-b border-base-content/10 shrink-0">
            <i class="fa-solid fa-display text-success text-sm"></i>
            <span class="text-sm font-bold grow">Preview</span>
            <select class="select select-xs select-bordered max-w-[180px]"
              v-model="selectedAppKey"
              @change="onAppSelected">
              <option value="">-- Select workspace app --</option>
              <option v-for="app in projectApps" :key="app.key" :value="app.key">
                {{ app.workspaceName }} / {{ app.name }}
              </option>
            </select>
            <button class="btn btn-xs btn-ghost" @click="reloadPreview" title="Reload preview">
              <i class="fa-solid fa-rotate-right"></i>
            </button>
            <button class="btn btn-xs btn-ghost" @click="openPreviewFullscreen" title="Fullscreen" v-if="selectedApp">
              <i class="fa-solid fa-expand"></i>
            </button>
          </div>

          <div class="grow min-h-0 relative overflow-hidden bg-base-100" v-if="selectedApp?.app" :key="selectedAppKey">
            <AppWindow
              :app="selectedApp.app"
              class="w-full h-full"
            />
          </div>
          <div v-else class="grow flex flex-col items-center justify-center gap-3 text-base-content/30">
            <i class="fa-solid fa-display text-5xl"></i>
            <span class="text-sm">Select a workspace app to preview</span>
          </div>
        </div>
      </template>
    </VerticalSplitter>

    <!-- Fallback: Chat only -->
    <div v-else-if="showChat" class="flex flex-col h-full w-full overflow-hidden">
      <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
        <ChatIcon mode="vibe" class="text-sm" />
        <span class="text-sm font-bold truncate grow">{{ workingChat?.name || 'Vibe session' }}</span>
        <button class="btn btn-xs btn-ghost" @click="showKanbanSelector = !showKanbanSelector" title="New session">
          <i class="fa-brands fa-trello"></i> Tasks
        </button>
        <button class="btn btn-xs btn-ghost" @click="showChatPicker = !showChatPicker" title="Switch session">
          Recent <i class="fa-solid fa-chevron-down"></i>
        </button>
      </div>

      <div v-if="showKanbanSelector" class="flex flex-col h-full overflow-hidden bg-base-100">
        <div class="flex items-center gap-2 px-2 py-2 border-b border-base-content/10 shrink-0">
          <span class="text-xs font-semibold">Select task or create new</span>
          <button class="btn btn-xs btn-ghost ml-auto" @click="showKanbanSelector = false">
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
        <div class="grow overflow-hidden">
          <KanbanContainer :params="kanbanParams" />
        </div>
      </div>

      <div v-else-if="showChatPicker" class="bg-base-100 border-b border-base-content/10 max-h-40 overflow-y-auto z-10">
        <div v-for="c in vibeSessions" :key="c.id"
          class="flex items-center gap-2 px-2 py-1.5 text-xs cursor-pointer hover:bg-base-200"
          :class="activeChat?.id === c.id ? 'bg-primary/10 text-primary' : ''"
          @click="selectSession(c)">
          <ChatIcon :mode="c.mode" class="opacity-60" />
          <span class="truncate grow">{{ c.name }}</span>
          <span class="text-base-content/30 shrink-0">{{ formatDate(c.updated_at) }}</span>
        </div>
        <div v-if="!vibeSessions.length" class="px-2 py-2 text-xs text-base-content/40 text-center">
          No vibe sessions yet
        </div>
      </div>

      <div class="flex items-center gap-1 px-2 text-xs text-base-content/50 py-0.5" v-if="showChildChat">
        <button class="hover:underline hover:text-base-content" @click="selectChildChat(null)">
          {{ activeChat?.name }}
        </button>
        <i class="fa-solid fa-chevron-right text-xs"></i>
        <span class="text-warning font-semibold truncate">{{ showChildChat.name }}</span>
      </div>

      <div class="grow min-h-0 overflow-hidden" v-else-if="workingChat">
        <Chat
          :chat="workingChat"
          :showHidden="showHidden"
          :filter="chatSearch"
          class="h-full px-2 pb-2"
          @refresh-chat="reloadActiveChat"
        />
      </div>
    </div>

    <!-- Create branch modal -->
    <modal v-if="showCreateBranchModal">
      <div class="flex flex-col gap-4 p-4 min-w-96">
        <h3 class="font-bold text-lg">Create New Branch</h3>
        <div class="form-control">
          <label class="label"><span class="label-text">From branch</span></label>
          <select class="select select-bordered select-sm" v-model="createBranchFrom">
            <option v-for="b in branches" :key="b" :value="b">{{ b }}</option>
          </select>
        </div>
        <input
          v-model="newBranchName"
          type="text"
          class="input input-bordered input-sm"
          placeholder="Branch name (e.g., feature/my-feature)"
          @keydown.enter="onCreateBranch"
        />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="showCreateBranchModal = false">Cancel</button>
          <button
            class="btn btn-sm btn-primary"
            @click="onCreateBranch"
            :disabled="!newBranchName.trim()">
            Create
          </button>
        </div>
      </div>
    </modal>

    <!-- New subtask modal -->
    <modal v-if="showSubtaskModal">
      <div class="flex flex-col gap-4 p-4">
        <h3 class="font-bold text-lg">New Subtask</h3>
        <input v-model="subtaskName" type="text" class="input input-bordered input-sm" placeholder="Subtask name" />
        <select class="select select-bordered select-sm" v-model="subtaskMode">
          <option value="task">Task</option>
          <option value="chat">Chat</option>
          <option value="vibe">Vibe</option>
          <option value="topic">Topic</option>
          <option value="prview">PR View</option>
        </select>
        <textarea v-model="subtaskDescription" class="textarea textarea-bordered textarea-sm" rows="3" placeholder="Description (optional)" />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="showSubtaskModal = false">Cancel</button>
          <button class="btn btn-sm btn-primary" @click="createSubTask" :disabled="!subtaskName.trim()">Create</button>
        </div>
      </div>
    </modal>

    <!-- New tag modal -->
    <modal v-if="showTagModal">
      <div class="flex flex-col gap-3 p-4">
        <div class="text-lg font-bold">Add tag</div>
        <select class="select select-sm select-bordered" @change="tagInput = $event.target.value">
          <option value="">New tag...</option>
          <option v-for="t in $storex.projects.allTags" :key="t" :value="t">{{ t }}</option>
        </select>
        <input type="text" class="input input-sm input-bordered" v-model="tagInput" placeholder="Tag name" />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm btn-error" @click="showTagModal = false">Cancel</button>
          <button class="btn btn-sm" @click="addTag" :disabled="!tagInput">Add</button>
        </div>
      </div>
    </modal>

    <!-- Create subtasks modal -->
    <modal v-if="showSubtasksModal">
      <div class="flex flex-col gap-4 p-4 min-w-96">
        <h3 class="font-bold text-lg">Split into subtasks</h3>
        <textarea v-model="createTasksInstructions" class="textarea textarea-bordered" rows="4" placeholder="Instructions for AI..." />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="showSubtasksModal = false">Cancel</button>
          <button class="btn btn-sm btn-primary" @click="executeCreateSubtasks">Create</button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
import moment from 'moment'
import { v4 as uuidv4 } from 'uuid'

export default {
  props: ['chat', 'kanban', 'params'],
  data() {
    return {
      showChat: true,
      showPreview: true,
      showChanges: false,
      showChatPicker: false,
      showKanbanSelector: false,
      selectedAppKey: '',
      selectedApp: null,
      previewKey: 0,
      branches: [],
      showCreateBranchModal: false,
      createBranchFrom: 'main',
      newBranchName: '',
      showChildChat: null,
      showHidden: false,
      chatSearch: '',
      showSubtaskModal: false,
      subtaskName: '',
      subtaskDescription: '',
      subtaskMode: 'task',
      showTagModal: false,
      tagInput: '',
      showSubtasksModal: false,
      createTasksInstructions: ''
    }
  },
  mounted() {
    this.init()
  },
  computed: {
    activeChat() {
      return this.$storex.chats.activeChat
    },
    workingChat() {
      return this.$storex.chats.chats[this.showChildChat?.id] || this.activeChat
    },
    projectApps() {
      return this.$storex.projects?.projectApps || []
    },
    vibeSessions() {
      return (this.$storex.chats.allChats || [])
        .filter(c => c.mode === 'vibe')
        .sort((a, b) => (a.updated_at > b.updated_at ? -1 : 1))
    },
    childrenChats() {
      if (!this.activeChat?.id) return []
      return (this.$storex.chats.allChats || [])
        .filter(c => c.parent_id === this.activeChat.id)
        .sort((a, b) => a.name > b.name ? 1 : -1)
    },
    splitterConfig() {
      return {
        left: { defaultSize: this.$storex.ui.panelWidths.chat, minSize: 15 },
        right: { defaultSize: 100 - this.$storex.ui.panelWidths.chat, minSize: 15 }
      }
    },
    splitterConfigRight() {
      const changesDefault = this.$storex.ui.panelWidths.changes
      const previewDefault = this.$storex.ui.panelWidths.preview
      const total = changesDefault + previewDefault
      return {
        left: { defaultSize: (changesDefault / total) * 100, minSize: 15 },
        right: { defaultSize: (previewDefault / total) * 100, minSize: 15 }
      }
    },
    currentBranchFromMeta() {
      return this.activeChat?.meta_data?.current_branch || 'main'
    },
    compareBranchFromMeta() {
      return this.activeChat?.meta_data?.compare_branch || 'local'
    },
    kanbanParams() {
      return this.params || {}
    }
  },
  watch: {
    '$storex.projects.activeProject'() {
      this.init()
    },
    vibeSessions(sessions) {
      if (!this.activeChat && sessions.length) {
        this.selectSession(sessions[0])
      }
    },
    activeChat(newVal) {
      if (newVal) {
        this.showKanbanSelector = false
        this.showChildChat = null
        this.childrenChats.forEach(c => this.$storex.chats.loadChat(c))
      }
    },
    projectApps(apps) {
      if (apps?.length && !this.selectedApp) {
        this.autoSelectApp()
      }
    }
  },
  methods: {
    async init() {
      await this.loadProjectBranches()
      this.createBranchFrom = this.branches[0] || 'main'
      if (!this.activeChat) {
        this.showKanbanSelector = true
      }
      this.autoSelectApp()
    },

    loadProjectBranches() {
      const projectApi = this.$storex.projects.activeProject?.$api || this.$api
      if (!projectApi?.repo?.branches) {
        this.branches = ['main']
        return Promise.resolve()
      }
      return projectApi.repo.branches()
        .then(result => {
          this.branches = Array.isArray(result) && result.length ? result : ['main']
        })
        .catch(e => {
          console.warn('[VibeCodingView] loadProjectBranches error:', e)
          this.branches = ['main']
        })
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
      if (!app) {
        this.selectedApp = null
        return
      }
      this.selectedApp = { app }
      this.previewKey++
    },

    toggleView(view) {
      if (view === 'chat') this.showChat = !this.showChat
      else if (view === 'changes') this.showChanges = !this.showChanges
      else if (view === 'preview') this.showPreview = !this.showPreview
    },

    onCurrentBranchChanged() {},
    onCompareBranchChanged() {},

    onChatMetaUpdated(updatedChat) {
      if (!updatedChat?.id) return
      Object.assign(this.activeChat, updatedChat)
      this.$storex.chats.saveChat(this.activeChat)
    },

    onPRBranchSelected({ fromBranch, toBranch }) {
      if (!this.activeChat) return
      Object.assign(this.activeChat, {
        meta_data: {
          ...(this.activeChat.meta_data || {}),
          current_branch: toBranch,
          compare_branch: fromBranch
        }
      })
      this.$refs.vibeHeader?.onBranchCreated?.(toBranch)
    },

    onCreateBranch() {
      if (!this.newBranchName.trim()) return
      const projectApi = this.$storex.projects.activeProject?.$api || this.$api
      projectApi.git.createBranch({ name: this.newBranchName, from: this.createBranchFrom })
        .then(() => this.loadProjectBranches())
        .then(() => {
          this.$refs.vibeHeader?.onBranchCreated?.(this.newBranchName)
          this.$storex.ui.addNotification({ text: `Branch created: ${this.newBranchName}` })
          this.newBranchName = ''
          this.showCreateBranchModal = false
        })
        .catch(error => {
          this.$storex.ui.addNotification({ text: `Error creating branch: ${error.message}`, type: 'error' })
        })
    },

    newVibeChat() {
      this.showChatPicker = false
      const currentBranch = this.branches[0] || 'main'
      this.$storex.chats.createNewChat({
        name: `Vibe ${moment().format('MMM D HH:mm')}`,
        mode: 'vibe',
        board: 'codx-junior',
        project_id: this.$storex.projects.activeProject?.project_id,
        messages: [],
        meta_data: { current_branch: currentBranch, compare_branch: 'local' }
      }).then(chat => this.$storex.chats.setActiveChat(chat))
    },

    selectSession(chat) {
      if (!chat) return
      this.$storex.chats.setActiveChat(chat)
      this.showChatPicker = false
      this.loadProjectBranches()
    },

    reloadActiveChat() {
      if (this.workingChat) this.$storex.chats.reloadChat(this.workingChat)
    },

    refreshChanges() {
      this.$refs.prView?.refreshSummary?.()
    },

    reloadPreview() {
      this.previewKey++
    },

    openPreviewFullscreen() {
      if (this.selectedApp) this.$projects?.openWorkspaceApp(this.selectedApp)
    },

    reloadWorkspace() {
      this.reloadPreview()
      this.reloadActiveChat()
    },

    navigateToBoard() {
      this.$emit('chats', this.kanban?.title || this.activeChat?.board)
    },

    navigateToParent(parentChat) {
      if (parentChat) this.$storex.chats.setActiveChat(parentChat)
      else this.navigateToBoard()
    },

    selectChildChat(childChat) {
      this.showChildChat = childChat
      if (childChat && !childChat.messages?.length) this.$storex.chats.reloadChat(childChat)
    },

    createSubTask() {
      if (!this.subtaskName.trim() || !this.activeChat) return
      this.$storex.chats.createNewChat({
        id: uuidv4(),
        board: this.activeChat.board,
        name: this.subtaskName,
        mode: this.subtaskMode,
        parent_id: this.activeChat.id,
        project_id: this.activeChat.project_id,
        owner_project_id: this.activeChat.owner_project_id,
        messages: this.subtaskDescription
          ? [{ role: 'user', content: this.subtaskDescription }]
          : [],
        column: this.activeChat.column
      }).then(chat => {
        this.$storex.chats.saveChat(chat)
        this.showSubtaskModal = false
        this.subtaskName = ''
        this.subtaskDescription = ''
      })
    },

    onCreateSubtasks() {
      this.showSubtasksModal = true
      this.createTasksInstructions = ''
    },

    executeCreateSubtasks() {
      if (this.activeChat) {
        this.$storex.projects.createSubtasks({
          chat: this.activeChat,
          instructions: this.createTasksInstructions
        })
      }
      this.showSubtasksModal = false
    },

    addTag() {
      if (!this.tagInput || !this.activeChat) return
      this.activeChat.tags = [...new Set([...(this.activeChat.tags || []), this.tagInput])]
      this.$storex.chats.saveChat(this.activeChat)
      this.tagInput = ''
      this.showTagModal = false
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
      if (file.chat?.messages) file.chat.messages.push({})
    },

    formatDate(date) {
      return moment(date).fromNow()
    }
  }
}
</script>