<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
import TeamSettings from '@/components/teams/TeamSettings.vue'
import ChannelSettings from '@/components/teams/ChannelSettings.vue'
import CategorySettings from '@/components/teams/CategorySettings.vue'
import MemberSettings from '@/components/teams/MemberSettings.vue'
import MemberAvatar from '@/components/teams/MemberAvatar.vue'
import CreateChannelDialog from '@/components/teams/CreateChannelDialog.vue'
import CreateTeamDialog from '@/components/teams/CreateTeamDialog.vue'
import AddMemberDialog from '@/components/teams/AddMemberDialog.vue'
import MainMenu from '@/components/main-menu/MainMenu.vue'
import Desktop from '@/components/desktop/Desktop.vue'
import StatuBar from '@/components/StatuBar.vue'
import UserInfo from '@/components/UserInfo.vue'
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

      <!-- Media manager toggle — opens as Desktop panel -->
      <div
        class="tooltip tooltip-right cursor-pointer shrink-0"
        data-tip="Media Library"
        @click="openMediaLibrary"
      >
        <div
          class="w-10 h-10 rounded-2xl flex items-center justify-center text-lg transition-all duration-200 hover:rounded-xl bg-base-300 text-base-content hover:bg-base-content/10"
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

      <div class="grow"></div>
      <MainMenu />
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

        <!-- Channel categories -->
        <div v-for="category in filteredCategories" :key="category.id" class="mb-2">

          <!-- Category row -->
          <div class="flex items-center gap-1 px-1 py-1 cursor-pointer text-xs font-semibold text-base-content/50 hover:text-base-content uppercase tracking-wide group">
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
              class="flex items-center gap-2 px-2 py-1 rounded cursor-pointer text-sm group text-base-content/60 hover:bg-base-content/10 hover:text-base-content"
              @click="openChannel(channel)"
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

        <!-- ── Direct Messages section ──────────────────────────────────── -->
        <div class="mt-3">
          <div class="flex items-center gap-1 px-1 py-1 text-xs font-semibold text-base-content/50 uppercase tracking-wide group">
            <span
              class="flex items-center gap-1 flex-1 cursor-pointer"
              @click="dmCollapsed = !dmCollapsed"
            >
              <i
                class="fa-solid fa-chevron-down text-xs transition-transform shrink-0"
                :class="dmCollapsed ? '-rotate-90' : ''"
              ></i>
              Direct Messages
            </span>
            <button
              class="btn btn-xs btn-ghost p-0 w-4 h-4 min-h-0 opacity-0 group-hover:opacity-100"
              @click.stop="showAddMember = true"
              title="Add member"
            >
              <i class="fa-solid fa-plus text-xs"></i>
            </button>
          </div>

          <!-- Member DM list -->
          <div v-if="!dmCollapsed">
            <div
              v-for="member in activeTeam.members"
              :key="member.id"
              class="flex items-center gap-2 px-2 py-1 rounded cursor-pointer group text-base-content/60 hover:bg-base-content/10 hover:text-base-content"
              @click="openDm(member)"
            >
              <MemberAvatar :member="member" size="xs" :show-status="true" class="shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="text-xs truncate font-medium">{{ member.username }}</div>
              </div>
              <button
                class="btn btn-ghost btn-xs p-0 w-4 h-4 min-h-0 opacity-0 group-hover:opacity-100 shrink-0"
                @click.stop="selectedMember = member"
                title="Member settings"
              >
                <i class="fa-solid fa-gear text-xs"></i>
              </button>
            </div>

            <div
              v-if="!activeTeam.members.length"
              class="px-3 py-2 text-xs text-base-content/30 italic"
            >
              No members yet
            </div>

            <button
              class="flex items-center gap-1 px-2 py-1 text-xs text-base-content/40 hover:text-primary cursor-pointer w-full"
              @click="showAddMember = true"
            >
              <i class="fa-solid fa-user-plus text-xs"></i>
              Add member
            </button>
          </div>
        </div>
      </div>

      <!-- User status bar -->
      <div class="flex items-center gap-2 px-3 py-2 border-t border-base-content/10 bg-base-300/50 shrink-0">
        <div class="flex justify-between">
          <div class="w-7 h-7 rounded-full bg-primary text-primary-content flex items-center justify-center text-xs font-bold shrink-0">
            {{ userInitial }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-xs font-semibold truncate">{{ $users.user?.username }}</div>
            <div class="text-xs text-success flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-success inline-block"></span>
              Online
            </div>
          </div>
          <UserInfo />
        </div>
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

    <!-- ── Main content placeholder (channels open in Desktop panels) ──── -->
    <div class="flex flex-col flex-1 min-w-0 overflow-hidden items-center justify-center text-base-content/40">
      <Desktop />
      <StatuBar class="w-full" />
      <!-- template v-if="activeTeam">
        <i class="fa-solid fa-hashtag text-5xl"></i>
        <div class="text-center">
          <div class="font-bold text-lg text-base-content/60">{{ activeTeam.name }}</div>
          <div class="text-sm mt-1">Select a channel or DM to open it as a panel</div>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-sm btn-primary" @click="openCreateChannel(null)">
            <i class="fa-solid fa-plus mr-1"></i> Create Channel
          </button>
          <button class="btn btn-sm btn-outline" @click="showAddMember = true">
            <i class="fa-solid fa-user-plus mr-1"></i> Add Member
          </button>
        </div>
      </template>
      <template v-else>
        <i class="fa-solid fa-people-group text-5xl"></i>
        <div class="text-center">
          <div class="font-bold text-lg text-base-content/60">Team Collaboration</div>
          <div class="text-sm mt-1">Create or select a team to start collaborating</div>
        </div>
        <button class="btn btn-sm btn-primary" @click="showCreateTeam = true">
          <i class="fa-solid fa-plus mr-1"></i> Create Team
        </button>
      </template -->
    </div>

    <!-- ── Modals ─────────────────────────────────────────────────────────── -->

    <modal v-if="showCreateTeam">
      <CreateTeamDialog @created="onTeamCreated" @close="showCreateTeam = false" />
    </modal>

    <modal v-if="showCreateChannel && activeTeam">
      <CreateChannelDialog
        :team="activeTeam"
        :default-category-id="createChannelCategoryId"
        @created="onChannelCreated"
        @close="showCreateChannel = false"
      />
    </modal>

    <modal close="true" @close="showTeamSettings = false" v-if="showTeamSettings && activeTeam">
      <TeamSettings
        :team="activeTeam"
        @save="onSaveTeam"
        @delete="onDeleteTeam"
        @close="showTeamSettings = false"
      />
    </modal>

    <modal close="true" @close="editingChannel = null" v-if="editingChannel">
      <ChannelSettings
        :channel="editingChannel"
        @save="onSaveChannel"
        @delete="onDeleteChannel"
        @close="editingChannel = null"
      />
    </modal>

    <modal close="true" @close="editingCategory = null" v-if="editingCategory">
      <CategorySettings
        :category="editingCategory"
        @save="onSaveCategory"
        @delete="onDeleteCategory"
        @close="editingCategory = null"
      />
    </modal>

    <modal close="true" @close="selectedMember = null" v-if="selectedMember">
      <MemberSettings
        :member="selectedMember"
        @save="onSaveMember"
        @remove="onRemoveMember"
        @close="selectedMember = null"
      />
    </modal>

    <modal v-if="showAddMember && activeTeam">
      <AddMemberDialog
        :team="activeTeam"
        @added="onMemberAdded"
        @close="showAddMember = false"
      />
    </modal>
  </div>
</template>

<script>
export default {
  name: 'TeamView',
  props: ['params'],
  data() {
    return {
      channelSearch: '',
      dmCollapsed: false,
      // Modals
      showCreateTeam: false,
      showCreateChannel: false,
      showTeamSettings: false,
      showAddMember: false,
      createChannelCategoryId: null,
      editingChannel: null,
      editingChannelCategory: null,
      editingCategory: null,
      selectedMember: null
    }
  },
  created() {
    this.$storex.teams.init()
    this.$storex.media.init()
  },
  computed: {
    teams() {
      return this.$storex.teams.teams
    },
    activeTeam() {
      return this.$storex.teams.activeTeam
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
  methods: {
    // ── Team actions ──────────────────────────────────────────────────────────
    selectTeam(teamId) {
      this.$storex.teams.selectTeam(teamId)
    },

    onTeamCreated() {
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

    // ── Category actions ──────────────────────────────────────────────────────
    addCategory() {
      if (!this.activeTeam) return
      this.$storex.teams.createCategory({ teamId: this.activeTeam.id, name: 'New Category' })
    },

    editCategory(category) {
      this.editingCategory = { ...category }
    },

    toggleCategory(categoryId) {
      if (!this.activeTeam) return
      this.$storex.teams.toggleCategoryCollapsed({ teamId: this.activeTeam.id, categoryId })
    },

    onSaveCategory(updated) {
      this.$storex.teams.updateCategory({ teamId: this.activeTeam.id, category: updated })
      this.editingCategory = null
    },

    onDeleteCategory() {
      if (!this.editingCategory) return
      this.$storex.teams.deleteCategory({ teamId: this.activeTeam.id, categoryId: this.editingCategory.id })
      this.editingCategory = null
    },

    // ── Channel actions ───────────────────────────────────────────────────────
    openCreateChannel(categoryId = null) {
      this.createChannelCategoryId = categoryId || this.activeTeam?.categories[0]?.id || null
      this.showCreateChannel = true
    },

    // Open channel as a Desktop panel via ui store
    openChannel(channel) {
      this.$storex.teams.markChannelRead({ teamId: this.activeTeam.id, channelId: channel.id })
      this.$storex.ui.openTeamChannel({ team: this.activeTeam, channel })
    },

    async onChannelCreated(channel) {
      this.showCreateChannel = false
      this.openChannel(channel)
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
    },

    // ── DM actions — open as Desktop panel ───────────────────────────────────
    openDm(member) {
      this.$storex.ui.openTeamDM({ team: this.activeTeam, member })
    },

    // ── Media library — open as Desktop panel ────────────────────────────────
    openMediaLibrary() {
      if (!this.activeTeam) return
      this.$storex.ui.openTeamMediaLibrary({ team: this.activeTeam })
    },

    // ── Member actions ────────────────────────────────────────────────────────
    onMemberAdded() {
      this.showAddMember = false
    },

    onSaveMember(updated) {
      this.$storex.teams.updateMember({ teamId: this.activeTeam.id, member: updated })
      this.selectedMember = null
    },

    onRemoveMember() {
      if (!this.selectedMember || !this.activeTeam) return
      this.$storex.teams.removeMember({ teamId: this.activeTeam.id, memberId: this.selectedMember.id })
      this.selectedMember = null
    }
  }
}
</script>