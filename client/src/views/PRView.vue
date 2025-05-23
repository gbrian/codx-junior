<script setup>
import GitDiffViewer from '@/components/code/GitDiffViewer.vue'
import Collapsible from '@/components/Collapsible.vue'
</script>

<template lang="pug">
  <div class="pr-view p-4 flex flex-col gap-4 h-full">
    <header class="flex justify-between items-start">
      <div class="flex flex-col gap-2">
        <h1 class="md:text-3xl text-xl font-bold">Changes review</h1>
        <div class="flex gap-2 items-center">
          <div class="flex items-center gap-2">
            <label class="block text-xs font-bold" for="branchSource">Source</label>
            <select id="branchSource" class="select select-bordered select-sm w-full max-w-xs" v-model="selectedBranchSource">
              <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label class="block text-xs font-bold" for="branchTarget">Target</label>
            <div class="flex gap-1 input input-sm input-bordered items-center">
              <button @click="toggleBranchInput" class="btn btn-xs">
                <i class="fa-solid" :class="isInputVisible ? 'fa-list' : 'fa-pen'"></i>
              </button>
              select(
                v-if="!isInputVisible"
                id="branchTarget"
                class="selectselect-sm w-full max-w-xs"
                v-model="selectedBranchTarget"
              )
                <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
              input(
                v-else
                id="branchTargetInput"
                type="text"
                class="input input-sm w-full max-w-xs"
                v-model="selectedBranchTarget"
              )
            </div>
          </div>
        </div>
      </div>
    </header>
    .flex.flex-col.gap-4.grow.overflow-auto

      Collapsible.hidden(v-model="overviewChecked" :start-expanded="true")
        template(v-slot:title)
          .flex.flex-col.grow
            .flex.justify-between.items-center
              | Overview
              button.btn.btn-sm.tooltip(data-tip="Rebuild summary" 
                                        @click="refreshSummary(true)")
                <i class="fa-solid fa-arrows-rotate"></i> Rebuild
            .text-sm Changes overview
        template(v-slot:content)
          Markdown(:text="$projects.changesSummary")

      Collapsible.hidden
        template(v-slot:title)
          .flex.flex-col.grow
            | Tasks
            .text-sm Tasks associated with {{ selectedBranchSource }}
        template(v-slot:content)
          

      GitDiffViewer(:diff="$projects.project_branches.git_diff" v-if="$projects.project_branches.git_diff")
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedBranchSource: null,
      selectedBranchTarget: null,
      activeTab: 'Overview',
      overviewChecked: true,
      isInputVisible: false 
    }
  },
  computed: {
    branches() {
      return this.$projects.project_branches.branches
    }
  },
  watch: {
    $project() {
      this.refreshSummary()
    },
    selectedBranchSource() {
      this.refreshSummary()
    },
    selectedBranchTarget() {
      this.refreshSummary()
    }
  },
  methods: {
    switchTab(tab) {
      this.activeTab = tab
    },
    copyText() {
      copyTextToClipboard(this.changesSummary)
    },
    async refreshSummary(rebuild = false) {
      this.$projects.refreshChangesSummary({
        source: this.selectedBranchSource,
        target: this.selectedBranchTarget,
        rebuild
      })
      await this.$projects.loadBranches()
      this.selectedBranchSource = this.$projects.currentBranch
      this.selectedBranchTarget = this.$projects.project_branches.parent_branch
    },
    toggleBranchInput() {
      this.isInputVisible = !this.isInputVisible
    }
  },
  mounted() {
    this.refreshSummary(false)
  }
}
</script>