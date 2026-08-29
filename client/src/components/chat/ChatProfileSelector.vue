<script setup>
import Selector from './Selector.vue'
import ProfileCard from '../ProfileCard.vue'
</script>

<template>
  <Selector
    :items="profiles"
    :selected-items="selectedProfiles"
    label="Profiles"
    icon="fa-solid fa-plus"
    :is-single-select="false"
    :use-modal="useModal"
    @update:selected-items="onProfilesSelected"
  >
    <!-- Custom profile card rendering in mini style -->
    <template #default="{ item, selected }">
      <div :class="selected ? 'ring-2 ring-primary rounded-lg' : 'rounded-lg'">
        <ProfileCard :profile="item" :mini="true" />
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
    useModal: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:selected-profiles', 'profiles-changed'],
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
          this.profiles = profilesList || []
        }
      } catch (error) {
        console.error('[ChatProfileSelector] Error loading profiles:', error)
        this.profiles = []
      }
    },
    onProfilesSelected(selectedItems) {
      this.$emit('update:selected-profiles', selectedItems)
      this.$emit('profiles-changed', selectedItems)
    }
  }
}
</script>