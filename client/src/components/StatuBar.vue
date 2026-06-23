<script setup>
import EventBar from './EventBar.vue'
import UserInfo from '@/components/UserInfo.vue'
</script>
<template>
  <div class="relative flex p-1 bg-base-100 items-center gap-2">
    <div class="grow"></div>
    <EventBar />
    
    <!-- User Status Section -->
    <div class="flex items-center gap-2 border-l border-base-content/10 pl-2">
      <div class="flex items-center gap-2 min-w-0">
        <div class="w-7 h-7 rounded-full bg-primary text-primary-content flex items-center justify-center text-xs font-bold shrink-0">
          {{ userInitial }}
        </div>
        <div class="flex flex-col min-w-0">
          <div class="text-xs font-semibold truncate">{{ $users.user?.username }}</div>
          <div class="text-xs text-success flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-success inline-block"></span>
            Online
          </div>
        </div>
      </div>
      <UserInfo>
        <template #trigger="{ togglePanel, dailyLimitStatus }">
          <button
            class="btn btn-xs btn-ghost p-1 w-6 h-6 min-h-0"
            @click="togglePanel"
            :class="dailyLimitStatus === 'exceeded' ? 'text-error' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-info'"
          >
            <i class="fa-solid fa-circle-info"></i>
          </button>
        </template>
      </UserInfo>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StatuBar',
  computed: {
    userInitial() {
      return this.$users.user?.username?.[0]?.toUpperCase() || '?'
    }
  }
}
</script>