<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView, DiffModeEnum, DiffParser } from "@git-diff-view/vue";
import PRBranchSelectoor from './PRBranchSelectoor.vue';
import CodeComment from "./CodeComment.vue";
import ChatEntry from "../ChatEntry.vue";
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
    <div class="flex gap-2 py-2 items-center" v-if="files?.length">
      <div class="flex gap-2 items-center border rounded-md px-1" 
        v-if="selectedFiles.length">
        <span>{{ selectedFiles.length }} selected</span>
        <div class="dropdown">
          <div tabindex="0" role="button" class="btn btn-xs m-1">
            <i class="fa-solid fa-bars"></i>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow-sm">
            <li @click="resetSelect"><a>Clear selection</a></li>
            <li @click="onBulkAction"><a>Bulk action</a></li>
          </ul>
        </div>
      </div>
      <div class="click btn btn-sm" @click.stop="toggleSelectAll" v-else>
        <i class="fa-regular fa-file-lines"></i>
      </div>
      <div class="grow">
        <div class="flex gap-2 items-center border rounded-md px-1">
          <input type="text" v-model="filter" class="grow input input-sm" />
          <i class="fa-solid fa-magnifying-glass"></i>
        </div>
      </div>
      <div class="badge badge-outline gap-2 badge-error tooltip" data-tip="Deleted">{{ deleteCount }} <i class="fa-regular fa-file-lines"></i></div>
      <div class="badge badge-outline gap-2 badge-success tooltip" data-tip="New">{{ newCount }} <i class="fa-regular fa-file-lines"></i></div>
      <div class="badge badge-outline gap-2 tooltip" data-tip="Changed">{{ changeCount }} <i class="fa-regular fa-file-lines"></i></div>
    </div>
    <div class="bg-base-100 border border-slate-600 rounded-md p-2 mb-2 relative"
       v-for="file, ix in visibleFiles" :key="ix"
       @dblclick="file.extended = !file.extended"
    >
      <div class="flex gap-2 text-xl py-2 items-center">
        <div class="flex flex-col gap-1">
          <div class="click flex gap-2 items-center truncate" :title="file.fileFullName" @click="openFile(file.fileFullName)">
            <span :class="file.selected && 'text-warning'"
              @click.stop="file.selected = !file.selected"
            >
              <i class="fa-regular fa-file-lines"></i>
            </span>
            <span :class="[file.isDeleted && 'text-error', file.isNewFile && 'text-success']">{{ file.fileShortName }}</span>
            <div class="avatar-group -space-x-6">
              <div class="avatar" :title="profile.name" v-for="profile in file.profiles" :key="profile.name">
                <div class="w-6">
                  <img :src="profile.avatar" />
                </div>
              </div>
            </div>
          </div>
          <div class="px-2 py-1 rounded-md text-xs w-fit" :class="`text-[${file.column.color}] border border-[${file.column.color}]`"  v-if="file.column">
            {{  file.column.title  }}
          </div> 
        </div>
        <div class="grow"></div>
        <div class="text-error text-xs" v-if="!file.parsed">
          --no diff available--
        </div>
        <button class="btn btn-sm" @click="toggleFileDiff(file)" 
          v-if="file.parsed">
          <i class="fa-solid fa-code-merge" :class="file.showDiff && 'text-warning'"></i>
        </button>

        <button class="btn btn-sm" 
          @click="copyDiff(file)" v-if="file.parsed">
          <i class="fa-regular fa-copy"></i>
        </button>

        <div class="indicator" v-if="prChats[file.fileFullName]"
          @click="onValidateChat(file)"
        >
          <span class="indicator-item indicator-start badge badge-secondary">
            {{ file.messageCount }}
          </span>
          <button class="btn"><i class="fa-regular fa-comment-dots"></i></button>
        </div>
        <button class="btn btn-sm tooltip" data-tip="Review changes" 
          :class="prChats[file.fileFullName] && 'border bg-sky-600'"
          @click="onValidateChat(file)" v-else>
          <i class="fa-solid fa-user-check"></i>
        </button>
      </div>
      <div class="flex flex-col gap-2">
        <div v-if="file.lastMessage && !file.showDiff">
          <ChatEntry class="max-h-60 overflow-auto mb-2"
            :message="file.lastMessage"
            :chat="file.chat"
            :menu-less="true"
          />
        </div>

        <DiffView
          :data="file"
          :diff-view-theme="'dark'" 
          :diff-view-add-widget="false"
          :extend-data="extendData"
          v-if="file.showDiff"
        >
          <template #widget="{ onClose, lineNumber, side }">
            <div class="absolute z-[100] top-0 left-0 right-0 bottom-0 bg-base-300">
              <div class="flex flex-col items-center justify-center w-full h-full">
                <CodeComment 
                  @close="onClose"
                  @save="onAddComment($event, file, lineNumber, side, onClose)"
                />
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
    <modal close="true" @close="showBulkAction = false" v-if="showBulkAction">
      <div class="flex flex-col gap-2">
        <div class="text-xl">Bulk action</div>
        <div>Send message to {{ selectedFiles.length }} files:</div>
        <textarea v-model="bulkAction" class="textarea textarea-bordered max-h-60 h-40" />
        <div class="flex justify-end">
          <button class="btn" @click="sendBulkAction">
            Send
          </button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
