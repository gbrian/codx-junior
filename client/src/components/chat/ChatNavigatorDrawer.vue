<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ChatNavigatorNode from './ChatNavigatorNode.vue'
</script>

<template>
  <div>
    <!-- Trigger Button -->
    <button 
      class="p-2 text-xs click gap-2 tooltip"
      @click="openDrawer"
      :data-tip="`${totalDescendants} subtasks`"
      title="Open task navigator"
    >
      <i class="fa-solid fa-bars"></i>
    </button>

    <!-- Drawer Backdrop & Panel -->
    <div 
      v-if="isOpen"
      class="fixed inset-0 z-50 flex"
      @click.self="closeDrawer"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/30" @click="closeDrawer"></div>

      <!-- Drawer Panel -->
      <div class="relative w-96 bg-base-100 shadow-xl flex flex-col h-full overflow-hidden">
        <!-- Header -->
        <div class="shrink-0 p-4 border-b border-base-content/10">
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-lg font-bold flex items-center gap-2">
              <ChatIcon :model="rootChat.mode" />
              {{ rootChat.name }}Actions
            </h2>
            <button class="btn btn-sm btn-ghost" @click="closeDrawer">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="flex-1 flex items-center justify-center">
          <div class="flex flex-col items-center gap-2">
            <div class="loading loading-spinner loading-lg text-primary"></div>
            <span class="text-sm text-base-content/60">Loading tasks...</span>
          </div>
        </div>

        <!-- Content Tabs -->
        <div v-else class="flex-1 overflow-y-auto flex flex-col scrollbar-thin">
          <!-- Tab Navigation -->
          <div class="shrink-0 tabs tabs-bordered px-2 pt-2">
            <a 
              class="tab tab-sm flex gap-1"
              :class="activeTab === 'navigator' ? 'tab-active' : ''"
              @click="activeTab = 'navigator'"
            >
              <i class="fa-solid fa-sitemap text-xs"></i>
              Tasks
            </a>
            <a 
              class="tab tab-sm  flex gap-1"
              :class="activeTab === 'actions' ? 'tab-active' : ''"
              @click="activeTab = 'actions'"
            >
              <i class="fa-solid fa-sliders text-xs"></i>
              Actions
            </a>
          </div>

          <!-- Navigator Tab -->
          <div v-if="activeTab === 'navigator'" class="flex-1 overflow-y-auto p-4 space-y-2">
            <!-- Add New Task Button -->
            <button
              class="w-full p-3 rounded-lg border-2 border-dashed border-primary/50 bg-primary/5 hover:bg-primary/10 hover:border-primary transition-all flex items-center gap-2 text-primary font-semibold text-sm"
              @click="onAddNewTask"
            >
              <i class="fa-solid fa-plus text-lg"></i>
              Add New Task
            </button>

            <!-- Root Chat Card -->
            <div
              v-if="rootChat"
              class="p-3 rounded-lg border-2 cursor-pointer transition-all group flex items-center justify-between"
              :class="selectedChatId === rootChat.id
                ? 'border-warning bg-warning/10'
                : 'border-base-content/10 bg-base-200 hover:border-base-content/30'"
              @click="selectChat(rootChat)"
            >
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <ChatIcon :mode="rootChat.mode" class="text-sm" />
                  <span class="font-bold text-sm truncate flex-1">{{ rootChat.name }}</span>
                  <span class="text-xs text-base-content/40">{{ rootChat.messages?.length || 0 }}</span>
                </div>
                <div v-if="rootChat.description" class="text-xs text-base-content/60 line-clamp-2">
                  {{ rootChat.description }}
                </div>
                <div v-if="totalDescendants" class="text-xs text-primary mt-1">
                  {{ totalDescendants }} subtasks
                </div>
              </div>

              <!-- Add Subtask Button -->
              <button
                class="btn btn-xs btn-ghost opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2"
                @click.stop="onAddSubtask(rootChat)"
                title="Create subtask"
              >
                <i class="fa-solid fa-plus text-primary"></i>
              </button>
            </div>

            <!-- Children Nodes -->
            <ChatNavigatorNode
              v-for="child in rootChildren"
              :key="child.id"
              :chat="child"
              :allChats="allLoadedChats"
              :selectedChatId="selectedChatId"
              :depth="0"
              @select="selectChat"
              @add-subtask="onAddSubtask"
            />

            <!-- Empty State -->
            <div v-if="!rootChildren.length && !isLoading" class="text-center text-sm text-base-content/40 py-8">
              <i class="fa-regular fa-inbox text-2xl block mb-2 opacity-50"></i>
              No subtasks yet
            </div>
          </div>

          <!-- Actions Tab -->
          <div v-if="activeTab === 'actions'" class="flex-1 overflow-y-auto p-4">
            <div class="space-y-4">
              <!-- Navigation Section -->
              <div>
                <div class="text-xs font-bold text-base-content/60 uppercase mb-2">Navigation</div>
                <ul class="space-y-1">
                  <li @click="onActionTimeline">
                    <a class=" flex gap-2 cursor-pointer items-center hover:bg-base-200 rounded-md p-2"><i class="fa-regular fa-hourglass text-sm"></i> Timeline</a>
                  </li>
                </ul>
              </div>

              <!-- Task Management Section -->
              <div>
                <div class="text-xs font-bold text-base-content/60 uppercase mb-2">Task Management</div>
                <ul class="p-2 space-y-1">
                  <li @click="onActionCreateSubtasks">
                    <a class=" flex gap-2 cursor-pointer items-center hover:bg-base-200 rounded-md p-2"><i class="fa-solid fa-wand-magic-sparkles text-sm"></i> Auto Split Tasks</a>
                  </li>
                  <li @click="onActionLinkChats">
                    <a class=" flex gap-2 cursor-pointer items-center hover:bg-base-200 rounded-md p-2"><i class="fa-solid fa-link text-sm"></i> Link Chats</a>
                  </li>
                </ul>
              </div>

              <!-- Chat Mode Section -->
              <div>
                <div class="text-xs font-bold text-base-content/60 uppercase mb-2">Chat Mode</div>
                <div class="dropdown w-full">
                  <div tabindex="0" role="button" class="btn btn-sm btn-block justify-start">
                    <ChatIcon :mode="workingChatMode" class="text-sm" />
                    <span>{{ modeLabel }}</span>
                  </div>
                  <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-full p-2 shadow">
                    <li @click="onActionSetMode('chat')"><a><ChatIcon mode="chat" /> Conversation</a></li>
                    <li @click="onActionSetMode('task')"><a><ChatIcon mode="task" /> Document</a></li>
                    <li @click="onActionSetMode('topic')"><a><ChatIcon mode="topic" /> Group Chat</a></li>
                    <li @click="onActionSetMode('vibe')"><a><ChatIcon mode="vibe" /> Vibe</a></li>
                    <li @click="onActionSetMode('prview')"><a><ChatIcon mode="prview" /> Changes Review</a></li>
                    <li @click="onActionSetMode('browser')"><a><ChatIcon mode="browser" /> Browser</a></li>
                  </ul>
                </div>
              </div>

              <!-- Tags Section -->
              <div>
                <div class="text-xs font-bold text-base-content/60 uppercase mb-2">Tags</div>
                <button class="btn btn-sm btn-block justify-start" @click="onActionNewTag">
                  <i class="fa-solid fa-plus text-sm"></i>
                  New Tag
                </button>
              </div>

              <!-- Import/Export Section -->
              <div>
                <div class="text-xs font-bold text-base-content/60 uppercase mb-2">Import/Export</div>
                <ul class="p-2 space-y-1">
                  <li @click="onActionExport">
                    <a class=" flex gap-2 cursor-pointer items-center hover:bg-base-200 rounded-md p-2"><i class="fa-solid fa-file-arrow-down text-sm"></i> Export</a>
                  </li>
                </ul>
              </div>

              <!-- Data Management Section -->
              <div>
                <div class="text-xs font-bold text-base-content/60 uppercase mb-2">Data Management</div>
                <ul class="p-2 space-y-1">
                  <li @click="onActionReload">
                    <a class=" flex gap-2 cursor-pointer items-center hover:bg-base-200 rounded-md p-2"><i class="fa-solid fa-recycle text-sm"></i> Reload</a>
                  </li>
                  <li @click="onActionSave">
                    <a class=" flex gap-2 cursor-pointer items-center hover:bg-base-200 rounded-md p-2"><i class="fa-solid fa-floppy-disk text-sm"></i> Save</a>
                  </li>
                </ul>
              </div>

              <!-- Settings Section -->
              <div>
                <div class="text-xs font-bold text-base-content/60 uppercase mb-2">Settings</div>
                <ul class="p-2 space-y-1">
                  <li @click="onActionSettings">
                    <a class=" flex gap-2 cursor-pointer items-center hover:bg-base-200 rounded-md p-2"><i class="fa-solid fa-gear text-sm"></i> Settings</a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  components: { ChatIcon, ChatNavigatorNode },
  props: {
    rootChat: {
      type: Object,
      required: true
    },
    allLoadedChats: {
      type: Array,
      default: () => []
    },
    selectedChatId: {
      type: String,
      default: null
    },
    workingChatMode: {
      type: String,
      default: 'chat'
    }
  },
  data() {
    return {
      isOpen: false,
      isLoading: false,
      activeTab: 'navigator'
    }
  },
  computed: {
    childrenChats() {
      if (!this.rootChat?.id) return []
      return this.$chats.allChats.filter(c => c.parent_id === this.rootChat.id)
    },
    rootChildren() {
      if (!this.rootChat?.id) return []
      return this.allLoadedChats
        .filter(c => c.parent_id === this.rootChat.id)
        .sort((a, b) => (a.child_index ?? 999999) - (b.child_index ?? 999999) || a.name.localeCompare(b.name))
    },
    totalDescendants() {
      if (!this.rootChat?.id) return 0
      const countDescendants = (parentId) => {
        return this.allLoadedChats
          .filter(c => c.parent_id === parentId)
          .reduce((sum, child) => sum + 1 + countDescendants(child.id), 0)
      }
      return countDescendants(this.rootChat.id)
    },
    modeLabel() {
      const modes = {
        chat: 'Conversation',
        task: 'Document',
        topic: 'Group Chat',
        vibe: 'Vibe',
        prview: 'Changes Review',
        browser: 'Browser'
      }
      return modes[this.workingChatMode] || 'Chat'
    }
  },
  methods: {
    openDrawer() {
      this.isOpen = true
    },
    closeDrawer() {
      this.isOpen = false
    },
    selectChat(chat) {
      this.$emit('select', chat)
      this.closeDrawer()
    },
    onAddNewTask() {
      this.$emit('add-subtask', this.rootChat)
      this.closeDrawer()
    },
    onAddSubtask(parentChat) {
      this.$emit('add-subtask', parentChat)
      this.closeDrawer()
    },
    onActionTimeline() {
      this.$emit('action', { type: 'timeline' })
      this.closeDrawer()
    },
    onActionNewSubtask() {
      this.$emit('action', { type: 'new-subtask' })
      this.closeDrawer()
    },
    onActionCreateSubtasks() {
      this.$emit('action', { type: 'create-subtasks' })
      this.closeDrawer()
    },
    onActionLinkChats() {
      this.$emit('action', { type: 'link-chats' })
      this.closeDrawer()
    },
    onActionSetMode(mode) {
      this.$emit('action', { type: 'set-mode', mode })
      this.closeDrawer()
    },
    onActionNewTag() {
      this.$emit('action', { type: 'new-tag' })
      this.closeDrawer()
    },
    onActionExport() {
      this.$emit('action', { type: 'export' })
      this.closeDrawer()
    },
    onActionReload() {
      this.$emit('action', { type: 'reload' })
      this.closeDrawer()
    },
    onActionSave() {
      this.$emit('action', { type: 'save' })
      this.closeDrawer()
    },
    onActionSettings() {
      this.$emit('action', { type: 'settings' })
      this.closeDrawer()
    }
  }
}
</script>
