<script setup>
import Chat from '@/components/chat/Chat.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import TeamSettings from '@/components/teams/TeamSettings.vue'
import ChannelSettings from '@/components/teams/ChannelSettings.vue'
import CategorySettings from '@/components/teams/CategorySettings.vue'
import MemberSettings from '@/components/teams/MemberSettings.vue'
import CreateChannelDialog from '@/components/teams/CreateChannelDialog.vue'
import CreateTeamDialog from '@/components/teams/CreateTeamDialog.vue'
import MediaManager from '@/components/media/MediaManager.vue'
</script>

<template>
  <div class="flex h-full bg-base-300 overflow-hidden">

    <!-- ── Team icons column ──────────────────────────────────────────────── -->
    <div class="flex flex-col items-center gap-2 px-2 py-3 bg-base-200 border-r border-base-content/10 w-16 shrink-0 overflow-y-auto">
      <div
        v-for="team in teams"
        :key="team.id"
        class="tooltip tooltip-right cursor-pointer shrink-0"
        :data-tip="team.name"
        @click="selectTeam(team.id)"
      >
        <div
          class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg font-bold transition-all duration-200 hover:rounded-xl overflow-hidden"
          :class="activeTeam?.id === team.id
            ? 'ring-2 ring-primary rounded-xl'
            : 'hover:opacity-90'"
          :style="{ backgroundColor: team.color || '#6366f1' }"
        >
          <img v-if="team.icon" :src="team.icon" class="w-full h-full object-cover" />
          <span v-else class="text-white font-bold">{{ team.name?.[0]?.toUpperCase() }}</span>
        </div>
      </div>

      <div class="divider my-0 w-8 mx-auto"></div>

      <!-- Media manager toggle -->
      <div
        class="tooltip tooltip-right cursor-pointer shrink-0"
        data-tip="Media Manager"
        @click="showMediaManager = !showMediaManager"
      >
        <div
          class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl"
          :class="showMediaManager
            ? 'bg-primary text-primary-content'
            : 'bg-base-300 text-base-content hover:bg-base-content/10'"
        >
          <i class="fa-solid fa-image"></i>
        </div>
      </div>

      <!-- Add team -->
      <div
        class="tooltip tooltip-right cursor-pointer shrink-0"
        data-tip="Create Team"
        @click="showCreateTeam = true"
      >
        <div class="w-10 h-10 rounded-2xl flex items-center justify-center text-success bg-base-300 hover:bg-success/20 hover:rounded-xl transition-all duration-200">
          <i class="fa-solid fa-plus"></i>
        </div>
      </div>
    </div>

    <!-- ── Media Manager Panel ───────────────────────────────────────────── -->
    <div
      v-if="showMediaManager"
      class="w-96 border-r border-base-content/10 bg-base-200 shrink-0 flex flex-col overflow-hidden"
    >
      <MediaManager
        v-if="activeTeam"
        :resource-type="'team'"
        :resource-id="activeTeam.id"
      />
      <div v-else class="flex-1 flex items-center justify-center text-base-content/50">
        <p class="text-sm">Select a team to manage media</p>
      </div>
    </div>

    <!-- ── Channels sidebar ───────────────────────────────────────────────── -->
    <div class="flex flex-col w-52 bg-base-200 border-r border-base-content/10 shrink-0" v-if="activeTeam">

      <!-- Team header -->
      <div
        class="flex items-center justify-between px-3 py-3 border-b border-base-content/10 cursor-pointer hover:bg-base-300/50"
        @click="showTeamSettings = true"
      >
        <span class="font-bold text-sm truncate">{{ activeTeam.name }}</span>
        <i class="fa-solid fa-chevron-down text-xs text-base-content/50"></i>
      </div>

      <!-- Search -->
      <div class="px-2 py-2">
        <div class="flex items-center gap-1 input input-sm input-bordered bg-base-300 w-full">
          <i class="fa-solid fa-magnifying-glass text-xs text-base-content/50"></i>
          <input v-model="channelSearch" class="bg-transparent w-full min-w-0 text-xs" placeholder="Search..." />
        </div>
      </div>

      <!-- Categories + channels -->
      <div class="flex-1 overflow-y-auto px-1">
        <div v-for="category in filteredCategories" :key="category.id" class="mb-2">

          <!-- Category row -->
          <div
            class="flex items-center gap-1 px-1 py-1 cursor-pointer text-xs font-semibold text-base-content/50 hover:text-base-content uppercase tracking-wide group"
          >
            <span @click="toggleCategory(category.id)" class="flex items-center gap-1 flex-1 min-w-0">
              <i
                class="fa-solid fa-chevron-down text-xs transition-transform shrink-0"
                :class="category.collapsed ? '-rotate-90' : ''"
              ></i>
              <span class="truncate">{{ category.name }}</span>
            </span>
            <span class="flex gap-0.5 opacity-0 group-hover:opacity-100 shrink-0">
              <button
                class="btn btn-xs btn-ghost p-0 w-4 h-4 min-h-0"
                @click.stop="openCreateChannel(category.id)"
                title="Add channel"
              >
                <i class="fa-solid fa-plus text-xs"></i>
              </button>
              <button
                class="btn btn-xs btn-ghost p-0 w-4 h-4 min-h-0"
                @click.stop="editCategory(category)"
                title="Edit category"
              >
                <i class="fa-solid fa-pen text-xs"></i>
              </button>
            </span>
          </div>

          <!-- Channels list -->
          <div v-if="!category.collapsed">
            <div
              v-for="channel in category.channels"
              :key="channel.id"
              class="flex items-center gap-2 px-2 py-1 rounded cursor-pointer text-sm group"
              :class="activeChannel?.id === channel.id
                ? 'bg-base-content/15 text-base-content'
                : 'text-base-content/60 hover:bg-base-content/10 hover:text-base-content'"
              @click="selectChannel(channel, category)"
            >
              <ChatIcon :mode="channel.mode" class="text-xs w-4 shrink-0" />
              <span class="truncate flex-1 text-xs">{{ channel.name }}</span>
              <span v-if="channel.unread" class="badge badge-xs badge-primary shrink-0">
                {{ channel.unread }}
              </span>
              <button
                class="btn btn-ghost btn-xs p-0 w-4 h-4 min-h-0 opacity-0 group-hover:opacity-100 shrink-0"
                @click.stop="editChannel(channel, category)"
              >
                <i class="fa-solid fa-gear text-xs"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Add category button -->
        <button
          class="flex items-center gap-1 px-2 py-1 text-xs text-base-content/40 hover:text-primary cursor-pointer w-full"
          @click="addCategory"
        >
          <i class="fa-solid fa-plus text-xs"></i>
          Add category
        </button>
      </div>

      <!-- User status bar -->
      <div class="flex items-center gap-2 px-3 py-2 border-t border-base-content/10 bg-base-300/50 shrink-0">
        <div
          class="w-7 h-7 rounded-full bg-primary text-primary-content flex items-center justify-center text-xs font-bold shrink-0"
        >
          {{ userInitial }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-xs font-semibold truncate">{{ $users.user?.username }}</div>
          <div class="text-xs text-success flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-success inline-block"></span>
            Online
          </div>
        </div>
        <button class="btn btn-xs btn-ghost" @click="showMembers = !showMembers">
          <i class="fa-solid fa-users text-xs"></i>
        </button>
      </div>
    </div>

    <!-- Empty sidebar when no team -->
    <div
      v-else
      class="flex flex-col items-center justify-center w-52 bg-base-200 border-r border-base-content/10 gap-3 text-base-content/40"
    >
      <i class="fa-solid fa-people-group text-4xl"></i>
      <span class="text-xs text-center px-4">Select or create a team</span>
    </div>

    <!-- ── Main content ───────────────────────────────────────────────────── -->
    <div class="flex flex-col flex-1 min-w-0 overflow-hidden">

      <!-- Channel selected -->
      <template v-if="activeChannel && activeChannelChat">

        <!-- Channel header -->
        <div class="flex items-center gap-3 px-4 py-2 border-b border-base-content/10 bg-base-200/50 shrink-0">
          <ChatIcon :mode="activeChannel.mode" class="text-base-content/60" />
          <span class="font-bold text-sm">{{ activeChannel.name }}</span>
          <span
            v-if="activeChannel.description"
            class="text-xs text-base-content/50 border-l border-base-content/20 pl-2 truncate"
          >
            {{ activeChannel.description }}
          </span>
          <div class="flex items-center gap-1 ml-auto shrink-0">
            <button
              class="btn btn-xs btn-ghost tooltip"
              :data-tip="showChannelSearch ? 'Close search' : 'Search'"
              @click="showChannelSearch = !showChannelSearch; messageSearch = ''"
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
            <input v-model="messageSearch" class="bg-transparent flex-1 min-w-0 text-sm" placeholder="Search messages..." />
            <button @click="showChannelSearch = false; messageSearch = ''" class="text-base-content/50 hover:text-base-content">
              <i class="fa-solid fa-xmark text-xs"></i>
            </button>
          </div>
        </div>

        <!-- Chat + members panel -->
        <div class="flex-1 min-h-0 flex overflow-hidden">
          <Chat
            class="flex-1 min-w-0 p-2"
            :chat="activeChannelChat"
            :filter="messageSearch"
          />

          <!-- Members panel -->
          <div
            class="w-52 border-l border-base-content/10 bg-base-200/50 flex flex-col shrink-0"
            v-if="showMembers"
          >
            <div class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-base-content/50 border-b border-base-content/10 flex items-center justify-between">
              <span>Members — {{ activeTeam.members.length }}</span>
              <button class="btn btn-xs btn-ghost" @click="showAddMember = true">
                <i class="fa-solid fa-plus text-xs"></i>
              </button>
            </div>
            <div class="flex-1 overflow-y-auto px-2 py-2 flex flex-col gap-1">
              <div
                v-for="member in activeTeam.members"
                :key="member.id"
                class="flex items-center gap-2 px-2 py-1 rounded hover:bg-base-content/10 cursor-pointer group"
                @click="selectedMember = member"
              >
                <div
                  class="w-6 h-6 rounded-full bg-secondary text-secondary-content flex items-center justify-center text-xs font-bold shrink-0"
                >
                  {{ member.username?.[0]?.toUpperCase() }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-xs font-medium truncate">{{ member.username }}</div>
                  <div class="text-xs text-base-content/40 truncate capitalize">{{ member.role }}</div>
                </div>
                <span class="w-2 h-2 rounded-full shrink-0" :class="statusColor(member.status)"></span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- No channel selected but team exists -->
      <div
        v-else-if="activeTeam"
        class="flex-1 flex flex-col items-center justify-center gap-4 text-base-content/40"
      >
        <i class="fa-solid fa-hashtag text-5xl"></i>
        <div class="text-center">
          <div class="font-bold text-lg text-base-content/60">Welcome to {{ activeTeam.name }}</div>
          <div class="text-sm mt-1">Select a channel or create one to start chatting</div>
        </div>
        <button class="btn btn-sm btn-primary" @click="showCreateChannel = true">
          <i class="fa-solid fa-plus mr-1"></i> Create Channel
        </button>
      </div>

      <!-- No team -->
      <div
        v-else
        class="flex-1 flex flex-col items-center justify-center gap-4 text-base-content/40"
      >
        <i class="fa-solid fa-people-group text-5xl"></i>
        <div class="text-center">
          <div class="font-bold text-lg text-base-content/60">Team Collaboration</div>
          <div class="text-sm mt-1">Create or select a team to start collaborating</div>
        </div>
        <button class="btn btn-sm btn-primary" @click="showCreateTeam = true">
          <i class="fa-solid fa-plus mr-1"></i> Create Team
        </button>
      </div>
    </div>

    <!-- ── Modals ─────────────────────────────────────────────────────────── -->

    <!-- Create team -->
    <modal v-if="showCreateTeam">
      <CreateTeamDialog
        @created="onTeamCreated"
        @close="showCreateTeam = false"
      />
    </modal>

    <!-- Create channel -->
    <modal v-if="showCreateChannel && activeTeam">
      <CreateChannelDialog
        :team="activeTeam"
        :default-category-id="createChannelCategoryId"
        @created="onChannelCreated"
        @close="showCreateChannel = false"
      />
    </modal>

    <!-- Team settings -->
    <modal close="true" @close="showTeamSettings = false" v-if="showTeamSettings && activeTeam">
      <TeamSettings
        :team="activeTeam"
        @save="onSaveTeam"
        @delete="onDeleteTeam"
        @close="showTeamSettings = false"
      />
    </modal>

    <!-- Channel settings -->
    <modal close="true" @close="editingChannel = null" v-if="editingChannel">
      <ChannelSettings
        :channel="editingChannel"
        @save="onSaveChannel"
        @delete="onDeleteChannel"
        @close="editingChannel = null"
      />
    </modal>

    <!-- Category settings -->
    <modal close="true" @close="editingCategory = null" v-if="editingCategory">
      <CategorySettings
        :category="editingCategory"
        @save="onSaveCategory"
        @delete="onDeleteCategory"
        @close="editingCategory = null"
      />
    </modal>

    <!-- Member settings -->
    <modal close="true" @close="selectedMember = null" v-if="selectedMember">
      <MemberSettings
        :member="selectedMember"
        @save="onSaveMember"
        @remove="onRemoveMember"
        @close="selectedMember = null"
      />
    </modal>

    <!-- Add member -->
    <modal v-if="showAddMember">
      <div class="flex flex-col gap-4 p-2 w-80">
        <h3 class="font-bold text-lg">Add Member</h3>
        <div class="form-control gap-1">
          <label class="label label-text text-xs font-semibold">Username</label>
          <input
            v-model="newMemberUsername"
            type="text"
            class="input input-bordered input-sm"
            placeholder="username"
            @keydown.enter="addMember"
          />
        </div>
        <div class="form-control gap-1">
          <label class="label label-text text-xs font-semibold">Role</label>
          <select class="select select-bordered select-sm" v-model="newMemberRole">
            <option value="admin">Admin</option>
            <option value="moderator">Moderator</option>
            <option value="member">Member</option>
            <option value="guest">Guest</option>
          </select>
        </div>
        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="showAddMember = false">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="!newMemberUsername.trim()" @click="addMember">
            Add
          </button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  name: 'TeamView',
  props: ['params'],
  data() {
    return {
      // UI state
      channelSearch: '',
      messageSearch: '',
      showChannelSearch: false,
      showMembers: false,
      showMediaManager: false,
      // Modals
      showCreateTeam: false,
      showCreateChannel: false,
      showTeamSettings: false,
      createChannelCategoryId: null,
      editingChannel: null,
      editingChannelCategory: null,
      editingCategory: null,
      selectedMember: null,
      showAddMember: false,
      newMemberUsername: '',
      newMemberRole: 'member',
      // Active chat backing the selected channel
      activeChannelChat: null
    }
  },
  created() {
    // Initialize store from localStorage
    this.$storex.teams.init()
    this.$storex.media.init()
    // Restore active channel chat if one was saved
    if (this.activeChannel?.chatId) {
      this.loadChannelChat(this.activeChannel)
    }
  },
  computed: {
    teams() {
      return this.$storex.teams.teams
    },
    activeTeam() {
      return this.$storex.teams.activeTeam
    },
    activeChannel() {
      return this.$storex.teams.activeChannel
    },
    userInitial() {
      return this.$users.user?.username?.[0]?.toUpperCase() || '?'
    },
    filteredCategories() {
      if (!this.activeTeam) return []
      const cats = this.activeTeam.categories || []
      if (!this.channelSearch) return cats
      const q = this.channelSearch.toLowerCase()
      return cats.map(cat => ({
        ...cat,
        channels: cat.channels.filter(c => c.name.toLowerCase().includes(q))
      })).filter(cat => cat.channels.length)
    }
  },
  watch: {
    // Reload chat when active channel changes (e.g. team switch)
    activeChannel(ch) {
      if (ch?.chatId) {
        this.loadChannelChat(ch)
      } else {
        this.activeChannelChat = null
      }
    }
  },
  methods: {
    // ── Team actions ────────────────────────────────────────────────────────
    selectTeam(teamId) {
      this.$storex.teams.selectTeam(teamId)
      this.activeChannelChat = null
    },

    onTeamCreated(team) {
      this.showCreateTeam = false
    },

    onSaveTeam(updated) {
      this.$storex.teams.updateTeam(updated)
      this.showTeamSettings = false
    },

    onDeleteTeam(teamId) {
      this.$storex.teams.deleteTeam(teamId)
      this.showTeamSettings = false
    },

    // ── Category actions ────────────────────────────────────────────────────
    addCategory() {
      if (!this.activeTeam) return
      this.$storex.teams.createCategory({
        teamId: this.activeTeam.id,
        name: 'New Category'
      })
    },

    editCategory(category) {
      this.editingCategory = { ...category }
    },

    toggleCategory(categoryId) {
      if (!this.activeTeam) return
      this.$storex.teams.toggleCategoryCollapsed({
        teamId: this.activeTeam.id,
        categoryId
      })
    },

    onSaveCategory(updated) {
      this.$storex.teams.updateCategory({
        teamId: this.activeTeam.id,
        category: updated
      })
      this.editingCategory = null
    },

    onDeleteCategory() {
      if (!this.editingCategory) return
      this.$storex.teams.deleteCategory({
        teamId: this.activeTeam.id,
        categoryId: this.editingCategory.id
      })
      this.editingCategory = null
    },

    // ── Channel actions ─────────────────────────────────────────────────────
    openCreateChannel(categoryId = null) {
      this.createChannelCategoryId = categoryId || this.activeTeam?.categories[0]?.id || null
      this.showCreateChannel = true
    },

    async onChannelCreated(channel) {
      this.showCreateChannel = false
      // Auto-select newly created channel
      await this.selectChannel(channel, this.findCategoryForChannel(channel.id))
    },

    async selectChannel(channel, category) {
      const catId = category?.id || channel.categoryId
      await this.$storex.teams.selectChannel({
        teamId: this.activeTeam.id,
        channelId: channel.id
      })
      await this.loadChannelChat(channel)
    },

    async loadChannelChat(channel) {
      if (!channel?.chatId) {
        this.activeChannelChat = null
        return
      }
      // Load from chats store if not already cached
      const cached = this.$chats.chats[channel.chatId]
      if (cached) {
        this.activeChannelChat = cached
      } else {
        const loaded = await this.$chats.loadChat({ id: channel.chatId })
        this.activeChannelChat = this.$chats.chats[channel.chatId] || loaded
      }
    },

    editChannel(channel, category) {
      this.editingChannel = { ...channel }
      this.editingChannelCategory = category
    },

    onSaveChannel(updated) {
      this.$storex.teams.updateChannel({
        teamId: this.activeTeam.id,
        categoryId: this.editingChannelCategory?.id || updated.categoryId,
        channel: updated
      })
      this.editingChannel = null
    },

    onDeleteChannel() {
      if (!this.editingChannel) return
      this.$storex.teams.deleteChannel({
        teamId: this.activeTeam.id,
        categoryId: this.editingChannelCategory?.id || this.editingChannel.categoryId,
        channelId: this.editingChannel.id
      })
      this.editingChannel = null
      this.activeChannelChat = null
    },

    findCategoryForChannel(channelId) {
      return this.activeTeam?.categories.find(cat =>
        cat.channels.some(ch => ch.id === channelId)
      ) || null
    },

    // ── Member actions ──────────────────────────────────────────────────────
    addMember() {
      if (!this.newMemberUsername.trim() || !this.activeTeam) return
      this.$storex.teams.addMember({
        teamId: this.activeTeam.id,
        memberData: {
          username: this.newMemberUsername.trim(),
          role: this.newMemberRole,
          status: 'offline'
        }
      })
      this.newMemberUsername = ''
      this.newMemberRole = 'member'
      this.showAddMember = false
    },

    onSaveMember(updated) {
      this.$storex.teams.updateMember({
        teamId: this.activeTeam.id,
        member: updated
      })
      this.selectedMember = null
    },

    onRemoveMember() {
      if (!this.selectedMember || !this.activeTeam) return
      this.$storex.teams.removeMember({
        teamId: this.activeTeam.id,
        memberId: this.selectedMember.id
      })
      this.selectedMember = null
    },

    // ── UI helpers ──────────────────────────────────────────────────────────
    statusColor(status) {
      return {
        online: 'bg-success',
        away: 'bg-warning',
        busy: 'bg-error',
        offline: 'bg-base-content/30'
      }[status] || 'bg-base-content/30'
    }
  }
}
</script>