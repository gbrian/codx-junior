<script setup>
import EventBar from './EventBar.vue'
import UserInfo from '@/components/UserInfo.vue'
import ProjectDetailt from './ProjectDetailt.vue';
</script>

<template>
  <div class="flex items-center gap-4 px-4 py-2 bg-base-100 border-b border-base-content/10 h-12 shrink-0">
    
    <ProjectDetailt 
      @click.stop=""
      :options="{ folders: true, showIcon: true }"
      @select="$storex.projects.setActiveProject($event)"
    />

    <div class="grow"></div>

    <!-- Center: Event Bar -->
    <EventBar />

    <!-- Right: Expand TeamBar Button + User Info -->
    <div class="flex items-center gap-2 border-l border-base-content/10 pl-3 shrink-0">
      <!-- User Info with dropdown -->
      <UserInfo>
        <template #trigger="{ togglePanel, dailyLimitStatus }">
          <button
            class="btn btn-xs btn-ghost p-1 w-6 h-6 min-h-0"
            @click="togglePanel"
            :class="dailyLimitStatus === 'exceeded' ? 'text-error' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-info'"
          >
            <div class="avatar tooltip" :data-tip="$user.username">
              <div class="w-8">
                <img :src="$user.avatar">
              </div>
            </div>
          </button>
        </template>
      </UserInfo>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TopBar',
  props: {
    projectName: {
      type: String,
      default: null
    },
    activeTeam: {
      type: Object,
      default: null
    }
  },
  emits: ['toggle-team-bar'],
  computed: {
    userInitial() {
      return this.$users.user?.username?.[0]?.toUpperCase() || '?'
    }
  }
}
</script>