const parser = new DiffParser()
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
      codeComment: null,
      filter: null,
      bulkAction: null,
      showBulkAction: false
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
    selectedFiles() {
      return this.files?.filter(f => f.selected) || []
    },
    visibleFiles() {
      return this.filter ? this.files?.filter(f => f.fileFullName.includes(this.filter.toLowerCase())) || [] :
        this.files
    }
  },
  watch: {
    filter() {
      this.resetSelect()
    }
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
        let diff = changes.diff
        if (changes.local_changes) {
          Object.values(changes.local_changes)
            .filter(loacalDiff => !!loacalDiff)
            .forEach(loacalDiff => diff += `\n${loacalDiff}`)
        }
        this.files = diff.split("diff --git ")
          .filter(d => d)
          .map(diff => this.buildDiffFile(diff))   
          .filter(diff => !!diff)   
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
    onFileComment(file, message) {
      const { chat, fileFullName, fileShortName } = file
      const profiles = file.profiles
      const description = message || ["```diff", file.hunks[0], "```"].join("\n")
      this.$emit('comment', { chat, title: fileShortName, files: [fileFullName], description, profiles, mode: 'task' })
    },
    onValidateChat(file) {
      if (file.chat) {
        this.$projects.setActiveChat(file.chat)
      } else {
        this.onFileComment(file, "Review file changes, fix errors and suggest improvements.")
      }
    },
    copyDiff(file) {
      const diffBlock = ["```diff", file.hunks[0], "```"].join("\n") 
      this.$ui.copyTextToClipboard(diffBlock)
    },
    openFile(fileName) {
      this.$ui.openProjectFile(fileName)
    },
    getFileProfiles(fileName) {
      return this.$projects.profiles.filter(p => p.file_match && fileName.match(p.file_match))
    },
    buildDiffFile(diff) {
      try {
          const lines = diff.split("\n")
          const [oldFile, newFile] = lines[0].trim().split(" ")
          // const diff = lines.slice(2).join("\n")
          const oldName = oldFile.replace("a/", "")
          const newName = newFile.replace("b/", "")
          
          let parsed = null
          try {
            parsed = parser.parse(diff)
          } catch (parseEx) {
            console.error(`Error parsing diff\n*** ${parseEx}\n${diff}`) 
          }
          
          const isDeleted = parsed?.header.includes("deleted") || false
          const isNewFile =  !isDeleted && newName && !oldName
          const isChanged =  !isDeleted && newName && oldName
          const fileName = oldName || newName
          const profiles = this.getFileProfiles(fileName)
          const fileShortName = fileName.split('/').reverse().slice(0, 3).reverse().join('/') 
          const fileFullName = fileName.startsWith(this.$project.project_path) ? fileName :
            this.$project.project_path + (fileName[0] === "/" ? "": "/") + fileName
          const chat = this.prChats[fileFullName]
          const lastMessage = chat?.messages.filter(m => m.role === "assistant" && !m.hide)
                                  .reverse()[0]
          const board = this.$storex.projects.kanban.boards[chat?.board]          
          const column = board?.columns.find(c => c.title === chat?.column)
          const messageCount = chat?.messages.length

          return {
            diff,
            fileName,
            fileShortName,
            fileFullName,
            chat,
            lastMessage,
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
            profiles,
            column,
            messageCount
          }
      } catch (ex) {
        console.error(`Error parsing diff\n*** ${ex}\n${diff}`)
      }
      return null
    },
    toggleFileDiff(file) {      
      file.showDiff = !file.showDiff
    },
    toggleSelectAll() {
      const setSeelcted = !this.selectedFiles.length
      this.visibleFiles.map(f => { f.selected = setSeelcted })
    },
    resetSelect() {
      this.files.map(f => { f.selected = false })
    },
    onBulkAction() {
      this.bulkAction = null
      this.showBulkAction = true
    },
    sendBulkAction() {
      this.showBulkAction = false
      requestAnimationFrame(() => 
        this.selectedFiles.map(file => 
          this.onFileComment(file, this.bulkAction)
        )
      )
    }
  },
  mounted() {
    this.$projects.loadBranches()
  }
}
</script>