<script setup>
</script>
<template>
  <select id="branchSource" class="select select-bordered select-xs w-full max-w-xs" 
    v-model="selectedBranch">
    <option v-for="projectBranch in allBranches" :key="projectBranch"
      :value="projectBranch">
      {{ projectBranch }}
    </option>
  </select>
</template>
<script>
export default {
  props: ['modelValue', 'localChanges', 'branches'],
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
    allBranches() {
      let branches = (this.branches || [])
      if (this.localChanges) {
        branches = ['local', ...branches]
      }
      return branches
    }
  }
}
</script>