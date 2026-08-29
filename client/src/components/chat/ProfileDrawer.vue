<script setup>
import ChatProfileSelector from './ChatProfileSelector.vue'
</script>

<template>
  <div class="drawer drawer-open">
    <input 
      id="profile-drawer"
      type="checkbox" 
      class="drawer-toggle" 
      :checked="isOpen"
      @change="$emit('update:is-open', $event.target.checked)"
    />
    
    <!-- Main content area -->
    <div class="drawer-content" @click="handleContentClick">
      <slot />
    </div>

    <!-- Drawer sidebar -->
    <div class="drawer-side" :class="{ 'z-50': isOpen }">
      <label for="profile-drawer" class="drawer-overlay"></label>
      
      <div class="menu p-4 w-64 min-h-full bg-base-200 text-base-content flex flex-col gap-4">
        <!-- Header -->
        <div class="flex items-center justify-between border-b border-base-300 pb-3">
          <h2 class="text-lg font-bold flex items-center gap-2">
            <i class="fa-solid fa-users"></i>
            <span>Profiles</span>
          </h2>
          <label for="profile-drawer" class="btn btn-sm btn-ghost btn-circle">
            <i class="fa-solid fa-times"></i>
          </label>
        </div>

        <!-- Profile Selector -->
        <div class="flex-1 overflow-auto">
          <ChatProfileSelector
            :project="project"
            :selected-profiles="selectedProfiles"
            @profiles-changed="onProfilesChanged"
          />
        </div>

        <!-- Footer info -->
        <div class="border-t border-base-300 pt-3 text-xs text-base-content/60">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-info-circle"></i>
            <span>{{ selectedProfiles.length }} profile(s) selected</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    project: {
      type: Object,
      default: null
    },
    selectedProfiles: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:is-open', 'profiles-changed'],
  methods: {
    onProfilesChanged(selectedProfiles) {
      this.$emit('profiles-changed', selectedProfiles)
    },
    handleContentClick() {
      // Close drawer when clicking on main content on mobile
      if (window.innerWidth < 1024) {
        this.$emit('update:is-open', false)
      }
    }
  }
}
</script>