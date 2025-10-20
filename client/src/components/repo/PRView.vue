<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffParser } from "@git-diff-view/vue";
import PRBranchSelectoor from './PRBranchSelectoor.vue';
import CodxMenu from "../CodxMenu.vue";
import PRReport from "./PRReport.vue";
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import PRFileViewModeSelector from "./PRFileViewModeSelector.vue";
</script>

<template>
  <div class="pr-view flex flex-col gap-1 h-full overflow-hidden">
    <header class="flex justify-between items-start">
      <div class="flex flex-col gap-2 w-full">
        <div class="flex gap-2 items-center" v-if="loading">
          <span class="text-xs">Loading</span>
          <progress class="progress grow"></progress>
        </div>
        <div class="flex gap-2">
          <PRBranchSelectoor :fromBranch="fromBranchSelected" :toBranch="toBranchSelected" @select="onBranchChanged" />
          <button class="btn btn-xs" @click="refreshSummary">
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>
          <div class="grow"></div>
          <PRFileViewModeSelector @select="onSelectFileOption" />
        </div>
      </div>
    </header>
    <div class="flex gap-2 py-2 items-center" v-if="files?.length">
      <div class="flex gap-2 items-center" 
        v-if="reportFiles.length">
        <div class="dropdown">
          <div tabindex="0" role="button" class="btn btn-sm m-1 indicator"
            :disabled="selectedFiles.length === 0"
          >
              <span class="indicator-item badge badge-xs badge-warning" v-if="selectedFiles.length">
                {{ selectedFiles.length }}
              </span>
            <i class="fa-solid fa-bars"></i>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow-sm">
            <li @click="onReviewSelected"
              v-if="selectedFiles.length"><a>Review files</a></li>
            <li @click="onBulkAction"
              v-if="selectedFiles.length"><a>Custom action...</a></li>
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
      <div class="avatar click" :title="profile.name" 
        @click="filter = (filter||'') + ' ' + profile.name"
        v-for="profile in profiles" :key="profile.name">
        <div class="w-4 h-4 ring ring-offset-1 rounded-full">
          <img :src="profile.avatar" />
        </div>
      </div>
      <div class="click px-2 py-1 border rounded-full flex gap-2 tooltip text-xs" 
        v-for="column in columns" :key="column.title"
        :class="`text-[${column.color}] border-[${column.color}]`"
        @click="filter = (filter||'') + ' ' + column.title"
        >
        {{  column.title }}
        {{ column.chats?.length }}
      </div>
    </div>

    <SplitterGroup class="h-full"
      id="splitter-group-1"
      direction="horizontal"
      v-if="files"
    >
      <SplitterPanel
        id="splitter-group-1-panel-1"
        :min-size="10"
        :collapsible="true"
        class=""
        :order="0"
      >
        <CodxMenu class="h-full overflow-auto"
          :items="visibleFiles"
          :item-key="'folder'"
          :defaultExpanded="defaultExpanded"
          @select="showFileDetails = $event"
        >
          <template v-slot:header>
            <h2 class="font-semibold !text-base text-blackA11 flex items-end gap-2 px-2 pt-1">
              <input type="checkbox" @change="toggleAllNoneSelected" class="checkbox checkbox-sm"
              />
              Files
              <span class="click ml-2 text-xs flex gap-1"><a @click="selectAll">all</a>/<a @click="selectNone">none</a></span>
            </h2>
          </template>
          <template v-slot:item="data">
            <div class="flex gap-1 items-center click px-2 text-nowrap"
              :class="data.item.value === showFileDetails ? 'text-warning font-bold' : 'opacity-90'"
            >
              <input type="checkbox" v-model="data.item.value.selected"
                class="checkbox checkbox-sm"
                @click.stop=""
                @change="onDataItemSelected(data.item)"  
              />
              <div class="avatar-group -space-x-2" v-if="data.item.value.profiles?.length">
                <div class="avatar" :title="profile.name" v-for="profile in data.item.value.profiles" :key="profile.name">
                  <div class="w-4 h-4">
                    <img :src="profile.avatar" />
                  </div>
                </div>
              </div>
              <i class="fa-regular fa-comment-dots" 
                :class="`text-[${data.item.value.column?.color}]`"
                v-if="data.item.value.chat"></i>
            
              <span :title="data.item.value.fileName">
                {{ data.item.value.title }}
              </span>

              <div class=""
              :class="`text-[${data.item.value.column.color}]`"
              v-if="data.item.value.column">
               ( {{ data.item.value.column.title }} )
              </div>
            </div>
          </template>
        </CodxMenu>
      </SplitterPanel>
      <SplitterResizeHandle
        id="splitter-group-1-resize-handle-1"
        class="w-1 hover:bg-slate-600"
      />
      <SplitterPanel
        id="splitter-group-1-panel-2"
        :min-size="20"
        :defaultSize="80"
        :order="1"
        class=""
      >
        <PRReport class="w-full h-full overflow-auto" 
          :files="reportFiles" 
          :showOption="showOption"
          @new-chat="onFileChat"
        />  
      </SplitterPanel>
    </SplitterGroup>

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
      showFileDetails: null,
      showOption: null
    }
  },
  created() {
    if (this.fromBranch && this.toBranch) {
      this.refreshSummary()
    }
  },
  computed: {
    reportFiles() {
      return [this.showFileDetails, ...this.selectedFiles]
        .filter((v, ix, arr) => v && arr.indexOf(v) === ix)
    },
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
      const fileIndex = ({ fileFullName, diff, chat }) => {
        const fileds = [
          fileFullName.toLowerCase(),
          diff?.toLowerCase(),
          chat?.profiles.map(p => p.name).join(),
          chat?.column
        ]
        return fileds.join("").toLowerCase()
      }
      return this.filter ? this.files?.filter(f =>
      fileIndex(f).includes(this.filter.trim().toLowerCase())) || [] :
        this.files
    },
    defaultExpanded() {
      return [...new Set(this.visibleFiles.filter(i => i.chat).map(i => i.folder))]
    },
    fileMap() {
      return this.files.reduce((acc, file) => ({ ...acc, [file.fileName]: file }), {})
    },
    columns() {
      return this.$projects.kanban.boards[this.chat.board].columns
    },
    profiles() {
      return this.files?.map(f => f.profiles)
              .reduce((a, b) => [...a, ...b])
              .reduce((acc, profile) => ({ ...acc, [profile.name]: profile }), {})
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
          
          let folderParts = fileName.split("/").reverse().slice(1).reverse()
          if (folderParts.length > 6) {
            folderParts = folderParts.map((v, ix) => ix <= 4 ? v[0] : v)
          }
          const folder = "/" + folderParts.join("/")

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
    },
    onFileChat({ file }) {
      const { fileFullName, fileShortName, profiles } = file
      this.$emit('new-chat', { title: fileShortName, files: [fileFullName], profiles, mode: 'task' })
    },
    onDataItemSelected(item) {
      if (item.hasChildren) {
        item.value.children.forEach(child => {
          child.selected = item.value.selected
        })
      }
    },
    selectAll() {
      this.files = this.files.map(f => ({...f, selected: true }))
    },
    selectNone() {
      this.files = this.files.map(f => ({...f, selected: false }))
    },
    onSelectFileOption(showOption) {
      this.showOption = showOption
    }
  },
  mounted() {
    this.$projects.loadBranches()
  }
}
</script>