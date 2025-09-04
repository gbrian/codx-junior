<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView, DiffModeEnum, DiffParser } from "@git-diff-view/vue";
import PRBranchSelectoor from './PRBranchSelectoor.vue';
</script>

<template>
  <div class="pr-view p-4 flex flex-col gap-4 h-full">
    <header class="flex justify-between items-start">
      <div class="flex flex-col gap-2">
        <div class="flex gap-2 items-center" v-if="loading">
          <span class="text-xs">Loading</span>
          <progress class="progress grow"></progress>
        </div>
        <div class="flex gap-2">
          <PRBranchSelectoor :fromBranch="fromBranch" :toBranch="toBranch" />
          <button class="btn btn-xs" @click="refreshSummary">
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>
        </div>
      </div>
    </header>

    <div>
      Hunkns {{ hunks?.length }}
      <div v-for="hunks, ix in files" :key="ix">
        <DiffView class="h-96 w-96" :data="{ hunks }" :diff-view-theme="'dark'" />
      </div>  
    </div>
  </div>
</template>

<script>
export default {
  props: ['fromBranch', 'toBranch'],
  data() {
    return {
      overviewChecked: true,
      isInputVisible: false,
      loading: false,
      changesSummary: null,
      files: {},
      hunks: []
    }
  },
  computed: {
    branches() {
      return this.$projects.project_branches.branches
    }
  },
  watch: {
  },
  methods: {
    copyText() {
      copyTextToClipboard(this.changesSummary)
    },
    async refreshSummary() {
      this.loading = true
      try {
        const { fromBranch: from_branch, toBranch: to_branch } = this
        const changes = await this.$storex.api.repo.changes({ from_branch, to_branch })
        this.files = changes.diff.split("diff --git")
          .filter(d => d)
          .map(d => "diff --git" + d)
        const parser = new DiffParser()
        this.hunks = this.files.map(diff => parser.parse(diff))
        this.changesSummary = [
          "```diff",
          changes.diff,
          "```"
        ].join("\n")
      } finally {
        this.loading = false
      }
    },
    toggleBranchInput() {
      this.isInputVisible = !this.isInputVisible
    }
  },
  mounted() {
    this.$projects.loadBranches()
  }
}
</script>