<script setup>
import Selector from './Selector.vue'
import ProfileCard from '../ProfileCard.vue'
</script>

<template>
  <Selector
    :items="profiles"
    :selected-items="selectedProfiles"
    :label="label"
    :icon="icon"
    :single="single"
    :allow-deselect="allowDeselect"
    :empty-label="emptyLabel"
    @select="onProfileSelected"
    @update:selected-items="onProfilesSelected"
  >
    <!-- Custom profile card rendering in mini style -->
    <template #default="{ item, selected }">
      <div :class="selected ? 'ring-2 ring-primary rounded-lg' : 'rounded-lg'">
        <ProfileCard :profile="item" :mini="$ui.isMobile" />
      </div>
    </template>
  </Selector>
</template>

<script>
export default {
  props: {
    project: {
      type: Object,
      default: null
    },
    openFromBottom: {
      type: Boolean,
      default: false
    },
    selectedProfiles: {
      type: Array,
      default: () => []
    },
    // Single-selection mode: only one profile can be selected at a time.
    // Listeners receive the selected profile only (`select` event + a list with
    // one item at most), which is what single-valued fields (a board assignee)
    // need.
    single: {
      type: Boolean,
      default: false
    },
    // Single mode only: clicking the selected profile clears the selection
    allowDeselect: {
      type: Boolean,
      default: false
    },
    // Trigger button label / icon / "nothing selected" hint
    label: {
      type: String,
      default: 'Profiles'
    },
    icon: {
      type: String,
      default: 'fa-solid fa-plus'
    },
    emptyLabel: {
      type: String,
      default: ''
    }
  },
  emits: ['update:selected-profiles', 'profiles-changed', 'select'],
  data() {
    return {
      profiles: []
    }
  },
  mounted() {
    this.loadProfiles(this.project || this.$project)
  },
  watch: {
    project: {
      handler(newProject) {
        if (newProject) {
          this.loadProfiles(newProject)
        }
      },
      immediate: true
    }
  },
  methods: {
    async loadProfiles(project) {
      try {
        if (project?.$api) {
          const profilesList = await project?.$api.profiles.list()
          this.profiles = (profilesList || []).sort((a, b) => a.name > b.name ? 1 : -1)
        }
      } catch (error) {
        console.error('[ChatProfileSelector] Error loading profiles:', error)
        this.profiles = []
      }
    },
    onProfilesSelected(selectedItems) {
      this.$emit('update:selected-profiles', selectedItems)
      this.$emit('profiles-changed', selectedItems)
    },
    // Single mode: the selector reports the clicked profile (null when cleared),
    // so a single-valued field never receives a list.
    onProfileSelected(profile) {
      const selected = profile ? [profile] : []
      this.$emit('select', profile?.name || null)
      this.$emit('update:selected-profiles', selected)
      this.$emit('profiles-changed', selected)
    }
  }
}
</script>
