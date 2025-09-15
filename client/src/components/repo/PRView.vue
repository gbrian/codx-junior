<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView, DiffModeEnum, DiffParser } from "@git-diff-view/vue";
import PRBranchSelectoor from './PRBranchSelectoor.vue';
import CodeComment from "./CodeComment.vue";
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
    <div class="flex justify-end gap-2 py-2" v-if="files?.length">
      <div class="badge badge-outline gap-2 badge-error">{{ deleteCount }} <i class="fa-regular fa-file-lines"></i></div>
      <div class="badge badge-outline gap-2 badge-success">{{ newCount }} <i class="fa-regular fa-file-lines"></i></div>
      <div class="badge badge-outline gap-2">{{ changeCount }} <i class="fa-regular fa-file-lines"></i></div>
    </div>
    <div class="bg-base-100 border border-slate-600 rounded-md p-2 mb-2"
       v-for="file, ix in files" :key="ix"
       @dblclick="file.extended = !file.extended"
    >
      <div class="flex gap-2 text-xl py-2">
        <span class="click flex gap-2 items-center" @click="openFile(file.fileName)">
          <i class="fa-regular fa-file-lines"></i>
          <span :class="[file.isDeleted && 'text-error', file.isNewFile && 'text-success']">{{ file.oldFile.fileName }}</span>
        </span> 
        <div class="grow"></div>
        <button class="btn btn-sm" @click="file.extended = !file.extended">
          <i class="fa-solid fa-caret-up" v-if="file.extended"></i>
          <i class="fa-solid fa-caret-down" v-else></i>
        </button>
        <button class="btn btn-sm" 
          @click="copyDiff(file)">
          <i class="fa-regular fa-copy"></i>
        </button>
        <button class="btn btn-sm" 
          :class="prChats[file.fileName] && 'btn-info'"
          @click="onFileComment(file)">
          <i class="fa-regular fa-comment-dots"></i>
        </button>
      </div>
      <DiffView
        :data="file"
        :diff-view-theme="'dark'" 
        :diff-view-add-widget="true"
        :extend-data="extendData"
        v-if="file.extended"
      >
      <template #widget="{ onClose, lineNumber, side }">
        <CodeComment @save="onAddComment($event, file, lineNumber, side, onClose)" />
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

  props: ['fromBranch', 'toBranch', 'extendedData', 'chat', 'prChats'],
  data() {
    return {
      overviewChecked: true,
      isInputVisible: false,
      loading: false,
      changesSummary: null,
      files: null,
      fromBranchSelected: this.fromBranch,
      toBranchSelected: this.toBranch,
      extendData: { oldFile: {}, newFile: {} },
      codeComment: null
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
    },
    newCount() {
      return this.files.filter(f => f.isNewFile).length
    },
    deleteCount() {
      return this.files.filter(f => f.isDeleted).length
    },
    changeCount() {
      return this.files.filter(f => f.isChanged).length
    },
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
        const { fromBranch, toBranch } = this
        const changes = await this.$storex.api.repo.changes({ from_branch: fromBranch, to_branch: toBranch })
        const parser = new DiffParser()
        this.files = changes.diff.split("diff --git ")
          .filter(d => d)
          .map(diff => {
            const lines = diff.split("\n")
            const [oldFile, newFile] = lines[0].trim().split(" ")
            // const diff = lines.slice(2).join("\n")
            const oldName = oldFile.replace("a/", "")
            const newName = newFile.replace("b/", "")
            const parsed = parser.parse(diff)
            const isDeleted = parsed.header.includes("deleted")
            const isNewFile =  parsed.hunks.length === 1 && !isDeleted
            const isChanged =  parsed.hunks.length === 2

            return {
              fileName: oldName || newName,
              oldFile: {
                fileName: oldName
              },
              newFile: {
                fileName: newName
              },
              hunks: [diff],
              isDeleted,
              isNewFile,
              isChanged,
              parsed,
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
    onAddComment(comment, file, lineNumber, side, onClose) {
      const metadata = {
        file: file.fileName,
        lineNumber,
        side
      }
      const message = {
        metadata,
        content: comment
      }
      
      const _side = side === 1 ? 'oldFile' : 'newFile';
      this.extendData[_side][lineNumber] = { data: "comment" };
      onClose()
    },
    onFileComment(file) {
      const fileName = file.fileName
      const chat = this.prChats[fileName]
      if (chat) {
        this.$projects.setActiveChat(chat)
      } else {
        const description = ["```diff", file.hunks[0], "```"].join("\n")
        this.$emit('comment', { fileName, description })
      }
    },
    copyDiff(file) {
      const diffBlock = ["```diff", file.hunks[0], "```"].join("\n") 
      this.$ui.copyTextToClipboard(diffBlock)
    },
    openFile(fileName) {
      this.$ui.openProjectFile(fileName)
    }
  },
  mounted() {
    this.$projects.loadBranches()
  }
}
</script>