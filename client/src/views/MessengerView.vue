<script setup>
import MessengerChannelList from '@/components/messenger/MessengerChannelList.vue'
import MessengerGroupInfo from '@/components/messenger/MessengerGroupInfo.vue'
import ChatView from '@/views/ChatView.vue'
import { countChannelUnread } from '@/utils/chatUnread'
</script>

<template>
  <div
    class="flex h-full w-full overflow-hidden bg-base-100"
    :class="isMobile ? 'flex-col' : 'flex-row'"
  >

    <!-- ══ CHANNEL SIDEBAR (left) ══ -->

    <!-- Desktop sidebar -->
    <aside
      v-if="!isMobile"
      class="shrink-0 flex flex-col h-full bg-base-200 border-r border-base-content/10 transition-all duration-200 overflow-hidden"
      :style="sidebarCollapsed ? 'width:64px' : 'width:288px'"
    >
      <MessengerChannelList
        :groups="channels"
        :active-chat="activeChat"
        :user-name="$user?.username || 'User'"
        :is-collapsed="sidebarCollapsed"
        :loading="loadingChannels"
        :unread-counts="unreadCounts"
        @select="openChat"
        @new-group="showNewGroupModal = true"
        @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
        @settings="$emit('settings')"
      />
    </aside>

    <!-- Mobile: channel list drawer -->
    <transition name="slide-left">
      <div
        v-if="isMobile && showMobileChannels"
        class="fixed inset-0 z-40 flex flex-col bg-base-200"
      >
        <div class="flex items-center justify-between px-4 py-4 border-b border-base-content/10 shrink-0">
          <span class="text-sm font-semibold text-base-content">Channels</span>
          <button
            class="w-9 h-9 flex items-center justify-center rounded-lg text-base-content/50 hover:text-base-content hover:bg-base-content/5 transition-colors"
            @click="showMobileChannels = false"
          >
            <i class="fas fa-xmark"></i>
          </button>
        </div>
        <div class="flex-1 overflow-hidden">
          <MessengerChannelList
            :groups="channels"
            :active-chat="activeChat"
            :user-name="$user?.username || 'User'"
            :is-collapsed="false"
            :loading="loadingChannels"
            :unread-counts="unreadCounts"
            @select="chat => { openChat(chat); showMobileChannels = false }"
            @new-group="showNewGroupModal = true; showMobileChannels = false"
            @toggle-collapse="showMobileChannels = false"
            @settings="$emit('settings')"
          />
        </div>
      </div>
    </transition>

    <!-- ══ MAIN AREA ══ -->
    <div class="relative flex-1 min-w-0 flex flex-col h-full overflow-hidden bg-base-100" :class="isMobile ? 'pb-16' : ''">

      <!-- ── Empty / home state ── -->
      <transition name="fade">
        <div
          v-if="!activeChat"
          class="flex-1 flex flex-col items-center justify-center gap-6 text-base-content/50"
        >
          <div
            class="absolute inset-0 pointer-events-none"
            style="background: radial-gradient(ellipse 60% 40% at 50% 50%, rgba(99,102,241,0.08) 0%, transparent 70%)"
          ></div>
          <i class="fas fa-hashtag text-5xl relative z-10"></i>
          <div class="text-center relative z-10">
            <p class="text-base text-base-content/70 font-medium">Select a channel to start chatting</p>
            <p class="text-sm text-base-content/50 mt-1">or create a new group channel</p>
          </div>
          <button
            class="btn btn-sm bg-primary/20 hover:bg-primary/30 text-primary border-primary/30 border relative z-10"
            @click="showNewGroupModal = true"
          >
            <i class="fas fa-plus mr-2"></i> New Channel
          </button>
        </div>
      </transition>

      <!-- ── Active chat with ChatView ──
           The channel list is on the left (above), the chat sidebar — now on the
           RIGHT via ChatView's `flex-row-reverse` — acts as the channel action
           rail. Its `sidebar-actions` slot hosts the members (group info)
           toggle, which used to float over the chat header. -->
      <transition name="fade">
        <ChatView
          v-if="activeChat"
          :chat="activeChat"
          class="flex-1 w-full h-full"
        >
          <template #sidebar-actions>
            <button
              class="flex-1 flex items-center justify-center h-9 rounded-lg transition-colors duration-150 focus:ring-2 focus:ring-primary/50 focus:outline-none"
              :class="showGroupInfo
                ? 'text-primary bg-primary/15'
                : 'text-base-content/60 hover:text-base-content/90 hover:bg-base-200'"
              :title="showGroupInfo ? 'Hide channel members' : 'Channel members'"
              :aria-pressed="showGroupInfo ? 'true' : 'false'"
              @click="showGroupInfo = !showGroupInfo"
            >
              <i class="fas fa-users text-sm"></i>
            </button>
          </template>
        </ChatView>
      </transition>
    </div>

    <!-- ══ DESKTOP MEMBERS PANEL ══ -->
    <aside v-if="!isMobile && activeChat && showGroupInfo" class="shrink-0 h-full">
      <MessengerGroupInfo
        :chat="activeChat"
        :profiles="profiles"
        @close="showGroupInfo = false"
        @update-members="updateGroupMembers"
        @update-name="updateGroupName"
        @leave-group="leaveGroup"
      />
    </aside>

    <!-- ══ MOBILE MEMBERS PANEL ══ -->
    <transition name="slide-right">
      <div
        v-if="isMobile && activeChat && showGroupInfo"
        class="fixed inset-0 z-50 bg-base-200"
      >
        <MessengerGroupInfo
          :chat="activeChat"
          :profiles="profiles"
          @close="showGroupInfo = false"
          @update-members="updateGroupMembers"
          @update-name="updateGroupName"
          @leave-group="leaveGroup"
        />
      </div>
    </transition>

    <!-- ══ MOBILE BOTTOM NAV ══ -->
    <nav
      v-if="isMobile"
      class="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around bg-base-200 border-t border-base-content/10 px-2 py-2"
    >
      <button
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl transition-colors"
        :class="showMobileChannels ? 'text-primary' : 'text-base-content/60 hover:text-base-content'"
        @click="showMobileChannels = !showMobileChannels"
      >
        <i class="fas fa-hashtag text-lg"></i>
        <span class="text-[10px]">Channels</span>
      </button>

      <button
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-base-content/60 hover:text-base-content transition-colors"
        @click="showNewGroupModal = true"
      >
        <i class="fas fa-plus text-lg"></i>
        <span class="text-[10px]">New</span>
      </button>

      <button
        v-if="activeChat"
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl transition-colors"
        :class="showGroupInfo ? 'text-primary' : 'text-base-content/60 hover:text-base-content'"
        @click="showGroupInfo = !showGroupInfo"
      >
        <i class="fas fa-users text-lg"></i>
        <span class="text-[10px]">Members</span>
      </button>

      <button
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-base-content/60 hover:text-base-content transition-colors"
        @click="$emit('account-settings')"
      >
        <div class="w-6 h-6 rounded-full bg-primary/30 flex items-center justify-center">
          <i class="fas fa-user text-xs text-primary"></i>
        </div>
        <span class="text-[10px]">Account</span>
      </button>
    </nav>

    <!-- ══ NEW GROUP MODAL ══ -->
    <transition name="fade">
      <div
        v-if="showNewGroupModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4"
        @click.self="showNewGroupModal = false"
      >
        <div class="bg-base-200 border border-base-content/10 rounded-2xl w-full max-w-md p-6 flex flex-col gap-5 shadow-2xl">

          <!-- Title -->
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
              <i class="fas fa-hashtag text-primary"></i>
            </div>
            <div>
              <h3 class="text-base font-semibold text-base-content">Create Channel</h3>
              <p class="text-xs text-base-content/60">Group chat for your team</p>
            </div>
          </div>

          <!-- Channel name -->
          <div class="flex flex-col gap-2">
            <label
              class="text-xs text-base-content/60 uppercase tracking-wider font-semibold"
              for="new-channel-name"
            >Channel Name</label>
            <input
              id="new-channel-name"
              v-model="newGroupName"
              ref="newGroupNameInput"
              type="text"
              placeholder="e.g. design, backend, general"
              class="bg-base-content/5 border border-base-content/15 rounded-xl px-4 py-3 text-sm text-base-content placeholder:text-base-content/40 outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/30 transition-colors"
              @keydown.enter="createGroup"
            />
          </div>

          <!-- Add members (profiles) -->
          <div class="flex flex-col gap-2">
            <label
              class="text-xs text-base-content/60 uppercase tracking-wider font-semibold"
              for="new-channel-member-search"
            >
              Add Members (optional)
            </label>
            <div class="flex items-center gap-2 bg-base-content/5 rounded-xl px-3 py-2 border border-base-content/15">
              <i class="fas fa-magnifying-glass text-base-content/50 text-xs shrink-0"></i>
              <input
                id="new-channel-member-search"
                v-model="newGroupMemberSearch"
                type="text"
                placeholder="Search profiles..."
                class="bg-transparent text-xs text-base-content placeholder:text-base-content/40 outline-none flex-1"
              />
            </div>

            <!-- Selected members chips -->
            <div v-if="newGroupMembers.length" class="flex flex-wrap gap-2 mt-1">
              <div
                v-for="name in newGroupMembers"
                :key="name"
                class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-medium"
              >
                <span>{{ name }}</span>
                <button class="hover:text-base-content transition-colors" @click="newGroupMembers = newGroupMembers.filter(n => n !== name)">
                  <i class="fas fa-xmark text-[10px]"></i>
                </button>
              </div>
            </div>

            <!-- Profile list -->
            <div class="flex flex-col gap-1 max-h-36 overflow-y-auto mt-1">
              <button
                v-for="profile in filteredNewGroupProfiles"
                :key="profile.name"
                class="flex items-center gap-3 px-3 py-2 rounded-xl text-left w-full hover:bg-base-content/5 transition-colors"
                @click="toggleNewGroupMember(profile.name)"
              >
                <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  :class="newGroupMembers.includes(profile.name) ? 'bg-primary/30' : 'bg-base-content/10'">
                  <i v-if="profile.icon" :class="[profile.icon, newGroupMembers.includes(profile.name) ? 'text-primary' : 'text-base-content/60']"
                    class="text-xs"></i>
                  <span v-else
                    :class="newGroupMembers.includes(profile.name) ? 'text-primary' : 'text-base-content/60'"
                    class="text-xs font-bold">{{ profile.name?.charAt(0)?.toUpperCase() }}</span>
                </div>
                <span class="text-xs text-base-content/80 flex-1 truncate">{{ profile.name }}</span>
                <i v-if="newGroupMembers.includes(profile.name)" class="fas fa-check text-primary text-xs"></i>
              </button>
              <div v-if="filteredNewGroupProfiles.length === 0" class="text-center py-3 text-base-content/50 text-xs">
                {{ newGroupMemberSearch ? 'No matches' : 'No profiles available' }}
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3">
            <button
              class="flex-1 btn btn-sm bg-base-content/5 hover:bg-base-content/10 text-base-content/80 border-base-content/15 border"
              @click="showNewGroupModal = false"
            >
              Cancel
            </button>
            <button
              class="flex-1 btn btn-sm bg-primary hover:bg-primary/80 text-primary-content border-none"
              :disabled="!newGroupName.trim() || creatingGroup"
              @click="createGroup"
            >
              <span v-if="creatingGroup" class="loading loading-spinner loading-xs"></span>
              <i v-else class="fas fa-hashtag text-xs"></i>
              Create Channel
            </button>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script>
