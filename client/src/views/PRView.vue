<script setup>
import Markdown from '@/components/Markdown.vue'
</script>

<template>
  <div class="pr-view p-4">
    <header class="flex justify-between items-center">
      <div>
        <h1 class="text-lg font-bold">Latest Changes</h1>
        .flex.gap-2
          <label for="branchSource" class="block text-sm font-medium mb-1">Source Branch:</label>
          <select id="branchSource" class="select select-bordered select-sm w-full max-w-xs" v-model="selectedBranchSource">
            <option v-for="branch in projectBranches" :key="branch" :value="branch">
              {{ branch }}
            </option>
          </select>
          <label for="branchTarget" class="block text-sm font-medium mt-2 mb-1">Target Branch:</label>
          <select id="branchTarget" class="select select-bordered select-sm w-full max-w-xs" v-model="selectedBranchTarget">
            <option v-for="branch in projectBranches" :key="branch" :value="branch">
              {{ branch }}
            </option>
          </select>
      </div>
      <div class="flex gap-2 items-center">
        <button class="btn btn-sm" @click="copyTextToClipboard">
          <i class="fa-solid fa-copy"></i>
        </button>
        <button @click="refreshChangesSummary(true)" class="btn btn-outline btn-sm">
          <i class="fas fa-sync-alt"></i> Rebuild
        </button>
      </div>
    </header>
    <Markdown :text="$projects.changesSummary" v-if="$projects.changesSummary"/>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedBranchSource: null,
      selectedBranchTarget: null
    }
  },
  mounted() {
    this.refreshChangesSummary(false)
  },
  computed: {
    branches () {
      return this.$projects.branches
    },
    project () {
      return this.$project
    }
  },
  watch: {
    project () {
      this.refreshChangesSummary()
    }
  },
  methods: {
    copyTextToClipboard() {
      this.$ui.copyTextToClipboard($projects.changesSummary)
    },
    refreshChangesSummary(rebuild) {
      this.$projects.refreshChangesSummary({
        source: this.selectedBranchSource,
        target: this.selectedBranchTarget,
        rebuild
      })
      this.$projects.loadBranches()
    }
  }
}
</script>