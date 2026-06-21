<script setup>
import Chat from '@/components/chat/Chat.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import MemberAvatar from '@/components/teams/MemberAvatar.vue'
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Channel header -->
    <div class="flex items-center gap-3 px-4 py-2 border-b border-base-content/10 bg-base-200/50 shrink-0">
      <ChatIcon :mode="channel.mode" class="text-base-content/60" />
      <span class="font-bold text-sm">{{ channel.name }}</span>
      <span
        v-if="channel.description"
        class="text-xs text-base-content/50 border-l border-base-content/20 pl-2 truncate"
      >
        {{ channel.description }}
      </span>
      <div class="flex items-center gap-1 ml-auto shrink-0">
        <button
          class="btn btn-xs btn-ghost tooltip"
          :data-tip="showChannelSearch ? 'Close search' : 'Search'"
          @click="toggleSearch"
        >
          <i class="fa-solid fa-magnifying-glass text-xs"></i>
        </button>
        <button
          class="btn btn-xs btn-ghost tooltip"
          data-tip="Members"
          :class="showMembers ? 'btn-active' : ''"
          @click="showMembers = !showMembers"
        >
          <i class="fa-solid fa-users text-xs"></i>
        </button>
      </div>
    </div>

    <!-- Search bar -->
    <div class="px-4 py-2 border-b border-base-content/10 shrink-0" v-if="showChannelSearch">
      <div class="flex items-center gap-2 input input-sm input-bordered w-full">
        <i class="fa-solid fa-magnifying-glass text-xs"></i>
        <input
          v-model="messageSearch"
          class="bg-transparent flex-1 min-w-0 text-sm"
          placeholder="Search messages..."
        />
        <button @click="toggleSearch" class="text-base-content/50 hover:text-base-content">
          <i class="fa-solid fa-xmark text-xs"></i>
        </button>
      </div>
    </div>

    <!-- Chat + members panel -->
    <div class="flex-1 min-h-0 flex overflow-hidden">
      <Chat
        v-if="chat"
        class="flex-1 min-w-0 p-2"
        :chat="chat"
        :filter="messageSearch"
      />
      <div v-else class="flex-1 flex items-center justify-center text-base-content-ERROR-40">
        <span class="loading loading-spinner"></span>
      </div>

      <!-- Members panel -->
      <div
        class="w-52 border-l border-base-content/10 bg-base-200/50 flex flex-col shrink-0"
        v-if="showMembers && team"
      >
        <div class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-base-content/50 border-b border-base-content/10 flex items-center justify-between">
          <span>Members — {{ team.members.length }}</span>
        </div>
        <div class="flex-1 overflow-y-auto px-2 py-2 flex flex-col gap-1">
          <div
            v-for="member in team.members"
            :key="member.id"
            class="flex items-center gap-2 px-2 py-1 rounded hover:bg-base-content/10 cursor-pointer"
            @click="openDm(member)"
          >
            <MemberAvatar :member="member" size="xs" :show-status="true" />
            <div class="flex-1 min-w-0">
              <div class="text-xs font-medium truncate">{{ member.username }}</div>
              <div class="text-xs text-base-content-ERROR-40 capitalize">{{ member.role }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TeamChannel',
  props: {
    params: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      chat: null,
      showChannelSearch: false,
      showMembers: false,
      messageSearch: ''
    }
  },
  computed: {
    channel() {
      return this.params?.channel || {}
    },
    team() {
      return this.params?.team || null
    }
  },
  created() {
    this.loadChat()
  },
  methods: {
    async loadChat() {
      const chatId = this.channel?.chatId
      if (!chatId) return
      const cached = this.$chats.chats[chatId]
      if (cached) {
        this.chat = cached
      } else {
        const loaded = await this.$chats.loadChat({ id: chatId })
        this.chat = this.$chats.chats[chatId] || loaded
      }
    },
    toggleSearch() {
      this.showChannelSearch = !this.showChannelSearch
      this.messageSearch = ''
    },
    async openDm(member) {
      if (!this.team) return
      await this.$storex.ui.openTeamDM({ team: this.team, member })
    }
  }
}
</script>