export default {
  emits: ['settings', 'account-settings'],
  data() {
    return {
      // Chat state
      activeChatId: null,
      isChatLoading: false,
      loadingChannels: false,

      // UI state
      sidebarCollapsed: false,
      showMobileChannels: false,
      showGroupInfo: false,
      showHidden: false,

      // New group modal
      showNewGroupModal: false,
      newGroupName: '',
      newGroupMembers: [],
      newGroupMemberSearch: '',
      creatingGroup: false,

      // Profiles / members
      profiles: []
    }
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    channels() {
      return this.$storex.chats.channels
    },
    activeChat() {
      if (!this.activeChatId) return null
      return this.$storex.chats.chats[this.activeChatId] || null
    },
    currentUsername() {
      return this.$user?.username || this.$storex?.users?.user?.username || null
    },
    // Derived unread per channel — nothing is persisted on the chat
    unreadCounts() {
      const counts = {}
      const username = this.currentUsername
      if (!username) return counts
      this.channels.forEach(chat => {
        counts[chat.id] = countChannelUnread(chat.messages, username)
      })
      return counts
    },
    hiddenCount() {
      return this.activeChat?.messages?.filter(m => m.hide)?.length || 0
    },
    membersLabel() {
      const count = this.activeChat?.profiles?.length || 0
      if (count === 0) return 'No members yet'
      const memberNames = (this.activeChat.profiles || []).slice(0, 3).join(', ')
      const extra = count > 3 ? ` +${count - 3} more` : ''
      return memberNames + extra
    },
    filteredNewGroupProfiles() {
      const q = this.newGroupMemberSearch.toLowerCase()
      return this.profiles.filter(p => !q || p.name?.toLowerCase().includes(q))
    },
    chatProject() {
      return this.$projects.activeProject
    }
  },
  watch: {
    '$project'() {
      this.loadProfiles()
    },
    showNewGroupModal(val) {
      if (val) {
        this.newGroupName = ''
        this.newGroupMembers = []
        this.newGroupMemberSearch = ''
        this.$nextTick(() => this.$refs.newGroupNameInput?.focus())
      }
    },
    // Reset showHidden when switching channels
    activeChatId() {
      this.showHidden = false
    }
  },
  async created() {
    this.loadProfiles()
    // Open chat from query param if present
    const chatId = this.$route?.query?.chatId
    if (chatId) {
      await this.openChat({ id: chatId })
    }
  },
  methods: {

    // ── Helpers ─────────────────────────────────────────────
    getInitials(name) {
      if (!name) return '#'
      const words = name.trim().split(/\s+/)
      if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
      return name.substring(0, 2).toUpperCase()
    },

    // ── Data loading ─────────────────────────────────────────
    async loadProfiles() {
      try {
        const project = this.$project
        if (project?.$api) {
          const list = await project.$api.profiles.list()
          this.profiles = (list || []).sort((a, b) => a.name > b.name ? 1 : -1)
        }
      } catch (err) {
        console.error('[Messenger] loadProfiles error', err)
        this.profiles = []
      }
    },

    // ── Chat open ────────────────────────────────────────────
    async openChat(chat) {
      if (!chat) return
      try {
        this.isChatLoading = true
        this.showGroupInfo = false
        const loaded = await this.$chats.loadChat(chat)
        this.activeChatId = loaded?.id || chat.id
        await this.markChannelAsSeen(this.activeChat)
      } catch (err) {
        console.error('[Messenger] openChat error', err)
      } finally {
        this.isChatLoading = false
      }
    },

    // Mark every unseen message of the channel as read for the current user,
    // so the unread badge clears without a reload
    async markChannelAsSeen(chat) {
      const username = this.currentUsername
      const messages = chat?.messages || []
      if (!username || !chat?.id || !messages.length) return
      const markSeen = this.$storex.chats.markMessageAsSeen
      if (typeof markSeen !== 'function') return
      const pending = messages.filter(m => m?.doc_id && m.user !== username &&
        (!m.read_by || !m.read_by.includes(username)))
      for (const message of pending) {
        try {
          await markSeen({ chat_id: chat.id, message_id: message.doc_id, username })
        } catch (err) {
          console.error('[Messenger] markChannelAsSeen error', err)
          break
        }
      }
    },

    // ── Create group ─────────────────────────────────────────
    async createGroup() {
      const name = this.newGroupName.trim()
      if (!name || this.creatingGroup) return
      try {
        this.creatingGroup = true
        const ownerProject = this.chatProject
        const chat = await this.$chats.createNewChat({
          name,
          mode: 'channel',
          board: 'messenger',
          profiles: this.newGroupMembers,
          messages: [],
          owner_project_id: ownerProject?.project_id
        })
        if (chat) {
          this.showNewGroupModal = false
          await this.openChat(chat)
        }
      } catch (err) {
        console.error('[Messenger] createGroup error', err)
        this.$ui?.addNotification?.({ text: 'Failed to create channel', type: 'error' })
      } finally {
        this.creatingGroup = false
      }
    },

    toggleNewGroupMember(name) {
      if (this.newGroupMembers.includes(name)) {
        this.newGroupMembers = this.newGroupMembers.filter(n => n !== name)
      } else {
        this.newGroupMembers.push(name)
      }
    },

    // ── Group management ─────────────────────────────────────
    async updateGroupMembers(profiles) {
      if (!this.activeChat) return
      try {
        await this.$storex.chats.saveChatInfo({
          ...this.activeChat,
          profiles
        })
        if (this.$storex.chats.chats[this.activeChatId]) {
          this.$storex.chats.chats[this.activeChatId].profiles = profiles
        }
      } catch (err) {
        console.error('[Messenger] updateGroupMembers error', err)
      }
    },

    async updateGroupName(name) {
      if (!this.activeChat) return
      try {
        await this.$storex.chats.saveChatInfo({
          ...this.activeChat,
          name
        })
        if (this.$storex.chats.chats[this.activeChatId]) {
          this.$storex.chats.chats[this.activeChatId].name = name
        }
      } catch (err) {
        console.error('[Messenger] updateGroupName error', err)
      }
    },

    leaveGroup(chat) {
      if (!chat) return
      if (this.activeChatId === chat.id) {
        this.activeChatId = null
        this.showGroupInfo = false
      }
    }
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-left-enter-active, .slide-left-leave-active { transition: transform 0.25s ease, opacity 0.25s ease; }
.slide-left-enter-from, .slide-left-leave-to { transform: translateX(-100%); opacity: 0; }

.slide-right-enter-active, .slide-right-leave-active { transition: transform 0.25s ease, opacity 0.25s ease; }
.slide-right-enter-from, .slide-right-leave-to { transform: translateX(100%); opacity: 0; }
</style>