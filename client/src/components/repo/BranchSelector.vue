<script setup>
</script>
<template>
  <select id="branchSource" class="select select-bordered select-xs w-full max-w-xs" 
    v-model="selectedBranch">
    <option v-for="projectBranch in branches" :key="projectBranch"
      :value="projectBranch">
      {{ projectBranch }}
    </option>
  </select>
</template>
<script>
export default {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  data() {
    return {
      // Variable to store the selected branch
      selectedBranch: this.modelValue
    }
  },
  watch: {
    selectedBranch(value) {
      this.$emit('update:modelValue', value)
    }
  },
  computed: {
    // Get the list of branches from the store
    branches() {
      return this.$storex.projects.project_branches.branches
    }
  }
}
</script>