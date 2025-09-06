<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView, DiffModeEnum, DiffParser } from "@git-diff-view/vue";
import PRBranchSelectoor from './PRBranchSelectoor.vue';
</script>

<template>
  <div class="pr-view flex flex-col gap-1 h-full">
    <header class="flex justify-between items-start">
      <div class="flex flex-col gap-2">
        <div class="flex gap-2 items-center" v-if="loading">
          <span class="text-xs">Loading</span>
          <progress class="progress grow"></progress>
        </div>
        <div class="flex gap-2">
          <PRBranchSelectoor :fromBranch="fromBranchSelected" :toBranch="toBranchSelected" @select="onBranchChanged" />
          <button class="btn btn-xs" @click="refreshSummary">
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>
        </div>
      </div>
    </header>

    <div class="bg-base-100 border border-slate-600 rounded-md p-2 mb-2" v-for="file, ix in files" :key="ix">
      <div class="flex gap-2 text-xl py-2">
        <i class="fa-regular fa-file-lines"></i> {{ file.oldFile.fileName }}
        <div class="grow"></div>
        <button class="btn btn-sm" @click="$emit('comment', file)">
          <i class="fa-regular fa-comment-dots"></i>
        </button>
      </div>
      <DiffView
        :data="file"
        :diff-view-theme="'dark'" 
        :diff-view-add-widget="false"
        :extend-data="extendData"
      >
      <template #widget="{ onClose, lineNumber, side }">
        <div class="flex w-full flex-col border px-[4px] py-[8px]">
          <textarea class="min-h-[80px] w-full border p-[2px]"  />
          <div class="m-[5px] mt-[0.8em] text-right">
            <div class="inline-flex justify-end gap-x-[12px]">
              <button class="rounded-[4px] border px-[12px] py-[6px]" @click="onClose">cancel</button>
              <button
                class="rounded-[4px] border px-[12px] py-[6px]"
                @click="onAddComment(file, lineNumber, side, onClose)"
              >
                submit
              </button>
            </div>
          </div>
        </div>
      </template>
      <template #extend="{ data }">
        <div class="flex border bg-slate-400 px-[10px] py-[8px]">
          <h2 class="text-[20px]">>> {{ data }}</h2>
        </div>
      </template>
    </DiffView>
    </div>
  </div>
</template>

<script>
export default {

  props: ['fromBranch', 'toBranch', 'extendedData'],
  data() {
    return {
      overviewChecked: true,
      isInputVisible: false,
      loading: false,
      changesSummary: null,
      files: null,
      fromBranchSelected: this.fromBranch,
      toBranchSelected: this.toBranch,
      extendData: { oldFile: {}, newFile: {} }
    }
  },
  created() {
    if (this.fromBranch && this.toBranch) {
      this.refreshSummary()
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
          .map(file => {
            const lines = file.split("\n")
            const [oldFile, newFile] = lines[0].trim().split(" ")
            const diff = lines.slice(2).join("\n")
            return {
              oldFile: {
                fileName: oldFile.replace("a/", "")
              },
              newFile: {
                fileName: newFile.replace("b/", "")
              },
              hunks: [diff]
            }
          })      
      } finally {
        this.loading = false
      }
    },
    toggleBranchInput() {
      this.isInputVisible = !this.isInputVisible
    },
    onBranchChanged({ fromBranch, toBranch }) {
      this.$emit('select', { fromBranch, toBranch })
    },
    onAddComment(file, lineNumber, side, onClose) {
      const _side = side === 1 ? 'oldFile' : 'newFile';
      this.extendData[_side][lineNumber] = { data: "comment" };
      onClose()
    }
  },
  mounted() {
    this.$projects.loadBranches()
  }
}
</script>