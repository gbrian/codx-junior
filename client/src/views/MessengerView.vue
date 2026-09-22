<script setup>
import MessengerChannelList from '@/components/messenger/MessengerChannelList.vue'
import MessengerGroupInfo from '@/components/messenger/MessengerGroupInfo.vue'
import Chat from '@/components/chat/Chat.vue'
</script>

<template>
  <div
    class="flex h-full w-full overflow-hidden"
    :class="isMobile ? 'flex-col' : 'flex-row'"
    style="background: #111111;"
  >

    <!-- ══ CHANNEL SIDEBAR ══ -->

    <!-- Desktop sidebar -->
    <aside
      v-if="!isMobile"
      class="shrink-0 flex flex-col h-full bg-[#1a1a1a] border-r border-white/5 transition-all duration-200 overflow-hidden"
      :style="sidebarCollapsed ? 'width:64px' : 'width:288px'"
    >
      <MessengerChannelList
        :groups="groupChats"
        :active-chat="activeChat"
        :user-name="$user?.username || 'User'"
        :is-collapsed="sidebarCollapsed"
        :loading="loadingGroups"
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
        class="fixed inset-0 z-40 flex flex-col bg-[#1a1a1a]"
      >
        <div class="flex items-center justify-between px-4 py-4 border-b border-white/5 shrink-0">
          <span class="text-sm font-semibold text-white/80">Channels</span>
          <button class="p-2 text-white/40 hover:text-white" @click="showMobileChannels = false">
            <i class="fas fa-xmark"></i>
          </button>
        </div>
        <div class="flex-1 overflow-hidden">
          <MessengerChannelList
            :groups="groupChats"
            :active-chat="activeChat"
            :user-name="$user?.username || 'User'"
            :is-collapsed="false"
            :loading="loadingGroups"
            @select="chat => { openChat(chat); showMobileChannels = false }"
            @new-group="showNewGroupModal = true; showMobileChannels = false"
            @toggle-collapse="showMobileChannels = false"
            @settings="$emit('settings')"
          />
        </div>
      </div>
    </transition>

    <!-- ══ MAIN AREA ══ -->
    <div class="flex-1 min-w-0 flex flex-col h-full overflow-hidden" :class="isMobile ? 'pb-16' : ''">

      <!-- ── Empty / home state ── -->
      <transition name="fade">
        <div
          v-if="!activeChat"
          class="flex-1 flex flex-col items-center justify-center gap-6 text-white/20"
        >
          <div
            class="absolute inset-0 pointer-events-none"
            style="background: radial-gradient(ellipse 60% 40% at 50% 50%, rgba(99,102,241,0.08) 0%, transparent 70%)"
          ></div>
          <i class="fas fa-hashtag text-5xl relative z-10"></i>
          <div class="text-center relative z-10">
            <p class="text-base text-white/30 font-medium">Select a channel to start chatting</p>
            <p class="text-sm text-white/15 mt-1">or create a new group channel</p>
          </div>
          <button
            class="btn btn-sm bg-primary/20 hover:bg-primary/30 text-primary border-primary/30 border relative z-10"
            @click="showNewGroupModal = true"
          >
            <i class="fas fa-plus mr-2"></i> New Channel
          </button>
        </div>
      </transition>

      <!-- ── Active chat ── -->
      <transition name="fade">
        <div v-if="activeChat" class="flex-1 flex flex-col h-full overflow-hidden">

          <!-- Chat header -->
          <div class="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-white/5 bg-[#111111]/80 backdrop-blur-sm">
            <!-- Mobile back -->
            <button
              v-if="isMobile"
              class="p-2 text-white/40 hover:text-white transition-colors"
              @click="activeChatId = null"
            >
              <i class="fas fa-arrow-left text-sm"></i>
            </button>

            <!-- Channel avatar -->
            <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center shrink-0">
              <span class="text-primary text-xs font-bold">{{ getInitials(activeChat.name) }}</span>
            </div>

            <div class="flex-1 min-w-0">
              <h2 class="text-sm font-semibold text-white/80 truncate"># {{ activeChat.name || 'Channel' }}</h2>
              <p class="text-[11px] text-white/30">
                {{ membersLabel }}
              </p>
            </div>

            <div class="flex items-center gap-1">
              <!-- Hidden messages toggle -->
              <button
                class="btn btn-ghost btn-xs rounded-lg flex items-center gap-1"
                :class="showHidden ? 'text-warning' : 'text-white/30 hover:text-white/70'"
                :title="showHidden ? 'Hide hidden messages' : 'Show hidden messages'"
                @click="showHidden = !showHidden"
              >
                <i :class="showHidden ? 'fas fa-eye' : 'fas fa-eye-slash'"></i>
                <span v-if="hiddenCount" class="text-xs tabular-nums">{{ hiddenCount }}</span>
              </button>

              <!-- Members / info toggle -->
              <button
                class="btn btn-ghost btn-xs text-white/30 hover:text-white/70 rounded-lg"
                :class="showGroupInfo ? 'text-primary' : ''"
                title="Group info & members"
                @click="showGroupInfo = !showGroupInfo"
              >
                <i class="fas fa-users text-sm"></i>
              </button>
              <!-- Loading indicator -->
              <span v-if="isChatLoading" class="loading loading-spinner loading-xs text-primary ml-1"></span>
            </div>
          </div>

          <!-- Content row (messages + optional group info panel) -->
          <div class="flex-1 min-h-0 flex flex-row overflow-hidden">

            <!-- Chat component column -->
            <div class="flex-1 min-w-0 overflow-hidden">
              <Chat
                :chat="activeChat"
                :show-hidden="showHidden"
                class="h-full"
              />
            </div>

            <!-- Group info panel (desktop right panel) -->
            <transition name="slide-right">
              <MessengerGroupInfo
                v-if="showGroupInfo && !isMobile && activeChat"
                :chat="activeChat"
                :profiles="profiles"
                @close="showGroupInfo = false"
                @update-members="updateGroupMembers"
                @update-name="updateGroupName"
                @leave-group="leaveGroup"
              />
            </transition>
          </div>
        </div>
      </transition>

      <!-- Group info drawer (mobile — full overlay) -->
      <transition name="slide-left">
        <div
          v-if="showGroupInfo && isMobile && activeChat"
          class="fixed inset-0 z-50 flex flex-col bg-[#1a1a1a]"
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
    </div>

    <!-- ══ MOBILE BOTTOM NAV ══ -->
    <nav
      v-if="isMobile"
      class="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around bg-[#1a1a1a] border-t border-white/10 px-2 py-2"
    >
      <button
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl transition-colors"
        :class="showMobileChannels ? 'text-primary' : 'text-white/50 hover:text-white'"
        @click="showMobileChannels = !showMobileChannels"
      >
        <i class="fas fa-hashtag text-lg"></i>
        <span class="text-[10px]">Channels</span>
      </button>

      <button
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-white/50 hover:text-white transition-colors"
        @click="showNewGroupModal = true"
      >
        <i class="fas fa-plus text-lg"></i>
        <span class="text-[10px]">New</span>
      </button>

      <button
        v-if="activeChat"
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl transition-colors"
        :class="showGroupInfo ? 'text-primary' : 'text-white/50 hover:text-white'"
        @click="showGroupInfo = !showGroupInfo"
      >
        <i class="fas fa-users text-lg"></i>
        <span class="text-[10px]">Members</span>
      </button>

      <button
        class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-white/50 hover:text-white transition-colors"
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
        <div class="bg-[#1e1e1e] border border-white/10 rounded-2xl w-full max-w-md p-6 flex flex-col gap-5 shadow-2xl">

          <!-- Title -->
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
              <i class="fas fa-hashtag text-primary"></i>
            </div>
            <div>
              <h3 class="text-base font-semibold text-white/90">Create Channel</h3>
              <p class="text-xs text-white/30">Group chat for your team</p>
            </div>
          </div>

          <!-- Channel name -->
          <div class="flex flex-col gap-2">
            <label class="text-xs text-white/40 uppercase tracking-wider font-semibold">Channel Name</label>
            <input
              v-model="newGroupName"
              ref="newGroupNameInput"
              type="text"
              placeholder="e.g. design, backend, general"
              class="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white/80 placeholder:text-white/20 outline-none focus:border-primary/50 transition-colors"
              @keydown.enter="createGroup"
            />
          </div>

          <!-- Add members (profiles) -->
          <div class="flex flex-col gap-2">
            <label class="text-xs text-white/40 uppercase tracking-wider font-semibold">
              Add Members (optional)
            </label>
            <div class="flex items-center gap-2 bg-white/5 rounded-xl px-3 py-2 border border-white/10">
              <i class="fas fa-magnifying-glass text-white/25 text-xs shrink-0"></i>
              <input
                v-model="newGroupMemberSearch"
                type="text"
                placeholder="Search profiles..."
                class="bg-transparent text-xs text-white/70 placeholder:text-white/25 outline-none flex-1"
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
                <button class="hover:text-white/80 transition-colors" @click="newGroupMembers = newGroupMembers.filter(n => n !== name)">
                  <i class="fas fa-xmark text-[10px]"></i>
                </button>
              </div>
            </div>

            <!-- Profile list -->
            <div class="flex flex-col gap-1 max-h-36 overflow-y-auto mt-1">
              <button
                v-for="profile in filteredNewGroupProfiles"
                :key="profile.name"
                class="flex items-center gap-3 px-3 py-2 rounded-xl text-left w-full hover:bg-white/6 transition-colors"
                @click="toggleNewGroupMember(profile.name)"
              >
                <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  :class="newGroupMembers.includes(profile.name) ? 'bg-primary/30' : 'bg-white/8'">
                  <i v-if="profile.icon" :class="[profile.icon, newGroupMembers.includes(profile.name) ? 'text-primary' : 'text-white/40']"
                    class="text-xs"></i>
                  <span v-else
                    :class="newGroupMembers.includes(profile.name) ? 'text-primary' : 'text-white/40'"
                    class="text-xs font-bold">{{ profile.name?.charAt(0)?.toUpperCase() }}</span>
                </div>
                <span class="text-xs text-white/60 flex-1 truncate">{{ profile.name }}</span>
                <i v-if="newGroupMembers.includes(profile.name)" class="fas fa-check text-primary text-xs"></i>
              </button>
              <div v-if="filteredNewGroupProfiles.length === 0" class="text-center py-3 text-white/20 text-xs">
                {{ newGroupMemberSearch ? 'No matches' : 'No profiles available' }}
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-3">
            <button
              class="flex-1 btn btn-sm bg-white/5 hover:bg-white/10 text-white/50 border-white/10 border"
              @click="showNewGroupModal = false"
            >
              Cancel
            </button>
            <button
              class="flex-1 btn btn-sm bg-primary hover:bg-primary/80 text-white border-none"
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
      loadingGroups: false,
      groupChats: [],

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
    activeChat() {
      if (!this.activeChatId) return null
      return this.$storex.chats.chats[this.activeChatId] || null
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
    await this.loadGroupChats()
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
    async loadGroupChats() {
      try {
        this.loadingGroups = true
        const project = this.$project
        if (!project?.$api) return

        const response = await project.$api.chats.getRecentChats({
          filters: { mode: 'group' },
          page: 1,
          pageSize: 100
        })

        if (response?.chats) {
          this.groupChats = response.chats.filter(c => c.mode === 'group')
          // Register them in store for reactive updates
          this.groupChats.forEach(chat => {
            if (!this.$storex.chats.chats[chat.id]) {
              this.$storex.chats.chats[chat.id] = chat
            }
          })
        }
      } catch (err) {
        console.error('[Messenger] loadGroupChats error', err)
      } finally {
        this.loadingGroups = false
      }
    },

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
      } catch (err) {
        console.error('[Messenger] openChat error', err)
      } finally {
        this.isChatLoading = false
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
          mode: 'group',
          board: 'messenger',
          profiles: this.newGroupMembers,
          messages: [],
          owner_project_id: ownerProject?.project_id
        })
        if (chat) {
          this.groupChats.unshift(chat)
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
        const idx = this.groupChats.findIndex(c => c.id === this.activeChatId)
        if (idx !== -1) this.groupChats[idx] = { ...this.groupChats[idx], profiles }
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
        const idx = this.groupChats.findIndex(c => c.id === this.activeChatId)
        if (idx !== -1) this.groupChats[idx] = { ...this.groupChats[idx], name }
      } catch (err) {
        console.error('[Messenger] updateGroupName error', err)
      }
    },

    leaveGroup(chat) {
      if (!chat) return
      this.groupChats = this.groupChats.filter(c => c.id !== chat.id)
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