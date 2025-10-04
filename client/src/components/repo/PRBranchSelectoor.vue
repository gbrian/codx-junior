<script setup>
import BranchSelector from './BranchSelector.vue'
</script>
<template lang="pug">
  div.flex.gap-2.items-center
    span From 
    BranchSelector(v-model="fromBranchSelected", :local-changes="true")
    span To 
    BranchSelector(v-model="toBranchSelected")
</template>
<script>
export default {
  props: ['fromBranch', 'toBranch'],
  data() {
    return {
      fromBranchSelected: this.fromBranch,
      toBranchSelected: this.toBranch
    }
  },
  watch: {
    fromBranchSelected() {
      this.selectBranches()
    },
    toBranchSelected() {
      this.selectBranches()
    }
  },
  methods: {
    selectBranches() {
      this.$emit('select', { 
        fromBranch: this.fromBranchSelected,
        toBranch: this.toBranchSelected
      })
    }
  }
}
</script>