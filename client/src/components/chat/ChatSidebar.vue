<script setup>
import ChatSidebarNode from './ChatSidebarNode.vue'
import ChatListRenderer from './ChatListRenderer.vue'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import ProfileCard from '../ProfileCard.vue'
import ChatAttachmentPreview from './ChatAttachmentPreview.vue'
</script>

<template>
  <div :class="[
    'border-r border-base-100 flex flex-col h-full overflow-hidden relative transition-all duration-200',
    'md:border-r md:border-base-100',
    isCompact ? 'w-16 md:w-16' : 'w-64 md:w-64',
    $ui?.isMobile && !isCompact ? 'shadow-lg z-40' : ''
  ]"
  >

    <!-- HEADER: Fixed - Root Chat Node -->
    <div class="shrink-0 border-b border-base-100">
      <!-- Root Chat Node - Expanded Mode -->
      <div v-if="!isCompact" class="px-2 md:px-3 py-2">
        <ChatSidebarNode
          :chat="rootChat"
          :allChats="allChats"
          :selectedChatId="selectedChatId"
          :isCompact="false"
          @select="selectChat"
          @add-subtask="$emit('add-subtask', $event)"
          @delete-chat="$emit('delete-chat', $event)"
          @click.stop=""
        />
      </div>
      <!-- Root Chat Node - Compact Mode -->
      <div v-else class="flex flex-col items-center gap-2 p-2">
        <div
          @click="selectChat(rootChat)"
          class="relative cursor-pointer group"
          :title="rootChat?.name"
        >
          <div
            class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold border transition-all duration-200"
            :class="[
              selectedChatId === rootChat.id
                ? 'border-primary/60 shadow-md ring-2 ring-primary/20'
                : 'border-base-content/20 hover:bg-white/20 hover:border-base-content/30'
            ]"
            :style="`background-image: url(${allChatsWorkingProject[rootChat]?.project_icon})`"
          >
            {{ getInitials(rootChat.name) }}
          </div>
          <!-- Tooltip -->
          <div class="absolute left-14 top-1/2 -translate-y-1/2 bg-white/20 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 border border-base-content/20">
            {{ rootChat.name }}
          </div>
        </div>
      </div>
    </div>

    <!-- CENTER: Scrollable Content Area -->
    <div class="flex-1 overflow-y-auto min-h-0 flex flex-col">
      <!-- Attachments Section -->
      <div v-if="workingChat.attachments?.length" class="border-b border-base-100 shrink-0">
        <ChatAttachmentPreview
          :attachments="workingChat.attachments"
          @remove-attachment="$emit('remove-attachment', $event)"
        />
      </div>

      <!-- Profiles Section -->
      <div v-if="chatProfiles.length" class="border-b border-base-100 shrink-0">
        <div v-if="!isCompact" class="px-3 py-3">
          <div class="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-3 px-1">
            <i class="fa-solid fa-circle-user text-xs mr-2 opacity-60"></i>Profiles
          </div>
          <div class="space-y-2">
            <ProfileCard 
              v-for="profile in chatProfiles"
              :key="profile.name"
              :profile="profile"
              :mini="true"
            />
          </div>
        </div>
        <div v-else class="p-2 flex flex-col items-center gap-2">
          <div class="text-xs font-semibold text-base-content/50 text-center">P</div>
          <div class="space-y-1.5 flex flex-col items-center">
            <ProfileAvatar 
              v-for="profile in chatProfiles"
              :key="profile.name"
              :profile="profile"
              :width="10"
            />
          </div>
        </div>
      </div>

      <!-- Chat Children (Subtasks) Section - Now shows ALL nested chats -->
      <div v-if="allNestedChats.length > 0" class="ml-1 px-2 md:px-3 py-2 flex flex-col flex-1 min-h-0">
        <!-- Header with status filter -->
        <div v-if="!isCompact" class="flex items-center justify-between gap-2 mb-2 px-1 shrink-0">
          <div class="text-xs font-semibold text-base-content/50 uppercase tracking-wider">
            <i class="fa-solid fa-list-check text-xs mr-2 opacity-60"></i>Subtasks
          </div>

          <!-- Status filter dropdown -->
          <div class="dropdown dropdown-end" @click.stop>
            <button
              tabindex="0"
              type="button"
              class="btn btn-xs btn-ghost gap-1 normal-case h-6 min-h-0 px-1.5"
              :class="statusFilter && $chats.statusTextColor(statusFilter)"
              :title="statusFilter ? `Filtered by: ${$chats.statusLabel(statusFilter)}` : 'Filter subtasks by status'"
            >
              <i :class="statusFilter ? $chats.statusIcon(statusFilter) : 'fa-solid fa-filter'"></i>
              <span class="text-[10px] font-medium">{{ statusFilter ? $chats.statusLabel(statusFilter) : 'All' }}</span>
              <i class="fa-solid fa-chevron-down text-[8px] opacity-60"></i>
            </button>
            <ul
              tabindex="0"
              class="dropdown-content menu menu-sm bg-base-100 rounded-box z-50 w-44 p-1 shadow-lg border border-base-300"
            >
              <li>
                <a
                  @click.stop="setStatusFilter(null)"
                  :class="[!statusFilter && 'active', 'flex items-center gap-2']"
                >
                  <i class="fa-solid fa-layer-group opacity-60"></i>
                  <span>All statuses</span>
                  <span class="ml-auto opacity-50 text-[10px]">{{ allNestedChats.length }}</span>
                </a>
              </li>
              <li v-for="option in $chats.statusList" :key="option.value">
                <a
                  @click.stop="setStatusFilter(option.value)"
                  :class="[statusFilter === option.value && 'active', 'flex items-center gap-2']"
                >
                  <i :class="[option.icon, option.textColor]"></i>
                  <span>{{ option.label }}</span>
                  <span class="ml-auto opacity-50 text-[10px]">{{ statusCounts[option.value] || 0 }}</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        <!-- Compact mode: active filter indicator -->
        <div
          v-else-if="statusFilter"
          class="flex justify-center mb-1 shrink-0"
          :title="`Filtered by: ${$chats.statusLabel(statusFilter)}`"
        >
          <i class="text-xs" :class="[$chats.statusIcon(statusFilter), $chats.statusTextColor(statusFilter)]"></i>
        </div>

        <ChatListRenderer
          :class="!isCompact && 'p-1'"
          :chatList="filteredNestedChats"
          :selectedChatId="selectedChatId"
          :isCompact="isCompact"
          :allChats="allChats"
          :useExtended="false"
          :emptyText="statusFilter ? 'No subtasks with this status' : 'No subtasks yet'"
          @select="selectChat"
          @add-subtask="$emit('add-subtask', $event)"
          @delete-chat="$emit('delete-chat', $event)"
        />
      </div>
      <div v-else class="px-3 py-8 text-center">
        <p class="text-xs text-base-content/40">No subtasks yet</p>
      </div>
    </div>

    <!-- FOOTER: Fixed - Icon Toolbar -->
    <div class="shrink-0 border-t border-base-100 px-2 py-2">
      <div class="flex items-center gap-1"
        :class="isCompact && 'flex-col gap-3'" 
      >
        <!-- Browser Session Button -->
        <button 
          @click.stop="openBrowserSessionDialog"
          :title="'Create browser session'"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus:ring-2 focus:ring-primary/50 transition-colors duration-150"
        >
          <i class="fa-solid fa-globe text-sm"></i>
        </button>

        <!-- More Actions Dropdown (opens top-right) -->
        <div class="dropdown dropdown-top dropdown-start flex-1">
          <div
            ref="actionsTrigger"
            tabindex="0"
            role="button"
            :title="'More actions'"
            class="flex items-center justify-center h-9 w-full rounded-lg cursor-pointer text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus:ring-2 focus:ring-primary/50 transition-colors duration-150"
          >
            <i class="fa-solid fa-ellipsis-vertical text-sm"></i>
          </div>
          <ul
            tabindex="0"
            class="dropdown-content menu menu-sm bg-base-100 rounded-box z-50 w-44 p-2 shadow-lg border border-base-300 mb-1"
          >
            <li>
              <a @click.stop="handleFooterAction({ type: 'timeline' })">
                <i class="fa-solid fa-timeline text-sm opacity-70"></i>
                View timeline
              </a>
            </li>
            <li>
              <a @click.stop="handleFooterAction({ type: 'logs' })">
                <i class="fa-solid fa-file-lines text-sm opacity-70"></i>
                View AI logs
              </a>
            </li>
            <li></li>
            <li>
              <a
                @click.stop="handleReload"
                :class="isReloading && 'is-disabled pointer-events-none opacity-50'"
              >
                <i class="fa-solid fa-arrows-rotate text-sm opacity-70" :class="isReloading && 'fa-spin'"></i>
                Reload chat
              </a>
            </li>
            <li>
              <a @click.stop="handleFooterAction({ type: 'export' })">
                <i class="fa-solid fa-download text-sm opacity-70"></i>
                Export chat
              </a>
            </li>
            <li></li>
            <li>
              <a @click.stop="handleFooterAction({ type: 'settings' })">
                <i class="fa-solid fa-gear text-sm opacity-70"></i>
                Settings
              </a>
            </li>
          </ul>
        </div>

        <!-- Compact Toggle Button -->
        <button 
          @click.stop="$emit('toggle-compact')"
          :title="isCompact ? 'Expand sidebar' : 'Collapse sidebar'"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus:ring-2 focus:ring-primary/50 transition-colors duration-150"
        >
          <i :class="isCompact ? 'fa-solid fa-angle-right' : 'fa-solid fa-angle-left'"></i>
        </button>
      </div>
    </div>

    <!-- Browser Session Dialog Modal -->
    <dialog v-if="showBrowserDialog" class="modal modal-open">
      <form method="dialog" class="modal-box w-full max-w-sm">
        <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">
          <i class="fa-solid fa-xmark"></i>
        </button>
        
        <h3 class="font-bold text-lg mb-4">Create Browser Session</h3>
        
        <div class="form-control gap-4">
          <!-- Session Name -->
          <div class="form-control w-full">
            <label class="label">
              <span class="label-text text-sm font-medium">Session Name</span>
            </label>
            <input
              v-model="browserSessionForm.name"
              type="text"
              placeholder="e.g., Testing Session"
              class="input input-bordered input-sm w-full focus:ring-2 focus:ring-primary/50"
            />
          </div>

          <!-- Chat ID (Read-only) -->
          <div class="form-control w-full">
            <label class="label">
              <span class="label-text text-sm font-medium">Chat ID</span>
            </label>
            <input
              :value="workingChat.id"
              type="text"
              disabled
              class="input input-bordered input-sm w-full bg-base-300 text-base-content/50"
            />
          </div>

          <!-- Description -->
          <div class="form-control w-full">
            <label class="label">
              <span class="label-text text-sm font-medium">Description (Optional)</span>
            </label>
            <textarea
              v-model="browserSessionForm.description"
              placeholder="Add notes about this session..."
              class="textarea textarea-bordered textarea-sm w-full focus:ring-2 focus:ring-primary/50 resize-none"
              rows="3"
            ></textarea>
          </div>
        </div>

        <!-- Actions -->
        <div class="modal-action gap-2 mt-6">
          <button
            type="button"
            @click="closeBrowserSessionDialog"
            class="btn btn-ghost btn-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            @click="createBrowserSession"
            :disabled="!browserSessionForm.name.trim() || isCreatingSession"
            class="btn btn-primary btn-sm"
          >
            <span v-if="isCreatingSession" class="loading loading-spinner loading-sm"></span>
            <span v-else>Create Session</span>
          </button>
        </div>
      </form>
      <form method="dialog" class="modal-backdrop">
        <button @click="closeBrowserSessionDialog">close</button>
      </form>
    </dialog>
  </div>
