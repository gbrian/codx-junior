<script setup>
import "@git-diff-view/vue/styles/diff-view.css"
import { DiffParser } from "@git-diff-view/vue"
import PRBranchSelectoor from './PRBranchSelectoor.vue'
import CodxMenu from "../CodxMenu.vue"
import PRReport from "./PRReport.vue"
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import PRFileViewModeSelector from "./PRFileViewModeSelector.vue"
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
          <PRBranchSelectoor :fromBranch="fromBranchSelected" :toBranch="toBranchSelected" @select="onBranchChanged" :branches="repoBranches?.branches" />
          <button class="btn btn-xs" @click="refreshSummary">
            <i class="fa-solid fa-arrows-rotate"></i>
          </button>
          <div class="grow"></div>
          <PRFileViewModeSelector @select="onSelectFileOption" />
        </div>
      </div>
    </header>
    <div class="flex gap-2 py-2 items-center" v-if="files?.length">
      <div class="flex gap-2 items-center" v-if="reportFiles.length">
        <div class="dropdown">
          <div tabindex="0" role="button" class="btn btn-sm m-1 indicator">
            <span class="indicator-item badge badge-xs badge-warning" v-if="selectedFiles.length">
              {{ selectedFiles.length }}
            </span>
            <i class="fa-solid fa-bars"></i>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow-sm">
            <li @click="onReviewSelected" v-if="selectedFiles.length"><a>Review files</a></li>
            <li @click="onBulkAction" v-if="selectedFiles.length"><a>Custom action...</a></li>
            <li @click="setFilesColumn" v-if="selectedFiles.length"><a>
              <select @click.stop="" class="select select-xs select-bordered" v-model="chatColumn">
                <option v-for="column, ix in columns" :value="column.title" :key="column.title + ix">
                  {{ column.title }}
                </option>
              </select>
              <button class="btn btn-xs">Set</button>
            </a></li>
          </ul>
        </div>
      </div>
      <div class="click btn btn-sm" @click.stop="toggleSelectAll" v-else>
        <i class="fa-regular fa-file-lines"></i>
      </div>
      <div class="grow">
        <div class="flex gap-2 items-center border rounded-md px-1">
          <span class="click" v-if="filter" @click="filter = ''"><i class="fa-solid fa-circle-xmark"></i></span>
          <input type="text" v-model="filter" class="grow input input-sm" />
          <div class="click flex gap-1 items-center px-1">
            <i class="fa-solid fa-magnifying-glass"></i>
          </div>
        </div>
      </div>
      <div class="avatar click" :title="profile.name" @click="filter = (filter||'') + ' profile:' + profile.name"
        v-for="profile in profiles" :key="profile.name">
        <div class="w-4 h-4 ring ring-offset-1 rounded-full">
          <img :src="profile.avatar" />
        </div>
      </div>
      <div class="click px-2 py-1 border rounded-full flex gap-2 tooltip text-xs" v-for="column in columns"
        :key="column.title" :class="`text-[${column.color}] border-[${column.color}]`"
        @click="filter = (filter||'') + ' column:' + column.title">
        {{ column.title }}
        {{ column.chats?.length }}
      </div>
      <div class="click px-2 py-1 border border-error text-error items-center rounded-full flex gap-2 tooltip text-xs"
        @click="filter = (filter||'') + ' hasNo:column'"
      >
        <i class="fa-solid fa-circle-exclamation"></i>
        {{ files?.filter(f => !f.column).length }}
      </div>
    </div>

    <SplitterGroup class="grow overflow-auto" id="splitter-group-1" direction="horizontal" v-if="files">
      <SplitterPanel id="splitter-group-1-panel-1" :min-size="10" :defaultSize="30" :collapsible="true" class="" :order="0">
        <CodxMenu class="h-full overflow-auto"
          :items="visibleFiles" :item-key="'folder'" 
          :defaultExpanded="defaultExpanded"
        >
          <template v-slot:header>
            <h2 class="font-semibold !text-base text-blackA11 flex items-end gap-2 px-2 pt-1">
              <input type="checkbox" @change="toggleAllNoneSelected" class="checkbox checkbox-sm" />
              Files
              <span class="click ml-2 text-xs flex gap-1"><a @click="selectAll">all</a>/<a @click="selectNone">none</a></span>
            </h2>
          </template>
          <template v-slot:item="data">
            <div class="flex gap-1 items-center click px-2 text-nowrap"
              :class="!data.item.hasChildren && 'ml-6'"
              @click="onDataItemClick(data.item)"
            >
              <input type="checkbox" v-model="data.item.value.selected" class="checkbox checkbox-sm" 
                @click.stop=""
                @change="onDataItemSelected(data.item)" />
              <div class="avatar-group -space-x-2" v-if="data.item.value.profiles?.length">
                <div class="avatar" :title="profile.name" v-for="profile in data.item.value.profiles" :key="data.item.value.title + profile.name">
                  <div class="w-4 h-4">
                    <img :src="profile.avatar" />
                  </div>
                </div>
              </div>
              <i class="fa-regular fa-comment-dots" :class="`text-[${data.item.value.column?.color}]`"
                v-if="data.item.value.chat"></i>

              <span :title="data.item.value.fileName">
                {{ data.item.value.title }}
              </span>

              <div class="" :class="`text-[${data.item.value.column.color}]`" v-if="data.item.value.column">
                ( {{ data.item.value.column.title }} )
              </div>
            </div>
          </template>
        </CodxMenu>
      </SplitterPanel>
      <SplitterResizeHandle id="splitter-group-1-resize-handle-1" class="w-1 hover:bg-slate-600" />
      <SplitterPanel class="w-full h-full overflow-auto" id="splitter-group-1-panel-2" :min-size="20" :defaultSize="70" :order="1">
        <PRReport  
          ref="prReport"
          :files="visibleFiles"
          :columns="columns"
          @new-chat="onFileChat"
          @chat-column="onSetChatColumn"  
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
  props: ['fromBranch', 'toBranch', 'chat'],
  data() {
    return {
      repoChanges: null,
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
      showOption: 'diff',
      chatColumn: null,
      projectContext: null,
      repoBranches: {}     
    }
  },
  created() {
    if (this.fromBranch && this.toBranch) {
      this.refreshSummary()
    }
    this.setProjectContext()
  },
  computed: {
    childrenChats() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => a.child_index > b.child_index ? 1 : -1)
    },
    prChats() {
      return this.childrenChats.filter(c => c.file_list?.length === 1)
            .sort((a, b) => a.updated_at > b.updated_at ? 1 : -1)
            .reduce((acc, c) => ({ ...acc, [c.file_list[0]]: c }), {})
    },
    reportFiles() {
      return this.selectedFiles?.length ?
        this.selectedFiles : this.visibleFiles
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
        const fields = [
          fileFullName.toLowerCase(),
          diff?.toLowerCase()
        ]
        return fields.join("").toLowerCase()
      }
      const keyMatcher = /(\w+):!?[^\s]+/g
      const filterKeys = this.filter?.match(keyMatcher) || []
      const textFilter = this.filter?.replace(keyMatcher, '').trim().toLowerCase() || ''

      const matchByKey = f => !filterKeys.length || filterKeys.find(key => {
        let [k, v] = key.split(':')
        const negate = v?.startsWith('!')
        const comparator = (a,b) => negate ? a !== b : a === b
        const includes = (a,b) => negate ? !a.includes(b) : a.includes(b)
        
        if (negate) {
          v = v.slice(1)
        }
        if (k === 'column') {
          return comparator(f.column?.title.toLowerCase(), v.toLowerCase())
        }
        if (k === 'profile') {
          return comparator(f.profiles.some(p => p.name.toLowerCase(), v.toLowerCase()))
        }
        if (k === 'file') {
          return includes(f.title.toLowerCase(), v.toLowerCase())
        }
        if (k === 'path') {
          return includes(f.fileFullName.toLowerCase(), v.toLowerCase())
        }
        if (k === 'hasNo') {
          const value = f[v]
          return !value || value.length === 0
        }
        if (k === 'has') {
          const value = f[v]
          if (value && value["length"] !== undefined) {
            return value.length !== 0
          }
          return value
        }
        return false
      })

      return this.files?.filter(f => {
        const index = fileIndex(f)
        return matchByKey(f) && index.includes(textFilter)
      }) || []
    },
    defaultExpanded() {
      return [...new Set(this.visibleFiles.map(i => i.folder))]
    },
    fileMap() {
      return this.files.reduce((acc, file) => ({ ...acc, [file.fileName]: file }), {})
    },
    columns() {
      return this.$projects.kanban.boards[this.chat.board].columns
        .reduce((acc, col) => ({
          ...acc,
          [col.title]: {
            ...col,
            chats: this.files.filter(f => f.column?.title === col.title)
          }
        }), {})
    },
    profiles() {
      return this.files?.map(f => f.profiles)
        .reduce((a, b) => [...a, ...b])
        .reduce((acc, profile) => ({ ...acc, [profile.name]: profile }), {})
    },
    $api() {
      const { $api } = this.chat.project_id ? this.$projects.allProjectsById[this.chat.project_id] : this.$project
      return $api
    }
  },
  watch: {
    chat() {
      this.setProjectContext()
    },
    filter() {
      this.resetSelect()
    },
    prChats() {
      this.buildFiles()
    }
  },
  methods: {
    async setProjectContext() {
      this.repoBranches = await this.$api.repo.branches() 
    },
    copyText() {
      copyTextToClipboard(this.changesSummary)
    },
    async refreshSummary() {
      this.loading = true
      try {
        const { fromBranch, toBranch } = this
        this.repoChanges = await this.$api.repo.changes({ from_branch: fromBranch, to_branch: toBranch })        
        this.buildFiles()  
      } finally {
        this.loading = false
      }
    },
    buildFiles() {
      if (!this.repoChanges) {
        this.files = null
        return
      }
      const { branch_file_and_commits } = this.repoChanges 
      const repoPath = this.repoChanges.repo_path
      
      const files = Object.keys(branch_file_and_commits)
                      .map(file_path => {
                        const diff = branch_file_and_commits[file_path].diff
                        return this.buildDiffFile(diff, repoPath)
                      })
                      .filter(diff => !!diff)
                      .sort((a, b) => a.title < b.title ? 1 : -1)
                      .reduce((acc, f) => ({ ...acc, [f.fileFullName]: f }), {}) 
      this.files = Object.values(files)

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

      const _side = side === 1 ? 'oldFile' : 'newFile'
      this.extendData[_side][lineNumber] = { data: "comment" }
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
        const lines = diff.replace("diff --git ", "").split("\n")
        const [oldFile, newFile] = lines[0].trim().split(" ")
        const oldName = oldFile.replace("a/", "")
        const newName = newFile.replace("b/", "")

        let parsed = null
        try {
          parsed = parser.parse(diff)
        } catch (parseEx) {
          console.error(`Error parsing diff\n*** ${parseEx}\n${diff}`)
        }

        const isDeleted = parsed?.header.includes("deleted") || false
        const isNewFile = !isDeleted && newName && !oldName
        const isChanged = !isDeleted && newName && oldName
        const fileName = oldName || newName
        const profiles = this.getFileProfiles(fileName)
        const fileShortName = fileName.split('/').reverse().slice(0, 3).reverse().join('/')
        const fileFullName = fileName.startsWith(repoPath) ? fileName :
          repoPath + (fileName[0] === "/" ? "" : "/") + fileName

        const getChat = () => {
          return this.prChats[fileFullName]
        }
        const chat = getChat()
        const lastMessage = chat?.messages.filter(m => m.role === "assistant" && !m.hide)
          .reverse()[0]
        
        let folderParts = fileName.split("/").reverse().slice(1).reverse()
        if (folderParts.length > 6) {
          folderParts = folderParts.map((v, ix) => ix <= 4 ? v[0] : v)
        }
        const folder = "/" + folderParts.join("/")

        const title = fileName.split("/").reverse()[0]
        const extension = fileFullName.split(".").reverse()[0]

        return {
          ...this.files?.find(f => f.fileFullName === fileFullName) || {},
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
          showDiff: true,
          showChat: false,
          ...this.getChatInfo(chat)
        }
      } catch (ex) {
        console.error(`Error parsing diff\n*** ${ex}\n${diff}`)
      }
      return null
    },
    getChatInfo(chat) {
      if (!chat) {
        return {}
      }
      const board = this.$storex.projects.kanban.boards[chat?.board]
      const column = board?.columns.find(c => c.title === chat?.column)
      const messageCount = chat?.messages.length
      return {
        board,
        column,
        messageCount
      }
    },
    toggleFileDiff(file) {
      file.showDiff = !file.showDiff
    },
    toggleSelectAll() {
      const setSelected = !this.selectedFiles.length
      this.visibleFiles.map(f => { f.selected = setSelected })
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
        this.onFileComment({
          file,
          message: "Review files and return a list of errors that need to be changed. Add examples for complex changes."
        })
      )
    },
    onFileChat({ file, column, message: description, metadata }) {
      column = column || this.chat.column
      const { fileFullName, fileShortName, profiles } = file
      this.$emit('new-chat', { title: fileShortName, description, files: [fileFullName], profiles, mode: 'task', column, metadata })
    },
    onDataItemSelected(item) {
      if (item.hasChildren) {
        item.value.children.forEach(child => {
          child.selected = item.value.selected
        })
      }
    },
    onDataItemClick(item) {
      if (!item.hasChildren) {
        this.$refs.prReport.scrollToFile(item.value.fileFullName)
      }
    },
    selectAll() {
      this.visibleFiles.map(f => { f.selected = true })
    },
    selectNone() {
      this.files.map(f => { f.selected = false })
    },
    onSelectFileOption(showOption) {
      this.showOption = showOption
    },
    async createFilesChat(files, column) {
      files.forEach(file => this.onFileChat({ file, column }))
      return new Promise(ok => setTimeout(ok, 2000))
    },
    async setFilesColumn() {
      const { chatColumn: column } = this
      if (!column) {
        return
      }
      const filesMissingChat = this.selectedFiles.filter(f => !f.chat) 
      if (filesMissingChat.length) {
        await this.createFilesChat(filesMissingChat, column)
      }
      const chats = this.selectedFiles.map(f => f.chat)
      this.$emit('change-column', { chats, column })
    },
    async onSetChatColumn({ file, column }) {
      if (!file.chat) {
        await this.createFilesChat([file], column)
      }
      const chats = [this.files.find(f => f.file === f.file).chat]
      this.$emit('change-column', { chats, column })
    }
  }
}
</script>