<script setup>
import ChatSidebarNode from './ChatSidebarNode.vue'
import ChatListRenderer from './ChatListRenderer.vue'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import ProfileCard from '../ProfileCard.vue'
import ChatAttachmentPreview from './ChatAttachmentPreview.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div :class="[
    'border-r border-base-100 flex flex-col h-full overflow-hidden relative transition-all duration-200',
    'md:border-r md:border-base-100',
    isCompact ? 'w-16 md:w-16' : 'w-64 md:w-64',
    $ui?.isMobile && !isCompact ? 'shadow-lg z-40' : ''
  ]"
  >

    <!-- HEADER: Fixed - Project Selector & Root Chat Node -->
    <div class="shrink-0 border-b border-base-100">
      <!-- Project Selector -->
      <div v-if="!isCompact" class="px-2 md:px-3 py-3 border-b border-base-100">
        <ProjectDetailt
          @click.stop=""
          :iconify="false"
          :modelValue="targetProject"
          :options="{ showFolders: false, showIcon: true, showSelector: true }"
          @update:modelValue="$emit('select-project', $event)"
        />
      </div>

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
              selectedChatId === rootChat?.id
                ? 'bg-codx-secondary  border-codx-primary/60 shadow-md ring-2 ring-codx-primary/20'
                : ' border-base-content/20 hover:bg-white/20 hover:border-base-content/30'
            ]"
          >
            {{ getInitials(rootChat?.name) }}
          </div>
          <!-- Tooltip -->
          <div class="absolute left-14 top-1/2 -translate-y-1/2 bg-white/20  text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 border border-base-content/20">
            {{ rootChat?.name }}
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

      <!-- Chat Children (Subtasks) Section -->
      <div v-if="sortedRootChildren.length > 0" class="ml-1 px-2 md:px-3 py-2 flex flex-col flex-1 min-h-0">
        <div v-if="!isCompact" class="text-xs font-semibold text-base-content/50 uppercase tracking-wider mb-2 px-1 shrink-0">
          <i class="fa-solid fa-list-check text-xs mr-2 opacity-60"></i>Subtasks
        </div>
        <ChatListRenderer
          :class="!isCompact && 'p-1'"
          :chatList="sortedRootChildren"
          :selectedChatId="selectedChatId"
          :isCompact="isCompact"
          :allChats="allChats"
          :useExtended="false"
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
        <!-- Logs Button -->
        <button 
          @click.stop="$emit('action', { type: 'logs' })"
          :title="'View AI logs'"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus:ring-2 focus:ring-primary/50 transition-colors duration-150"
        >
          <i class="fa-solid fa-file-lines text-sm"></i>
        </button>

        <!-- Timeline Button -->
        <button 
          @click.stop="$emit('action', { type: 'timeline' })"
          :title="'View timeline'"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus:ring-2 focus:ring-primary/50 transition-colors duration-150"
        >
          <i class="fa-solid fa-timeline text-sm"></i>
        </button>

        <!-- Export Button -->
        <button 
          @click.stop="$emit('action', { type: 'export' })"
          :title="'Export chat'"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus:ring-2 focus:ring-primary/50 transition-colors duration-150"
        >
          <i class="fa-solid fa-download text-sm"></i>
        </button>

        <!-- Settings Button -->
        <button 
          @click.stop="$emit('action', { type: 'settings' })"
          :title="'Open settings'"
          class="flex-1 flex items-center justify-center h-9 rounded-lg text-base-content/60 hover:text-base-content/90 hover:bg-base-200 focus:ring-2 focus:ring-primary/50 transition-colors duration-150"
        >
          <i class="fa-solid fa-gear text-sm"></i>
        </button>

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
  emits: ['select', 'add-subtask', 'action', 'update-search', 'mode-changed', 'toggle-compact', 'delete-chat', 'remove-attachment', 'select-project'],
  computed: {
    rootChildren() {
      return this.allChats.filter(c => c.parent_id === this.rootChat.id)
    },
    sortedRootChildren() {
      return [...this.rootChildren].sort((a, b) => {
        const timeA = new Date(a.updated_at || a.created_at || 0).getTime()
        const timeB = new Date(b.updated_at || b.created_at || 0).getTime()
        return timeB - timeA
      })
    },
    selectedChat() {
      return this.allChats.find(c => c.id === this.selectedChatId) || this.rootChat
    },
    targetProject() {
      return this.$chats.getChatWorkingProject(this.selectedChat)
    }
  },
  methods: {
    selectChat(chat) {
      this.$emit('select', chat)
    },
    getInitials(name) {
      if (!name) return 'CH'
      const cleanName = name.replace(/[^\w\s-]/g, '').trim()
      const words = cleanName.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    }
  }
}
</script>