<script setup>
import ChatSidebarNode from './ChatSidebarNode.vue'
import ProfileAvatar from '../profile/ProfileAvatar.vue'
import ProfileCard from '../ProfileCard.vue'
import ChatAttachmentPreview from './ChatAttachmentPreview.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div :class="[
    'border-r border-base-300 bg-base-100 flex flex-col h-full overflow-hidden relative',
    'md:border-r md:border-base-300',
    isCompact ? 'w-20 md:w-20' : 'w-64 md:w-64',
    $ui?.isMobile && !isCompact ? 'shadow-lg' : ''
  ]"
    @click="isCompact && $emit('toggle-compact')"
  >

    <!-- Root Chat Node with Project Selector -->
    <div class="px-1 shrink-0 space-y-2">
      <!-- Project Selector -->
      <div v-if="!isCompact" class="px-2 md:px-3 z-50 w-full">
        <ProjectDetailt
          :iconify="false"
          :modelValue="targetProject"
          :options="{ showFolders: false, showIcon: true, showSelector: true }"
          @update:modelValue="$emit('select-project', $event)"
        />
      </div>

      <!-- Root Chat Node -->
      <ChatSidebarNode
        :chat="rootChat"
        :allChats="allChats"
        :selectedChatId="selectedChatId"
        :isCompact="isCompact"
        @select="selectChat"
        @add-subtask="$emit('add-subtask', $event)"
        @delete-chat="$emit('delete-chat', $event)"
      />
    </div>

    <div class="grow"></div>
    <ChatAttachmentPreview
      :attachments="workingChat.attachments"
      @remove-attachment="$emit('remove-attachment', $event)"
      v-if="workingChat.attachments?.length"
    />

    <!-- Profiles Section -->
    <div v-if="chatProfiles.length" class="border-t border-base-300 shrink-0">
      <div v-if="!isCompact" class="px-1 py-2">
        <div class="text-xs font-semibold text-base-content/60 uppercase mb-2">Profiles</div>
        <div class="overflow-y-auto space-y-2 max-h-48">
          <ProfileCard 
            v-for="profile in chatProfiles"
            :key="profile.name"
            :profile="profile"
            :mini="true"
          />
        </div>
      </div>
      <div v-else class="p-2 overflow-y-auto space-y-2 max-h-48 flex flex-col items-center">
        <ProfileAvatar 
          v-for="profile in chatProfiles"
          :key="profile.name"
          :profile="profile"
          :width="10"
        />
      </div>
    </div>

    <!-- Footer: Actions -->
    <div class="border-t border-base-300 p-3 space-y-1 shrink-0">
      <button 
        v-if="!isCompact"
        class="btn btn-xs btn-block btn-ghost justify-start gap-2"
        @click="$emit('action', { type: 'logs' })"
        title="View AI logs"
      >
        <i class="fa-solid fa-file-lines"></i> AI Logs
      </button>
      <button 
        v-if="!isCompact"
        class="btn btn-xs btn-block btn-ghost justify-start gap-2"
        @click="$emit('action', { type: 'timeline' })"
      >
        <i class="fa-solid fa-timeline"></i> Timeline
      </button>
      <button 
        v-if="!isCompact"
        class="btn btn-xs btn-block btn-ghost justify-start gap-2"
        @click="$emit('action', { type: 'export' })"
      >
        <i class="fa-solid fa-download"></i> Export
      </button>
      <button 
        v-if="!isCompact"
        class="btn btn-xs btn-block btn-ghost justify-start gap-2"
        @click="$emit('action', { type: 'settings' })"
      >
        <i class="fa-solid fa-gear"></i> Settings
      </button>
      
      <!-- Compact Toggle Button -->
      <button 
        class="btn btn-xs btn-block btn-ghost justify-center gap-2"
        :title="isCompact ? 'Expand sidebar' : 'Compact sidebar'"
        @click.stop="$emit('toggle-compact')"
      >
        <i :class="isCompact ? 'fa-solid fa-arrow-right' : 'fa-solid fa-arrow-left'"></i>
        <span v-if="!isCompact">Compact</span>
      </button>
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
    chatProfiles: { type: Array, default: () => [] },
  },
  emits: ['select', 'add-subtask', 'action', 'update-search', 'mode-changed', 'toggle-compact', 'delete-chat', 'remove-attachment', 'select-project'],
  computed: {
    rootChildren() {
      return this.allChats.filter(c => c.parent_id === this.rootChat.id)
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
    }
  }
}
</script>