</template>

<script>
export default {
  props: {
    workingChat: { type: Object, required: true },
    rootChat: { type: Object, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null },
    workingChatMode: { type: String, default: 'chat' },
    chatSearch: { type: String, default: null },
    isCompact: { type: Boolean, default: false },
    chatProfiles: { type: Array, default: () => [] }
  },
  emits: ['select', 'add-subtask', 'action', 'update-search', 'mode-changed', 'toggle-compact', 'delete-chat', 'remove-attachment'],
  data() {
    return {
      showBrowserDialog: false,
      isCreatingSession: false,
      isReloading: false,
      statusFilter: null,
      browserSessionForm: {
        name: '',
        description: ''
      }
    }
  },
  computed: {
    allNestedChats() {
      return this.$storex.chats.chatDescendants(this.rootChat.id).filter(chat => chat.id !== this.rootChat.id)
    },
    sortedAllNestedChats() {
      return [...this.allNestedChats].sort((a, b) => {
        const timeA = new Date(a.updated_at || a.created_at || 0).getTime()
        const timeB = new Date(b.updated_at || b.created_at || 0).getTime()
        return timeB - timeA
      })
    },
    filteredNestedChats() {
      if (!this.statusFilter) return this.sortedAllNestedChats
      // Chats without an explicit status default to 'todo' (store DEFAULT_STATUS)
      return this.sortedAllNestedChats.filter(chat => (chat.status || 'todo') === this.statusFilter)
    },
    statusCounts() {
      return this.allNestedChats.reduce((counts, chat) => {
        const status = chat.status || 'todo'
        counts[status] = (counts[status] || 0) + 1
        return counts
      }, {})
    },
    selectedChat() {
      return this.allChats.find(c => c.id === this.selectedChatId) || this.rootChat
    },
    allChatsWorkingProject() {
      return [this.rootChat, ...this.allNestedChats]
        .reduce((v, acc) => ({ ...acc, [v.id]: this.$chats.getChatWorkingProject(v) }), {})
    }
  },
  methods: {
    selectChat(chat) {
      this.$emit('select', chat)
    },
    setStatusFilter(status) {
      // Toggle: clicking the active status clears the filter
      this.statusFilter = this.statusFilter === status ? null : status
      document.activeElement?.blur()
    },
    getInitials(name) {
      if (!name) return 'CH'
      const cleanName = name.replace(/[^\w\s-]/g, '').trim()
      const words = cleanName.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    },
    handleFooterAction(action) {
      this.$emit('action', action)
      // Close the dropdown after selecting an item
      this.$refs.actionsTrigger?.blur()
    },
    handleReload() {
      // Close the dropdown, then trigger reload
      this.$refs.actionsTrigger?.blur()
      this.reloadActiveChat()
    },
    async reloadActiveChat() {
      const chat = this.workingChat
      if (!chat?.id || this.isReloading) return

      this.isReloading = true
      try {
        await this.$storex.chats.reloadChat({
          id: chat.id,
          project_id: chat.project_id,
          owner_project_id: chat.owner_project_id
        })
      } catch (error) {
        console.error('[ChatSidebar] Error reloading chat:', error)
      } finally {
        this.isReloading = false
      }
    },
    openBrowserSessionDialog() {
      this.browserSessionForm = {
        name: `${this.workingChat.name} - Browser Session`,
        description: ''
      }
      this.showBrowserDialog = true
    },
    closeBrowserSessionDialog() {
      this.showBrowserDialog = false
      this.browserSessionForm = {
        name: '',
        description: ''
      }
    },
    async createBrowserSession() {
      if (!this.browserSessionForm.name.trim()) return

      this.isCreatingSession = true
      try {
        const sessionData = {
          name: this.browserSessionForm.name,
          description: this.browserSessionForm.description,
          chat_id: this.workingChat.id
        }

        await this.$storex.browsers.createSession(sessionData)
        this.closeBrowserSessionDialog()
      } catch (error) {
        console.error('[ChatSidebar] Error creating browser session:', error)
      } finally {
        this.isCreatingSession = false
      }
    }
  }
}
</script>