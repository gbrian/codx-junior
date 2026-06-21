<script setup>
import ChatIcon from '@/components/chat/ChatIcon.vue'
import MemberAvatar from '@/components/teams/MemberAvatar.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
</script>

<template>
  <div class="flex flex-col w-full" v-if="activeTeam">

    <!-- Project dropdown / context -->
    <ProjectDetailt class="px-4 py-4"
      @click.stop=""
      :options="{ folders: true, showIcon: true }"
      @select="$projects.setActiveProject($event)"
    />

    <!-- Team header -->
    <div
      class="flex items-center justify-between px-3 py-3 border-b border-base-content/10 cursor-pointer hover:bg-base-300/50"
      @click="$emit('open-team-settings')"
    >
      <span class="font-bold text-sm truncate">{{ activeTeam.name }}</span>
      <i class="fa-solid fa-chevron-down text-xs text-base-content/50"></i>
    </div>

    <!-- Search channels -->
    <div class="px-2 py-2">
      <div class="flex items-center gap-1 input input-sm input-bordered bg-base-300 w-full">
        <i class="fa-solid fa-magnifying-glass text-xs text-base-content/50"></i>
        <input v-model="channelSearch" class="bg-transparent w-full min-w-0 text-xs" placeholder="Search..." />
      </div>
    </div>

    <!-- Categories + channels -->
    <div class="px-1 flex flex-col gap-1">

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
              @click.stop="$emit('open-create-channel', category.id)"
              title="Add channel"
            >
              <i class="fa-solid fa-plus text-xs"></i>
            </button>
            <button
              class="btn btn-xs btn-ghost p-0 w-4 h-4 min-h-0"
              @click.stop="$emit('edit-category', category)"
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
              @click.stop="$emit('edit-channel', { channel, category })"
            >
              <i class="fa-solid fa-gear text-xs"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Add category button -->
      <button
        class="flex items-center gap-1 px-2 py-1 text-xs text-base-content-ERROR-40 hover:text-primary cursor-pointer w-full mb-3"
        @click="addCategory"
      >
        <i class="fa-solid fa-plus text-xs"></i>
        Add category
      </button>

      <!-- ── Direct Messages section ──────────────────────────────────── -->
      <div class="mt-1">
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
            @click.stop="$emit('add-member')"
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
              @click.stop="$emit('select-member', member)"
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
            class="flex items-center gap-1 px-2 py-1 text-xs text-base-content-ERROR-40 hover:text-primary cursor-pointer w-full mt-1"
            @click="$emit('add-member')"
          >
            <i class="fa-solid fa-user-plus text-xs"></i>
            Add member
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TeamChannelsSidebar',
  props: {
    activeTeam: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      channelSearch: '',
      dmCollapsed: false
    }
  },
  computed: {
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
    toggleCategory(categoryId) {
      if (!this.activeTeam) return
      this.$storex.teams.toggleCategoryCollapsed({ teamId: this.activeTeam.id, categoryId })
    },
    addCategory() {
      if (!this.activeTeam) return
      this.$storex.teams.createCategory({ teamId: this.activeTeam.id, name: 'New Category' })
    },
    openChannel(channel) {
      this.$storex.teams.markChannelRead({ teamId: this.activeTeam.id, channelId: channel.id })
      this.$storex.ui.openTeamChannel({ team: this.activeTeam, channel })
    },
    openDm(member) {
      this.$storex.ui.openTeamDM({ team: this.activeTeam, member })
    }
  }
}
</script>