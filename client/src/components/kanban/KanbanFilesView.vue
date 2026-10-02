<script setup>
import KanbanTreeNode from './KanbanTreeNode.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 overflow-auto p-2">
    <!-- Header stats -->
    <div class="flex gap-2 items-center flex-wrap">
      <div class="stat bg-base-200 rounded-box p-3 flex-1 min-w-[120px]">
        <div class="stat-title text-xs">Total Files</div>
        <div class="stat-value text-lg">{{ allFiles.length }}</div>
      </div>
      <div class="stat bg-base-200 rounded-box p-3 flex-1 min-w-[120px]">
        <div class="stat-title text-xs">Tasks with Files</div>
        <div class="stat-value text-lg">{{ tasksWithFiles.length }}</div>
      </div>
      <div class="stat bg-base-200 rounded-box p-3 flex-1 min-w-[120px]">
        <div class="stat-title text-xs">Unique Files</div>
        <div class="stat-value text-lg">{{ uniqueFiles.length }}</div>
      </div>
      <div class="stat bg-base-200 rounded-box p-3 flex-1 min-w-[120px]">
        <div class="stat-title text-xs">Boards</div>
        <div class="stat-value text-lg">{{ allBoardIds.length }}</div>
      </div>
      <div class="grow"></div>

      <!-- Create chat from selection button -->
      <button
        v-if="selectedFiles.length"
        class="btn btn-sm btn-primary gap-2"
        :disabled="creatingChat"
        @click="openCreateChatModal"
      >
        <span v-if="creatingChat" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-comment-medical"></i>
        New chat ({{ selectedFiles.length }} files)
      </button>

      <!-- Filter input -->
      <div class="input input-sm input-bordered flex items-center gap-2 w-64">
        <i class="fa-solid fa-filter opacity-60"></i>
        <input
          type="text"
          v-model="fileFilter"
          placeholder="Filter files..."
          class="grow bg-transparent outline-none text-sm"
        />
        <span v-if="fileFilter" class="cursor-pointer" @click="fileFilter = ''">
          <i class="fa-regular fa-circle-xmark"></i>
        </span>
      </div>

      <!-- Group toggle -->
      <div class="join">
        <button
          class="btn btn-sm join-item"
          :class="groupBy === 'file' ? 'btn-active' : ''"
          @click="groupBy = 'file'"
        >
          <i class="fa-solid fa-file"></i> By File
        </button>
        <button
          class="btn btn-sm join-item"
          :class="groupBy === 'task' ? 'btn-active' : ''"
          @click="groupBy = 'task'"
        >
          <i class="fa-solid fa-list-check"></i> By Task
        </button>
        <button
          class="btn btn-sm join-item"
          :class="groupBy === 'column' ? 'btn-active' : ''"
          @click="groupBy = 'column'"
        >
          <i class="fa-solid fa-table-columns"></i> By Column
        </button>
        <button
          class="btn btn-sm join-item"
          :class="groupBy === 'tree' ? 'btn-active' : ''"
          @click="groupBy = 'tree'"
        >
          <i class="fa-solid fa-folder-tree"></i> Tree
        </button>
      </div>

      <!-- List/Tree view toggle (only in tree mode) -->
      <div v-if="groupBy === 'tree'" class="join">
        <button
          class="btn btn-xs join-item"
          :class="treeViewMode === 'tree' ? 'btn-active' : ''"
          @click="treeViewMode = 'tree'"
          title="Tree view"
        >
          <i class="fa-solid fa-sitemap"></i>
        </button>
        <button
          class="btn btn-xs join-item"
          :class="treeViewMode === 'list' ? 'btn-active' : ''"
          @click="treeViewMode = 'list'"
          title="List view"
        >
          <i class="fa-solid fa-list"></i>
        </button>
      </div>

      <!-- Include child boards toggle -->
      <div class="form-control">
        <label class="label cursor-pointer gap-2">
          <span class="label-text text-xs">Child boards</span>
          <input
            type="checkbox"
            class="toggle toggle-xs toggle-primary"
            v-model="includeChildBoards"
          />
        </label>
      </div>
    </div>

    <!-- Board breadcrumb info when including children -->
    <div v-if="includeChildBoards && allBoardIds.length > 1" class="flex flex-wrap gap-1 items-center">
      <span class="text-xs opacity-50">Showing files from:</span>
      <div
        v-for="bid in allBoardIds"
        :key="bid"
        class="badge badge-xs badge-outline"
      >
        {{ bid }}
      </div>
    </div>

    <!-- Selection toolbar -->
    <div v-if="selectionMode" class="flex items-center gap-2 bg-base-300 rounded-box px-3 py-2">
      <span class="text-sm font-medium">
        <i class="fa-solid fa-check-square text-primary mr-1"></i>
        {{ selectedFiles.length }} file(s) selected
      </span>
      <button class="btn btn-xs btn-ghost" @click="selectAll">All</button>
      <button class="btn btn-xs btn-ghost" @click="selectedFiles = []">None</button>
      <div class="grow"></div>
      <button class="btn btn-xs btn-ghost" @click="selectionMode = false">
        <i class="fa-solid fa-xmark"></i> Cancel
      </button>
    </div>

    <!-- Toggle selection mode when not active -->
    <div v-else class="flex justify-end">
      <button class="btn btn-xs btn-ghost gap-1" @click="selectionMode = true">
        <i class="fa-regular fa-square-check"></i> Select files
      </button>
    </div>

    <!-- Grouped by FILE -->
    <div v-if="groupBy === 'file'" class="flex flex-col gap-2">
      <div
        v-for="group in filteredFileGroups"
        :key="group.file"
        class="collapse collapse-arrow bg-base-200 rounded-box"
      >
        <input type="checkbox" :checked="expandedFiles[group.file]" @change="toggleExpand(group.file)" />
        <div class="collapse-title flex items-center gap-2 py-2 min-h-0">
          <input
            v-if="selectionMode"
            type="checkbox"
            class="checkbox checkbox-xs checkbox-primary"
            :checked="selectedFiles.includes(group.file)"
            @change.stop="toggleFileSelection(group.file)"
            @click.stop
          />
          <i class="fa-solid fa-file-code text-info text-xs"></i>
          <span class="font-mono text-xs truncate flex-1">{{ group.file }}</span>
          <button
            class="btn btn-ghost btn-xs px-1 mr-1"
            :class="{ 'text-success': copiedFile === group.file }"
            title="Copy file path"
            @click.stop.prevent="copyFileName(group.file)"
          >
            <i class="fa-regular fa-copy text-xs"></i>
          </button>
          <div class="badge badge-sm badge-neutral">{{ group.tasks.length }} tasks</div>
        </div>
        <div class="collapse-content">
          <div class="flex flex-col gap-1 pt-1">
            <div
              v-for="entry in group.tasks"
              :key="entry.chat.id + entry.source"
              class="flex items-center gap-2 p-2 bg-base-100 rounded-lg cursor-pointer hover:bg-base-300 transition-colors"
              @click="$emit('open-task', entry.chat)"
            >
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate">{{ entry.chat.name || 'Untitled' }}</div>
                <div class="flex gap-2 items-center mt-1">
                  <div class="badge badge-xs badge-outline">{{ entry.chat.column }}</div>
                  <div class="badge badge-xs badge-ghost">{{ entry.chat.board }}</div>
                  <span class="text-xs opacity-50">{{ sourceLabel(entry.source) }}</span>
                </div>
              </div>
              <i class="fa-solid fa-arrow-right text-xs opacity-40"></i>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!filteredFileGroups.length" class="text-center opacity-50 py-8">
        No files found
      </div>
    </div>

    <!-- Grouped by TASK -->
    <div v-if="groupBy === 'task'" class="flex flex-col gap-2">
      <div
        v-for="entry in filteredTaskGroups"
        :key="entry.chat.id"
        class="collapse collapse-arrow bg-base-200 rounded-box"
      >
        <input type="checkbox" />
        <div class="collapse-title flex items-center gap-2 py-2 min-h-0">
          <i class="fa-solid fa-comment text-primary text-xs"></i>
          <span class="text-sm font-medium flex-1 truncate">{{ entry.chat.name || 'Untitled' }}</span>
          <div class="badge badge-sm badge-ghost mr-1">{{ entry.chat.board }}</div>
          <div class="badge badge-sm badge-outline mr-2">{{ entry.chat.column }}</div>
          <div class="badge badge-sm badge-neutral mr-2">{{ entry.files.length }} files</div>
        </div>
        <div class="collapse-content">
          <div class="flex flex-col gap-1 pt-1">
            <div
              v-for="f in entry.files"
              :key="f.file + f.source"
              class="group flex items-center gap-2 p-2 bg-base-100 rounded-lg hover:bg-base-200 transition-colors"
            >
              <input
                v-if="selectionMode"
                type="checkbox"
                class="checkbox checkbox-xs checkbox-primary"
                :checked="selectedFiles.includes(f.file)"
                @change="toggleFileSelection(f.file)"
                @click.stop
              />
              <i class="fa-solid fa-file-code text-info text-xs w-4"></i>
              <span class="font-mono text-xs flex-1 truncate">{{ f.file }}</span>
              <button
                class="btn btn-ghost btn-xs px-1 opacity-0 group-hover:opacity-100 transition-opacity"
                :class="{ 'text-success opacity-100': copiedFile === f.file }"
                title="Copy file path"
                @click.stop="copyFileName(f.file)"
              >
                <i class="fa-regular fa-copy text-xs"></i>
              </button>
              <span class="badge badge-xs badge-ghost">{{ sourceLabel(f.source) }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!filteredTaskGroups.length" class="text-center opacity-50 py-8">
        No tasks with files found
      </div>
    </div>

    <!-- Grouped by COLUMN -->
    <div v-if="groupBy === 'column'" class="flex flex-col gap-2">
      <div
        v-for="col in filteredColumnGroups"
        :key="col.column"
        class="collapse collapse-arrow bg-base-200 rounded-box"
      >
        <input type="checkbox" checked />
        <div class="collapse-title flex items-center gap-2 py-2 min-h-0">
          <i class="fa-solid fa-table-columns text-secondary text-xs"></i>
          <span class="text-sm font-semibold flex-1">{{ col.column }}</span>
          <div class="badge badge-sm badge-ghost mr-1" v-if="col.board">{{ col.board }}</div>
          <div class="badge badge-sm badge-neutral mr-2">{{ col.files.length }} files</div>
        </div>
        <div class="collapse-content">
          <div class="flex flex-col gap-2 pt-1">
            <div v-for="entry in col.tasks" :key="entry.chat.id" class="bg-base-100 rounded-lg p-2">
              <div
                class="flex items-center gap-2 cursor-pointer hover:opacity-80"
                @click="$emit('open-task', entry.chat)"
              >
                <i class="fa-solid fa-comment text-primary text-xs"></i>
                <span class="text-sm font-medium flex-1 truncate">{{ entry.chat.name || 'Untitled' }}</span>
                <div class="badge badge-xs badge-neutral">{{ entry.files.length }}</div>
              </div>
              <div class="flex flex-col gap-1 mt-2 pl-5">
                <div
                  v-for="f in entry.files"
                  :key="f.file"
                  class="group flex items-center gap-2 rounded px-1 py-0.5 hover:bg-base-200 transition-colors"
                >
                  <input
                    v-if="selectionMode"
                    type="checkbox"
                    class="checkbox checkbox-xs checkbox-primary"
                    :checked="selectedFiles.includes(f.file)"
                    @change.stop="toggleFileSelection(f.file)"
                    @click.stop
                  />
                  <i class="fa-solid fa-file-code text-info text-xs"></i>
                  <span
                    class="font-mono text-xs flex-1 truncate cursor-pointer"
                    :class="selectedFiles.includes(f.file) ? 'text-primary' : ''"
                    :title="f.file"
                    @click.stop="selectionMode && toggleFileSelection(f.file)"
                  >
                    {{ shortPath(f.file) }}
                  </span>
                  <button
                    class="btn btn-ghost btn-xs px-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    :class="{ 'text-success opacity-100': copiedFile === f.file }"
                    title="Copy file path"
                    @click.stop="copyFileName(f.file)"
                  >
                    <i class="fa-regular fa-copy text-xs"></i>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="!filteredColumnGroups.length" class="text-center opacity-50 py-8">
        No files found
      </div>
    </div>

    <!-- TREE view -->
    <div v-if="groupBy === 'tree'" class="flex flex-col gap-2">
      <!-- Flat list mode -->
      <div v-if="treeViewMode === 'list'" class="flex flex-col gap-1">
        <div
          v-for="file in filteredFlatFileList"
          :key="file.path"
          class="group flex items-center gap-2 p-2 bg-base-200 rounded-lg hover:bg-base-300 transition-colors"
        >
          <input
            v-if="selectionMode"
            type="checkbox"
            class="checkbox checkbox-xs checkbox-primary"
            :checked="selectedFiles.includes(file.path)"
            @change="toggleFileSelection(file.path)"
            @click.stop
          />
          <i class="fa-solid fa-file-code text-info text-xs w-4"></i>
          <span class="font-mono text-xs flex-1 truncate" :title="file.path">{{ file.path }}</span>
          <button
            class="btn btn-ghost btn-xs px-1 opacity-0 group-hover:opacity-100 transition-opacity"
            :class="{ 'text-success opacity-100': copiedFile === file.path }"
            title="Copy file path"
            @click.stop="copyFileName(file.path)"
          >
            <i class="fa-regular fa-copy text-xs"></i>
          </button>
          <div class="badge badge-xs badge-neutral">{{ file.tasks.length }}</div>
        </div>
        <div v-if="!filteredFlatFileList.length" class="text-center opacity-50 py-8">
          No files found
        </div>
      </div>

      <!-- Tree mode -->
      <div v-else class="flex flex-col gap-1">
        <kanban-tree-node
          v-for="node in filteredFileTree"
          :key="node.name"
          :node="node"
          :selection-mode="selectionMode"
          :selected-files="selectedFiles"
          :expanded-nodes="expandedNodes"
          @toggle-expand="toggleNodeExpand"
          @toggle-select="toggleFileSelection"
          @toggle-select-many="toggleFolderSelection"
          @open-task="$emit('open-task', $event)"
        />
        <div v-if="!filteredFileTree.length" class="text-center opacity-50 py-8">
          No files found
        </div>
      </div>
    </div>

    <!-- Create chat modal -->
    <dialog ref="createChatModal" class="modal">
      <div class="modal-box flex flex-col gap-4">
        <h3 class="font-bold text-lg flex items-center gap-2">
          <i class="fa-solid fa-comment-medical text-primary"></i>
          New chat from files
        </h3>

        <!-- Chat name input -->
        <label class="form-control w-full">
          <div class="label">
            <span class="label-text">Chat name</span>
          </div>
          <input
            type="text"
            v-model="newChatName"
            placeholder="Leave empty for auto-name..."
            class="input input-bordered input-sm w-full"
          />
        </label>

        <!-- Mode selector -->
        <label class="form-control w-full">
          <div class="label">
            <span class="label-text">Mode</span>
          </div>
          <select v-model="newChatMode" class="select select-bordered select-sm">
            <option value="chat">Chat</option>
            <option value="task">Task</option>
          </select>
        </label>

        <!-- Selected files list -->
        <div class="flex flex-col gap-1">
          <div class="label-text mb-1">Files ({{ selectedFiles.length }})</div>
          <div class="max-h-48 overflow-y-auto flex flex-col gap-1">
            <div
              v-for="file in selectedFiles"
              :key="file"
              class="flex items-center gap-2 bg-base-200 rounded px-2 py-1"
            >
              <i class="fa-solid fa-file-code text-info text-xs"></i>
              <span class="font-mono text-xs flex-1 truncate">{{ file }}</span>
              <button class="btn btn-ghost btn-xs" @click="toggleFileSelection(file)">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </div>
        </div>

        <div class="modal-action mt-2">
          <button class="btn btn-ghost btn-sm" @click="closeCreateChatModal">Cancel</button>
          <button
            class="btn btn-primary btn-sm gap-2"
            :disabled="creatingChat || !selectedFiles.length"
            @click="createChatFromFiles"
          >
            <span v-if="creatingChat" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-comment-medical"></i>
            Create chat
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button>close</button>
      </form>
    </dialog>
  </div>
</template>

<script>
import KanbanTreeNode from './KanbanTreeNode.vue'

export default {
  components: { KanbanTreeNode },
  props: {
    columns: {
      type: Array,
      default: () => []
    }
  },
  emits: ['open-task', 'chat-created'],
  data() {
    return {
      fileFilter: '',
      groupBy: 'file',
      treeViewMode: 'tree',
      expandedFiles: {},
      expandedNodes: {},
      selectionMode: false,
      selectedFiles: [],
      newChatName: '',
      newChatMode: 'chat',
      creatingChat: false,
      copiedFile: null,
      includeChildBoards: true
    }
  },
  computed: {
    // Collect all board IDs: current + all descendants
    allBoardIds() {
      const kanban = this.$projects?.kanban || {}
      const activeBoard = this.$projects?.activeBoard
      if (!activeBoard || !this.includeChildBoards) return [activeBoard].filter(Boolean)
      return this.collectDescendantBoardIds(activeBoard, kanban.boards || {})
    },

    // All tasks from current board columns prop + child board tasks when enabled
    allTasks() {
      const fromColumns = this.columns.reduce((acc, col) => acc.concat(col.tasks || []), [])
      if (!this.includeChildBoards) return fromColumns

      // Gather tasks from child/descendant boards via allChats
      const allChats = Object.values(this.$projects?.allChats || {})
      const currentBoardId = this.$projects?.activeBoard
      const childBoardIds = this.allBoardIds.filter(id => id !== currentBoardId)
      const fromChildren = allChats
        .filter(c => !c.message_id && childBoardIds.includes(c.board))
        .map(c => ({ ...c, column: c.column || '--none--' }))

      // Merge, deduplicating by id
      const seen = new Set(fromColumns.map(t => t.id))
      const merged = [...fromColumns]
      fromChildren.forEach(t => {
        if (!seen.has(t.id)) {
          seen.add(t.id)
          merged.push(t)
        }
      })
      return merged
    },

    tasksWithFiles() {
      return this.allTasks.filter(chat => this.getFilesForChat(chat).length > 0)
    },

    allFiles() {
      return this.tasksWithFiles.reduce((acc, chat) => {
        return acc.concat(this.getFilesForChat(chat))
      }, [])
    },

    uniqueFiles() {
      return [...new Set(this.allFiles.map(f => f.file))]
    },

    fileGroups() {
      const map = {}
      this.allFiles.forEach(({ file, chat, source }) => {
        if (!map[file]) map[file] = { file, tasks: [] }
        map[file].tasks.push({ chat, source })
      })
      return Object.values(map).sort((a, b) => a.file.localeCompare(b.file))
    },

    taskGroups() {
      return this.tasksWithFiles.map(chat => ({
        chat,
        files: this.getFilesForChat(chat)
      }))
    },

    // Group by column, also keying on board so same-named columns on different boards are distinct
    columnGroups() {
      const map = {}
      this.tasksWithFiles.forEach(chat => {
        const key = `${chat.board}::${chat.column}`
        if (!map[key]) map[key] = { column: chat.column, board: chat.board, tasks: [], files: [] }
        const files = this.getFilesForChat(chat)
        map[key].tasks.push({ chat, files })
        map[key].files.push(...files)
      })
      return Object.values(map)
    },

    flatFileList() {
      return this.fileGroups.map(g => ({ path: g.file, tasks: g.tasks }))
    },

    filteredFlatFileList() {
      if (!this.fileFilter) return this.flatFileList
      const f = this.fileFilter.toLowerCase()
      return this.flatFileList.filter(fi =>
        fi.path.toLowerCase().includes(f) ||
        fi.tasks.some(t => t.chat.name?.toLowerCase().includes(f))
      )
    },

    fileTree() {
      return this.buildTree(this.fileGroups)
    },

    filteredFileTree() {
      if (!this.fileFilter) return this.fileTree
      const f = this.fileFilter.toLowerCase()
      const filtered = this.fileGroups.filter(g =>
        g.file.toLowerCase().includes(f) ||
        g.tasks.some(t => t.chat.name?.toLowerCase().includes(f))
      )
      return this.buildTree(filtered)
    },

    filteredFileGroups() {
      if (!this.fileFilter) return this.fileGroups
      const f = this.fileFilter.toLowerCase()
      return this.fileGroups.filter(g =>
        g.file.toLowerCase().includes(f) ||
        g.tasks.some(t => t.chat.name?.toLowerCase().includes(f))
      )
    },

    filteredTaskGroups() {
      if (!this.fileFilter) return this.taskGroups
      const f = this.fileFilter.toLowerCase()
      return this.taskGroups.filter(e =>
        e.chat.name?.toLowerCase().includes(f) ||
        e.files.some(fi => fi.file.toLowerCase().includes(f))
      )
    },

    filteredColumnGroups() {
      if (!this.fileFilter) return this.columnGroups
      const f = this.fileFilter.toLowerCase()
      return this.columnGroups.map(col => ({
        ...col,
        tasks: col.tasks.filter(e =>
          e.chat.name?.toLowerCase().includes(f) ||
          e.files.some(fi => fi.file.toLowerCase().includes(f))
        )
      })).filter(col => col.tasks.length > 0)
    }
  },
  methods: {
    // Recursively collect board ID + all descendant board IDs
    collectDescendantBoardIds(boardId, boards) {
      const ids = [boardId]
      Object.entries(boards).forEach(([id, board]) => {
        if (board.parent_id === boardId) {
          ids.push(...this.collectDescendantBoardIds(id, boards))
        }
      })
      return ids
    },

    getFilesForChat(chat) {
      const entries = []
      const seen = new Set()
      const addFile = (file, source) => {
        if (!file || seen.has(file + source)) return
        seen.add(file + source)
        entries.push({ file, chat, source })
      }
      ;(chat.files || []).forEach(f => {
        const path = typeof f === 'string' ? f : f?.path || f?.name
        if (path) addFile(path, 'chat')
      })
      ;(chat.file_list || []).forEach(f => {
        const path = typeof f === 'string' ? f : f?.path || f?.name
        if (path) addFile(path, 'file_list')
      })
      ;(chat.messages || []).forEach(msg => {
        ;(msg.files || []).forEach(f => {
          const path = typeof f === 'string' ? f : f?.path || f?.name
          if (path) addFile(path, 'message')
        })
      })
      return entries
    },

    buildTree(groups) {
      const root = {}
      groups.forEach(({ file, tasks }) => {
        const parts = file.replace(/\\/g, '/').split('/')
        let node = root
        parts.forEach((part, ix) => {
          if (!node[part]) node[part] = { __children: {}, __tasks: [], __isFile: false }
          if (ix === parts.length - 1) {
            node[part].__isFile = true
            node[part].__tasks = tasks
            node[part].__path = file
          }
          node = node[part].__children
        })
      })
      return this.nodeToArray(root, '')
    },

    nodeToArray(obj, parentPath) {
      return Object.entries(obj)
        .map(([name, val]) => {
          const path = parentPath ? `${parentPath}/${name}` : name
          if (val.__isFile) {
            return { name, path: val.__path || path, isFolder: false, tasks: val.__tasks }
          }
          const children = this.nodeToArray(val.__children, path)
          const fileCount = this.countLeaves(children)
          return { name, path, isFolder: true, children, fileCount }
        })
        .sort((a, b) => {
          if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1
          return a.name.localeCompare(b.name)
        })
    },

    countLeaves(nodes) {
      return nodes.reduce((acc, n) => {
        return acc + (n.isFolder ? this.countLeaves(n.children) : 1)
      }, 0)
    },

    toggleExpand(file) {
      this.expandedFiles = { ...this.expandedFiles, [file]: !this.expandedFiles[file] }
    },

    toggleNodeExpand(path) {
      this.expandedNodes = {
        ...this.expandedNodes,
        [path]: this.expandedNodes[path] === false ? true : false
      }
    },

    toggleFileSelection(file) {
      if (this.selectedFiles.includes(file)) {
        this.selectedFiles = this.selectedFiles.filter(f => f !== file)
      } else {
        this.selectedFiles = [...this.selectedFiles, file]
      }
    },

    toggleFolderSelection({ paths, select }) {
      if (select) {
        const toAdd = paths.filter(p => !this.selectedFiles.includes(p))
        this.selectedFiles = [...this.selectedFiles, ...toAdd]
      } else {
        this.selectedFiles = this.selectedFiles.filter(p => !paths.includes(p))
      }
    },

    selectAll() {
      this.selectedFiles = [...this.uniqueFiles]
    },

    async copyFileName(filePath) {
      this.$ui.copyTextToClipboard(filePath)
      this.copiedFile = filePath
      setTimeout(() => { this.copiedFile = null }, 1500)
    },

    openCreateChatModal() {
      this.newChatName = ''
      this.newChatMode = 'chat'
      this.$refs.createChatModal.showModal()
    },

    closeCreateChatModal() {
      this.$refs.createChatModal.close()
    },

    async createChatFromFiles() {
      if (!this.selectedFiles.length) return
      this.creatingChat = true
      try {
        const chat = await this.$service.chat.createChatFromFiles({
          files: this.selectedFiles,
          name: this.newChatName || undefined,
          mode: this.newChatMode
        })
        this.closeCreateChatModal()
        this.selectedFiles = []
        this.selectionMode = false
        this.$emit('chat-created', chat)
      } catch (e) {
        console.error('Failed to create chat from files', e)
      } finally {
        this.creatingChat = false
      }
    },

    sourceLabel(source) {
      const labels = { chat: 'Chat files', file_list: 'File list', message: 'Message' }
      return labels[source] || source
    },

    shortPath(filePath) {
      const parts = filePath.replace(/\\/g, '/').split('/')
      return parts.slice(-2).join('/')
    }
  }
}
</script>