<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffParser } from "@git-diff-view/vue";
import PRBranchSelectoor from './PRBranchSelectoor.vue';
import CodxMenu from "../CodxMenu.vue";
import PRFile from "./PRFile.vue";
</script>

<template>
  <div class="pr-view flex flex-col gap-1 h-full overflow-hidden">
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
        <span>{{ selectedFiles.length }} files</span>
        <div class="dropdown">
          <div tabindex="0" role="button" class="btn btn-xs m-1">
            <i class="fa-solid fa-bars"></i>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow-sm">
            <li @click="onReviewSelected"><a>Review files</a></li>
            <li @click="onBulkAction"><a>Custom action...</a></li>
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


    <div class="flex gap-2 h-full" v-if="files">
      <div class="w-3/12 shrink-0 h-full overflow-auto">
        <CodxMenu class="w-full overflow-auto"
          :items="visibleFiles"
          :item-key="'folder'"
          :defaultExpanded="defaultExpanded"
          @select="showFileDetails = $event"  
        >
          <template v-slot:header>
            <h2 class="font-semibold !text-base text-blackA11 flex items-center gap-2 px-2 pt-1">
              <input type="checkbox" @change="toggleAllNoneSelected" class="checkbox checkbox-sm"
              />
              Files
            </h2>
          </template>
          <template v-slot:item="data">
            <div class="flex gap-1 items-center click px-2 text-nowrap"
              :class="data.item.value === showFileDetails ? 'text-warning font-bold' : 'opacity-90'"
            >
              <input type="checkbox" v-model="data.item.value.selected" class="checkbox checkbox-sm"
                v-if="!data.item.hasChildren"
              />
              <div class="avatar-group -space-x-2" v-if="data.item.value.profiles?.length">
                <div class="avatar" :title="profile.name" v-for="profile in data.item.value.profiles" :key="profile.name">
                  <div class="w-4 h-4">
                    <img :src="profile.avatar" />
                  </div>
                </div>
              </div>
              <i class="fa-regular fa-comment-dots" 
                :class="`text-[${data.item.value.column.color}]`"
                v-if="data.item.value.chat"></i>
            
              {{ data.item.value.title }}

              <div class=""
              :class="`text-[${data.item.value.column.color}]`"
              v-if="data.item.value.column">
               ( {{ data.item.value.column.title }} )
              </div>
            </div>
          </template>
        </CodxMenu>
      </div>
      <PRFile :file="showFileDetails" 
        class="grow bg-base-200 p-2 border-l border-slate-500 h-full"
        @comment="onFileComment" 
        v-if="showFileDetails">
      </PRFile>
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
      showBulkAction: false,
      showFileDetails: null
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
      return this.filter ? this.files?.filter(f =>
        f.fileFullName.includes(this.filter.toLowerCase()) ||
        f.diff.toLowerCase().includes(this.filter.toLowerCase())
      ) || [] :
        this.files
    },
    defaultExpanded() {
      return [...new Set(this.visibleFiles.filter(i => i.chat).map(i => i.folder))]
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
        const repoPath = changes.repo_path
        if (changes.local_changes) {
          Object.values(changes.local_changes)
            .filter(loacalDiff => !!loacalDiff)
            .forEach(loacalDiff => diff += `\n${loacalDiff}`)
        }
        this.files = diff.split("diff --git ")
          .filter(d => d)
          .map(diff => this.buildDiffFile(diff, repoPath))   
          .filter(diff => !!diff)   

        this.showFileDetails = this.files.filter(f => f.chat)
                                        .sort((a, b) => a.chat.updated_at > b.chat.updated_at ? -1 : 1)[0]
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
    buildDiffFile(diff, repoPath) {
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
          const fileFullName = fileName.startsWith(repoPath) ? fileName :
                                  repoPath + (fileName[0] === "/" ? "": "/") + fileName
          const chat = this.prChats[fileFullName]
          const lastMessage = chat?.messages.filter(m => m.role === "assistant" && !m.hide)
                                  .reverse()[0]
          const board = this.$storex.projects.kanban.boards[chat?.board]          
          const column = board?.columns.find(c => c.title === chat?.column)
          const messageCount = chat?.messages.length
          const folder = "/" + fileName.split("/").reverse().slice(1).reverse().join("/")
          const title = fileName.split("/").reverse()[0]
          const extension = fileFullName.split(".").reverse()[0]
        
          return {
            title,
            folder,
            extension,
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
            messageCount,
            showDiff: true,
            showChat: false
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
      const files = [...this.selectedFiles]
      requestAnimationFrame(() => 
        files.map(file => 
          this.onFileComment({ file, message: this.bulkAction })
        )
      )
    },
    toggleAllNoneSelected() {
      const setVal = this.selectedFiles.length === 0
      this.visibleFiles.map(file => { file.selected = setVal })
    },
    onFileComment({ file, message }) {
      const { chat, fileFullName, fileShortName } = file
      const profiles = file.profiles
      const description = message || ["```diff", file.hunks[0], "```"].join("\n")
      this.$emit('comment', { chat, title: fileShortName, files: [fileFullName], description, profiles, mode: 'task' })
    },
    onReviewSelected() {
      const files = [...this.selectedFiles]
      files.map(file => 
        this.onFileComment({ file, message: "Review files and return a list of erros that need to be changed. Add examples for complex changes." })
      )
    }
  },
  mounted() {
    this.$projects.loadBranches()
  }
}
</script>