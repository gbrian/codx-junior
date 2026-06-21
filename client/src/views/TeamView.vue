<script setup>
import TeamSettings from '@/components/teams/TeamSettings.vue'
import ChannelSettings from '@/components/teams/ChannelSettings.vue'
import CategorySettings from '@/components/teams/CategorySettings.vue'
import MemberSettings from '@/components/teams/MemberSettings.vue'
import CreateChannelDialog from '@/components/teams/CreateChannelDialog.vue'
import CreateTeamDialog from '@/components/teams/CreateTeamDialog.vue'
import AddMemberDialog from '@/components/teams/AddMemberDialog.vue'
import Desktop from '@/components/desktop/Desktop.vue'
import StatuBar from '@/components/StatuBar.vue'
import TeamQuickBar from '@/components/teams/TeamQuickBar.vue'
import TeamBar from '@/components/teams/TeamBar.vue'
import VibeCodingView from '@/views/VibeCodingView.vue'
</script>

<template>
  <div class="flex h-full bg-base-300 overflow-hidden">

    <!-- ── Team icons + QuickBar column ──────────────────────────────────── -->
    <TeamQuickBar
      :teams="teams"
      :active-team="activeTeam"
      @new-quick-chat="onNewQuickChat"
      @select-team="selectTeam"
      @create-team="showCreateTeam = true"
      @open-media="openMediaLibrary"
    />

    <!-- ── Combined Channels + Recents sidebar column ─────────────────────── -->
    <TeamBar
      v-if="activeTeam"
      :active-team="activeTeam"
      @open-team-settings="showTeamSettings = true"
      @open-create-channel="openCreateChannel"
      @edit-category="editCategory"
      @edit-channel="onEditChannel"
      @add-member="showAddMember = true"
      @select-member="onSelectMember"
    />

    <!-- Empty sidebar when no team -->
    <div
      v-else
      class="flex flex-col items-center justify-center w-64 bg-base-200 border-r border-base-content/10 gap-3 text-base-content/40"
    >
      <i class="fa-solid fa-people-group text-4xl"></i>
      <span class="text-xs text-center px-4">Select or create a team</span>
    </div>

    <!-- ── Main content placeholder (channels open in Desktop panels) ──── -->
    <div class="flex flex-col flex-1 min-w-0 overflow-hidden items-center justify-center text-base-content/40"
      v-if="isExpertMode"
    >
      <Desktop />
      <StatuBar class="w-full" />
    </div>
    <VibeCodingView v-else />

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
    isExpertMode() {
      return this.$storex.ui.viewMode === 'expert'
    }
  },
  methods: {
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
    editCategory(category) {
      this.editingCategory = { ...category }
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
    openCreateChannel(categoryId = null) {
      this.createChannelCategoryId = categoryId || this.activeTeam?.categories[0]?.id || null
      this.showCreateChannel = true
    },
    openChannel(channel) {
      this.$storex.teams.markChannelRead({ teamId: this.activeTeam.id, channelId: channel.id })
      this.$storex.ui.openTeamChannel({ team: this.activeTeam, channel })
    },
    async onChannelCreated(channel) {
      this.showCreateChannel = false
      this.openChannel(channel)
    },
    onEditChannel({ channel, category }) {
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
    },
    async onNewQuickChat() {
      const chat = await this.$service.chat.newQuickChat()
      this.$ui.openChat(chat)
    },
    openMediaLibrary() {
      if (!this.activeTeam) return
      this.$storex.ui.openTeamMediaLibrary({ team: this.activeTeam })
    },
    onSelectMember(member) {
      this.selectedMember = member
    }
  }
}
</script>