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
    profiles: {
      type: Array,
      default: () => []
    },
    selectedProfiles: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:selected-profiles'],
  data() {
    return {}
  },
  computed: {},
  watch: {},
  methods: {
    onProfilesSelected(selectedItems) {
      this.$emit('update:selected-profiles', selectedItems)
    }
  }
}
</script>