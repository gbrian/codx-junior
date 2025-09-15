# [[{"id": "23a78a80-5972-46b9-9808-243650b247c8", "doc_id": null, "project_id": null, "parent_id": null, "message_id": null, "status": "", "tags": ["skip_knowledge"], "file_list": [], "check_lists": [], "profiles": ["daisyui_components", "Vue files"], "users": [], "name": "changes-at-kanban-kanban-vue-2025-09-15-05-55-42-118944", "description": "The user provided a Vue file and requested to apply best practices and rewrite the content according to specific guidelines. The instructions emphasized using DaisyUI components, following a structured format for Vue files, utilizing TailwindCSS for styling, and avoiding the use of certain imports and long functions. The user also requested to remove codx comments and to ensure that no details or parts of the document are lost while making these changes. Finally, the user asked to return only the content of the file without any additional comments or decorations.", "created_at": "2025-09-15 05:32:31.901060", "updated_at": "2025-09-15T05:58:15.183713", "mode": "chat", "kanban_id": "", "column_id": "", "board": "mentions", "column": "changes", "chat_index": 0, "url": "", "branch": "", "file_path": "", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "20fb80f0-8090-4d38-9338-7a1ce91cf9b7", "role": "user", "task_item": "", "think": "", "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-15 05:32:31.897138", "updated_at": "2025-09-15 05:32:31.897163", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]

        Apply codx comments and rewrite full content.
        Return only the content without any further decoration or comments.
        Do not surround response with '```' marks, just content.
        Remove codx comments from the final version.
        
## [[{"doc_id": "8d1c4565-538a-4222-a9c5-a22e1e850dc6", "role": "user", "task_item": "", "think": "", "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-15 05:32:31.897138", "updated_at": "2025-09-15 05:32:31.897163", "images": [], "files": ["/shared/codx-junior/client/src/components/kanban/Kanban.vue"], "meta_data": {}, "profiles": ["daisyui_components", "Vue files"], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]

                    Processing user's file comments.
                  
                    File:
                    ```document /shared/codx-junior/client/src/components/kanban/Kanban.vue
                    <script setup>
import draggable from "vuedraggable"
import TaskCard from "./TaskCard.vue"
import TaskCardLite from "./TaskCardLite.vue"
import ChatViewVue from "../../views/ChatView.vue"
import { v4 as uuidv4 } from "uuid"
import VSwatches from "../VSwatches.vue"
import KanbanList from "./KanbanList.vue"
import ChatIcon from "../chat/ChatIcon.vue"
import ProjectIcon from "../ProjectIcon.vue"
</script>

<template>
  <div class="h-full px-2" v-if="kanban?.boards">
    <div class="flex flex-col gap-2" v-if="!$projects.activeChat && !board">
      <div class="font-bold" v-if="topProjects?.length">Related projects</div>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4" v-if="$storex.projects.childProjects">
        <ProjectIcon v-for="project in topProjects" :key="project.project_id"
          :project="project" 
          :online="true" 
          :right="false"
          @click="$projects.setActiveProject(project)"
          />
      </div>
      
      <div v-if="lastUpdatedTasks?.length">
        <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between">
          <div>Last tasks</div>
        </h1>
        <div class="grid grid-cols-2 grid-flow-row gap-2">
          <TaskCardLite @click="$projects.setActiveChat(task)" 
            :task="task" class="click h-40 overflow-hidden border rounded-md border-slate-600" v-for="task in lastUpdatedTasks" :key="task.id"/>
        </div>
      </div>

      <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between">
        <div>Boards Dashboard</div>
        <input type="text" v-model="boardFilter" class="input input-sm input-bordered" placeholder="Search boards" />
        <button class="btn btn-sm btn-warning btn-outline" @click="showNewBoardModal">
          New kanban
        </button>
      </h1>
      <KanbanList
        :boards="filteredParentBoards"
        @select="selectBoard"
        @edit="onEditBoard"
        @new="showNewBoardModal"
        @delete="onDeleteBoard"
      />
    </div>

    <ChatViewVue
      class="h-full"
      @chats="onChatEditDone"
      @sub-task="createSubTask"
      @sub-tasks="createSubTasks"
      @chat="$projects.setActiveChat($event)"
      :kanban="activeBoard"
      :chat="$projects.activeChat"
      v-if="$projects.activeChat"
    />
    <div class="flex flex-col h-full" v-if="!$projects.activeChat && showKanban">
      <div class="flex gap-4 items-center">
        <div class="flex gap-2 items-center">
          <div tabindex="0" class="text-xl py-1 px-2 cursor-pointer flex items-center gap-2" @click="toggleDropdown">
            <button class="btn btn-sm" @click="selectBoard(parentBoard?.title)">
              <i class="fa-solid fa-caret-left"></i>
            </button>
            {{ activeBoard?.title }}
          </div>
        </div>
        <div class="grow"></div>
        <div class="flex gap-2 items-center">
          <div class="grow input input-sm input-bordered flex items-center gap-2">
            <input type="text" :class="{ hidden: !searchVisible }" v-model="filter" class="grow" placeholder="Search..." />
            <span class="cursor-pointer" v-if="filter" @click.stop="[filter = '', searchVisible = false]">
              <i class="fa-regular fa-circle-xmark"></i>
            </span>
            <span v-else><i class="fa-solid fa-filter click" @click="searchVisible = !searchVisible"></i></span>
          </div>
          <button class="btn btn-sm" @click="showColumnModal = true">
            <i class="fa-solid fa-table-columns"></i>
          </button>
          <div class="dropdown dropdown-left">
            <div tabindex="0" class="btn btn-sm mt-1">
              <i class="fa-solid fa-ellipsis-vertical"></i>
            </div>
            <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
              <li @click="addNewFile"><a><i class="fa-solid fa-plus"></i> File</a></li>
              <li @click="showColumnModal = true"><a><i class="fa-solid fa-plus"></i> Column</a></li>
              <li @click="showNewBoardModal"><a><i class="fa-solid fa-plus"></i> Board</a></li>
              <li @click="showChildrenBoards = !showChildrenBoards"><a><i class="fa-solid fa-eye"></i> Show Boards</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="mt-3 grow relative flex flex-col gap-2">
        <div class="transition-all pb-2" v-if="showChildrenBoards">
          <KanbanList
            class="mb-2"
            :boards="childBoards"
            :options="{ addNew: false }"
            @select="selectBoard"
            @edit="onEditBoard"
            @new="showNewBoardModal"
          />
        </div>
        
        <draggable
          v-model="filteredColumns"
          group="columns"
          itemKey="id"
          :disabled="$ui.isMobile"
          @end="onColumnTaskListChanged"
          class="min-h-60 grid grid-flow-col overflow-x-scroll relative gap-2 justify-start"
        >
          <template #item="{ element: column }">
            <div class="bg-info/20 rounded-lg px-3 py-3 w-80 rounded overflow-auto h-full flex flex-col"
              :class="column.color && 'border-t-4'"
              :style="{ borderColor: column.color }"
            >
              <div class="group font-semibold font-sans tracking-wide text-sm flex gap-2 items-center">
                <div class="cursor-pointer w-6 h-6 flex items-center justify-center rounded-md group shadow-lg bg-base-100" 
                  :style="{ backgroundColor: column.color }" @click="openColumnPropertiesModal(column)">
                  <span class="hidden group-hover:block">
                    <i class="fa-solid fa-pen-to-square"></i>
                  </span>
                </div>
                <div class="flex gap-2 items-center grow">
                  <div>{{column.title}}</div>
                </div>
                <div class="flex gap-2 items-center">
                  <div class="dropdown dropdown-end">
                    <div tabindex="0" role="button" class="btn btn-sm m-1 flex items-center">
                      <span v-if="column.tasks?.length">({{ column.tasks.length }})</span>
                      <i class="mt-1 fa-solid fa-plus"></i>
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li class="flex gap-2" @click="newTask(column.title, 'chat')">
                        <a><ChatIcon mode="chat" /> Chat</a>
                      </li>
                      <li class="flex gap-2" @click="newTask(column.title, 'task')">
                        <a><ChatIcon mode="task" /> Document</a>
                      </li>
                      <li class="flex gap-2" @click="newTask(column.title, 'topic')">
                        <a><ChatIcon mode="topic" /> Discussion</a>
                      </li>
                      <li class="flex gap-2" @click="newTask(column.title, 'prview')">
                        <a><ChatIcon mode="prview" /> Changes review</a>
                      </li>
                      <li class="flex gap-2" @click="importTask(column.title)">
                        <a>Import task</a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
              <div class="grow overflow-y-auto">
                <draggable
                  v-model="column.tasks"
                  group="tasks"
                  itemKey="id"
                  :disabled="$ui.isMobile"
                  @end="onColumnTaskListChanged(column)"
                  class="mt-3"
                >
                  <template #item="{ element: task }">
                    <task-card
                      v-if="taskMatchesFilter(task)"
                      :task="task"
                      :itemKey="'id'"
                      class="cursor-pointer bg-base-100 overflow-hidden mt-2"
                      :class="[lastUpdatedTask.id == task.id ? 'border boder-primary border-dashed':'',
                        (column.showSubTasks !== false) || !task.parent_id ? '' : 'hidden'
                      ]"
                      @click="openChat(task)"
                    />
                  </template>
                </draggable>
              </div>
            </div>
          </template>
        </draggable>
      </div>
    </div>
    <modal v-if="showBoardModal">
      <h2 class="font-bold text-3xl">{{ editBoard ? 'Edit Board' : 'Add New Board' }}</h2>
      <div class="collapse bg-contain"
        :style="`background-image:url('${ newBoardBackground }')`"
      >
        <input type="radio" name="newboard"  v-model="newBoardType" value="manual" />
        <div class="hidden collapse-title text-xl font-medium"><i class="fa-solid fa-gear"></i> Manual settings</div>
        <div class="collapse-content">
          <div class="text-xl text-info font-bold" v-if="activeBoard">Parent {{ activeBoard.title }}</div>
          <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardDescription" placeholder="Enter board description" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardBackground" placeholder="Enter board backgorund image" class="input input-bordered w-full mt-2"/>
        @codx-ok, please-wait...: add a select with all boards to allow changing the board parent
        </div>
      </div>
      <div class="collapse hidden">
        <input type="radio" name="newboard" v-model="newBoardType" value="issue" />
        <div class="collapse-title text-xl font-medium"><i class="fa-solid fa-link"></i> From issue</div>
        <div class="collapse-content">
          <input type="text" v-model="newBoardIssueLink" placeholder="Enter isue url" class="input input-bordered w-full mt-2"/>
        </div>
      </div>

      <div class="modal-action">
        <button class="btn" @click="addOrUpdateBoard" :disabled="isBoardNameTaken || !newBoardName">Save</button>
        <button class="btn" @click="showBoardModal = false">Cancel</button>
      </div>
    </modal>
    <modal v-if="showColumnModal">
      <h2 class="font-bold text-lg">Add/Edit Column</h2>
      <div class="flex gap-1 items-center">
        <VSwatches v-model="columnColor" class="h-full mt-1" />
        <input type="text" v-model="columnTitle" placeholder="Enter column name"
          class="grow input input-bordered w-full"/>
        
      </div>
      <span v-if="editColumnError" class="text-error">{{ editColumnError }}</span>
      <div class="modal-action">
        <button class="btn" @click="addOrUpdateColumn">OK</button>
        <button class="btn" @click="showColumnModal = false">Cancel</button>
        <button class="btn btn-error" @click="deleteColumn">Delete</button>
        <div class="text-error text-xs" v-if="confirmDeleteColumn">
          Are you sure you want to delete this column? 
          All tasks will be removed.
        </div>
      </div>
      <div class="badge badge-error" v-if="editColumnError">{{ editColumnError }}</div>
    </modal>
    <modal v-if="showImportModalForColumn">
      <h2 class="font-bold text-lg">Import Task</h2>
      <div class="form-control">
        <label class="label cursor-pointer">
          <span class="label-text">Import from clipboard</span> 
          <input type="radio" name="importOptions" value="clipboard" v-model="importOption" class="radio" />
        </label>
        <label class="label cursor-pointer">
          <span class="label-text">Import from URL</span> 
          <input type="radio" name="importOptions" value="url" v-model="importOption" class="radio" />
        </label>
        <input v-if="importOption === 'url'" type="text" v-model="importUrl" placeholder="Paste URL here" class="input input-bordered w-full mt-2"/>
      </div>
      <div class="modal-action">
        <button class="btn" @click="confirmImportTask">Import</button>
        <button class="btn" @click="showImportModalForColumn = false">Cancel</button>
      </div>
    </modal>
  </div>
</template>

<script>
const ALL_BOARD_TITLE_ID = "$ALL"
const FILES_COLUMN = "__files__"
export default {
  data() {
    return {
      boardFilter: '',
      filter: null,
      showBoardModal: false,
      showColumnModal: false,
      newBoardType: 'manual',
      newBoardIssueLink: '',
      newBoardName: '',
      newBoardDescription: '',
      newBoardBackground: '',
      newBoardBranch: '',
      columnTitle: '',
      columnColor: '#000000',
      isDropdownOpen: false,
      selectedColumn: null,
      editColumnError: null,
      columns: [],
      selectedTemplate: null,
      showChildrenBoards: false,
      editBoard: null,
      originalBoardName: null,
      filteredColumns: [],
      confirmDeleteColumn: false,
      showImportModalForColumn: null,
      importOption: 'clipboard',
      importUrl: '',
      searchVisible: false
    }
  },
  created() {
    this.projectChanged()
  },
  computed: {
    topProjects() {
      const children = this.$storex.projects.childProjects
      const parent = this.$project.parentProject
      return parent ? [parent, ...children] : children
    },
    filteredParentBoards() {
      return this.parentBoards.filter(board => 
        board.title.toLowerCase().includes(this.boardFilter.toLowerCase())
      )
    },
    board() {
      return this.$projects.activeBoard
    },
    lastUpdatedTask() {
      return this.visibleTasks.sort((a, b) => 
        (a.updated_at || new Date(1900, 1, 1)) > 
        (b.updated_at || new Date(1900, 1, 1)) ? -1 : 1)
        .slice(0, 1)[0] || {}
    },
    lastUpdatedTasks() {
      return this.chats.sort((a, b) => 
        (a.updated_at || new Date(1900, 1, 1)) > 
        (b.updated_at || new Date(1900, 1, 1)) ? -1 : 1)
        .slice(0, 3) || []
    },
    showKanban() {
      return this.kanban && this.activeKanbanBoard
    },
    kanban() {
      return this.$projects.kanban
    },
    activeKanbanBoard() {
      return this.kanban.boards[this.board]
    },
    chats() {
      const allChats = this.$projects.allChats
      return Object.values(allChats || {}).map(c => ({
        ...c,
        column: c.column || "--none--"
      }))
    },
    chat() {
      return this.$projects.activeChat
    },
    project() {
      return this.$projects.activeProject
    },
    activeBoard() {
      return this.boards[this.$projects.activeBoard]
    },
    boardColumns() {
      return this.boards[this.board]?.columns
    },
    columnList() {
      return (this.boards[this.board]?.columns?.map(c => c.title) || [])
    },
    parentBoard() {
      return this.boards[this.activeBoard?.parent_id]
    },
    boards() {
      const { kanban: { boards }, chats } = this
      return [
        ...Object.keys(boards).map(board => ({
          ...boards[board],
          id: board,
          title: board
        }))
      ].reduce((acc, b) => ({ ...acc, [b.id]: {
        ...b,
        tasks: chats.filter(c => !c.message_id && (b.id === ALL_BOARD_TITLE_ID || c.board === b.id))
      }}), {})
    },
    parentBoards() {
      return Object.values(this.boards).filter(b => !b.parent_id)
    },
    childBoards() {
      return Object.values(this.boards).filter(b => b.parent_id === this.activeBoard?.id)
    },
    visibleTasks() {
      return this.filteredColumns.reduce((a, b) => a.concat(b.tasks || []), [])
    },
    templates() {
      return this.$projects.kanbanTemplates
    },
    isBoardNameTaken() {
      return this.newBoardName && this.newBoardName !== this.originalBoardName && this.kanban.boards[this.newBoardName];
    }
  },
  watch: {
    filter(newValue, oldValue) {
      if ((!newValue && oldValue) || newValue?.length > 3) {
        this.buildKanban()
      }
    },
    project() {
      this.projectChanged()
    },
    chats(newValue, oldValue) {
      if (newValue.map(c => c.id).sort().join()
      !== oldValue.map(c => c.id).sort().join())
      this.buildColumns()
    },
    kanban() {
      this.buildKanban()
    }
  },
  methods: {
    buildFilteredColumns() {
      if (!this.filter) {
        this.filteredColumns = this.columns
      } else {
        const filterText = this.filter.toLowerCase()
        this.filteredColumns = this.columns.map(column => {
          const filteredTasks = column.tasks.filter(task => {
            const taskNameMatches = task.name.toLowerCase().includes(filterText)
            const messageContentMatches = task.messages?.some(message =>
              message.content.toLowerCase().includes(filterText)
            )
            return taskNameMatches || messageContentMatches
          })
          return { ...column, tasks: filteredTasks }
        })
      }
    },
    async projectChanged() {
      await this.$projects.loadKanban()
      this.selectBoard()
      this.buildKanban()
    },
    toggleDropdown() {
      this.isDropdownOpen = !this.isDropdownOpen
    },
    async selectBoard(board) {
      this.$projects.setActiveBoard(board)
      this.isDropdownOpen = false
      await this.$projects.loadChats()
      if (board && this.kanban.boards[board] && !this.kanban.boards[board].active) {
        Object.keys(this.kanban.boards)
          .filter(b => this.kanban.boards[b])
          .forEach(b => this.kanban.boards[b].active = (b === board))
        this.kanban.boards[board].last_update = new Date().toISOString()
        this.saveKanban()
      }
      this.buildKanban()
      this.showChildrenBoards = !!this.childBoards?.length
    },
    async editKanban(board) {
      if (!this.newBoardName.trim()) {
        return
      }
      board.title = this.newBoardName
      board.description = this.newBoardDescription
      board.background = this.newBoardBackground
      board.last_update = new Date().toISOString()
      await this.saveKanban()
    },
    async createNewChat(base) {
      return this.$projects.createNewChat({
        ...base,
        id: uuidv4(),
        board: this.board || "Default",
      })
    },
    addNewFile() {
      this.newTask(FILES_COLUMN)
    },
    newTask(column, mode) {
      this.createNewChat({
        column,
        name: "New Task",
        mode: mode || 'chat',
        profiles: []
      })
    },
    async importTask(column) {
      this.showImportModalForColumn = column
    },
    async confirmImportTask() {
      const column = this.activeBoard?.columns?.find(c => c.title === this.columnTitle)
      if (this.importOption === 'clipboard') {
        const clipboardContent = await navigator.clipboard.readText()
        const existingChat = JSON.parse(clipboardContent)
        const newChat = await this.createNewChat({
          ...existingChat,
          id: null,
          column
        })
        this.$projects.saveChat(newChat)
      } else if (this.importOption === 'url') {
        const chat = {
          board: this.board || "Default",
          column: this.showImportModalForColumn,
          name: "Import from url",
          mode: 'chat',
          url: this.importUrl
        }
        await this.$projects.createNewChatFromUrl(chat)
      }
      this.showImportModalForColumn = null
      this.importUrl = null
    },
    async buildKanban() {
      if (this.kanban) {
        this.buildColumns()
      }
    },
    buildColumns() {
      const columnTitles = this.columnList
      const cloumnChats = this.kanban.boards[this.board]?.columns?.chats || []
      this.columns = columnTitles
        .map((col, ix) => {
          const boardColumn = this.boards[this.board]?.columns?.find(bc => bc.title === col)||{}
          const getChatIndex = c => {
            return cloumnChats.findIndex(kc => kc.id === c.id)
          }
          return {
            title: col,
            ...boardColumn,
            tasks: this.activeBoard.tasks
              .filter(t => (t.column || "--none--") === col)
              .sort((a, b) => getChatIndex(a) < getChatIndex(b) ? -1 : 1),
            position: ix
          }
        }).sort((a, b) => a.position < b.position ? -1: 1)
        || []
        this.buildFilteredColumns()
    },
    async onColumnTaskListChanged() {
      if (this.$ui.isMobile) {
        return
      }
      const kboard = this.kanban.boards[this.board]
      kboard.columns = await Promise.all(this.filteredColumns.map(async (column, ix) => {
        const kcolumn = kboard.columns.find(kc => kc.id === column.id)
        kcolumn.chats = column.tasks.map(t => t.id)
        await Promise.all(column.tasks.filter(t => t.column !== column.title)
          .map(task => this.$storex.projects.saveChatInfo({ ...task, column: column.title })))
        return kcolumn
      }))
      kboard.last_update = new Date().toISOString()
      this.saveKanban()
    },
    async openChat(element) {
      if (element.id === -1) {
        this.newChat()
      } else {
        await this.$projects.setActiveChat(element)
      }
    },
    async onChatEditDone(board) {
      if (this.board !== board) {
        this.selectBoard(board)
      }
      await this.$projects.setActiveChat()
      this.buildKanban()
    },
    async createSubTask({ parent, name, description, project_id, parent_id, message_id, file_list }) {
      const chat = await this.createNewChat({
        board: parent.board,
        name,
        column: parent.column,
        parent_id: parent_id || parent.id,
        message_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: "user", content: description }] : [],
        file_list
      })
      
      this.$projects.saveChat(chat)
      if (description) {
        this.$storex.projects.chatWihProject(chat)
      }
    },
    async createSubTasks(event) {
      this.$projects.createSubtasks(event)
    },
    async addOrUpdateColumn() {
      this.columnTitle = this.columnTitle.trim()
      if (!this.columnTitle) {
        return this.resetColumnModal()
      }
      const existingColumnTitle = this.activeKanbanBoard.columns.find(c => c.title === this.columnTitle)
      if (existingColumnTitle && existingColumnTitle.id !== this.selectedColumn?.id) {
        this.editColumnError = "Name already used"
        return
      }
      if (this.selectedColumn) {
        this.selectedColumn.title = this.columnTitle
        this.selectedColumn.color = this.columnColor
      } else {
        const newColumn = {
          id: uuidv4(),
          title: this.columnTitle,
          color: this.columnColor
        }
        this.activeBoard.columns.push(newColumn)
      }
      this.activeBoard.last_update = new Date().toISOString()
      await this.saveKanban()
      this.resetColumnModal()
      this.buildKanban()
    },
    async deleteColumn() {
      if (this.confirmDeleteColumn) {
        this.resetColumnModal()
        this.activeKanbanBoard.columns = this.activeKanbanBoard.columns.filter(
          column => column.id !== this.selectedColumn.id
        )
        await this.saveKanban()
      }
      this.confirmDeleteColumn = !this.confirmDeleteColumn
    },
    resetColumnModal() {
      this.showColumnModal = false
      this.columnTitle = ''
      this.columnColor = '#000000'
      this.selectedColumn = null
      this.editColumnError = null
    },
    async addOrUpdateBoard() {
      const oldBoardName = this.originalBoardName;
      const boardName = this.newBoardName.trim()
      let board = this.editBoard ? this.kanban.boards[oldBoardName] :
                                    {
                                      title: boardName,
                                      columns: [],
                                    }
      if (this.editBoard && boardName !== this.originalBoardName) {
        delete this.kanban.boards[oldBoardName];
        board.title = boardName;
        this.chats.forEach(chat => {
          if (chat.board === oldBoardName) {
            chat.board = boardName;
            this.$projects.saveChatInfo(chat)
          }
        });
      }
      
      this.kanban.boards[boardName] = board 
      board.description = this.newBoardDescription?.trim()
      board.background = this.newBoardBackground?.trim()

      await this.saveKanban();
      this.showBoardModal = false;
      this.resetNewBoardInfo();
      this.buildKanban();
    },
    resetNewBoardInfo () {
      this.newBoardName = ''
      this.newBoardDescription = ''
      this.newBoardBackground = ''
      this.newBoardBranch = ''
      this.selectedTemplate = null
      this.newBoardIssueLink = ''
    },
    openColumnPropertiesModal(column) {
      this.selectedColumn = this.activeKanbanBoard.columns.find(c => c.id === column.id)
      this.columnTitle = column?.title
      this.columnColor = column?.color || '#000000'
      this.showColumnModal = true
    },
    async saveKanban() {
      await this.$projects.saveKanban()
    },
    showNewBoardModal() {
      this.newBoardName = null
      this.newBoardDescription = null
      this.showBoardModal = true
    },
    taskMatchesFilter(task) {
      const filterText = this.filter?.toLowerCase() || ''
      const taskNameMatches = task.name.toLowerCase().includes(filterText)
      const messageContentMatches = task.messages?.some(message =>
        message.content.toLowerCase().includes(filterText)
      )
      return taskNameMatches || messageContentMatches
    },
    onEditBoard(board) {
      this.editBoard = board;
      this.originalBoardName = board.title;
      this.newBoardBackground = board.background;
      this.newBoardDescription = board.description;
      this.newBoardName = board.title;
      this.showBoardModal = true;
    },
    onDeleteBoard(board) {
      this.$projects.deleteBoard(board)
    }
  }
}
</script>

                    ```

                    User comments:
                      User commented in line 197: add a select with all boards to allow changing the board parent
                    
                    Instructions:
                      Best practices for this file:
            Project uses DaisyUI for components, use them instead basic HTML elements
When writing vue files always follow this best parctices:
Vue files must always follow this structure in this order.
No other elements are valid:
```example vue file
<script setup>
import Component from './component.vue'
import markdown from 'mardown'
</script>
<template>
<div class="w.full h-full flex gap-2">
</div>
</template>
<script>
export default {
props: [].
data (){
// Reactive data, don't use "ref"
 return { myVariable: null }
},
computed: {},
watch: {},
methods: {}
}
</sctipt>
```
* No need to import ref, computed or mapState 
* export default component object
* Use component "data" method to return an object variables
* Use component "computed" to define computed properties
" Use component "methods" to define component methods 
* Use "this.$storex" or "$storex" to access store data.
* To access vue store data use "$storex"
* "script setup" section contains ONLY imports, no variables, properties bnor methods
* Use TailwindCSS classes for styling, always consider mobile styles
* Vue component definition will be exporting a default object like, without ref, nor computed imports
* Don't use ";" in the javascript or typescript code
* Avoid long functions
* Add short and concise comments for complex functions
* Don't use <style> elements, use TailWindCSS classes
            
                      Apply all comments to the document and return a final version.
                      Pay attention to do not loose any detail or part of the document.
                      Return only the file content 
                    
## [[{"doc_id": "cce86a14-e652-454a-8d9e-e0d9536b80f6", "role": "assistant", "task_item": "", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-15 05:32:31.897138", "updated_at": "2025-09-15 05:32:31.897163", "images": [], "files": [], "meta_data": {"time_taken": 150.79583859443665, "first_chunk_time_taken": 8.130073547363281e-05, "model": "openai/gpt-4o"}, "profiles": ["daisyui_components", "Vue files"], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
<script setup>
import draggable from 'vuedraggable'
import TaskCard from './TaskCard.vue'
import TaskCardLite from './TaskCardLite.vue'
import ChatViewVue from '../../views/ChatView.vue'
import { v4 as uuidv4 } from 'uuid'
import VSwatches from '../VSwatches.vue'
import KanbanList from './KanbanList.vue'
import ChatIcon from '../chat/ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
</script>

<template>
  <div class="h-full px-2" v-if="kanban?.boards">
    <div class="flex flex-col gap-2" v-if="!$projects.activeChat && !board">
      <div class="font-bold" v-if="topProjects?.length">Related projects</div>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4" v-if="$storex.projects.childProjects">
        <ProjectIcon v-for="project in topProjects" :key="project.project_id"
          :project="project" 
          :online="true" 
          :right="false"
          @click="$projects.setActiveProject(project)"
          />
      </div>
      
      <div v-if="lastUpdatedTasks?.length">
        <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between">
          <div>Last tasks</div>
        </h1>
        <div class="grid grid-cols-2 grid-flow-row gap-2">
          <TaskCardLite @click="$projects.setActiveChat(task)" 
            :task="task" class="click h-40 overflow-hidden border rounded-md border-slate-600" v-for="task in lastUpdatedTasks" :key="task.id"/>
        </div>
      </div>

      <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between">
        <div>Boards Dashboard</div>
        <input type="text" v-model="boardFilter" class="input input-sm input-bordered" placeholder="Search boards" />
        <button class="btn btn-sm btn-warning btn-outline" @click="showNewBoardModal">
          New kanban
        </button>
      </h1>
      <KanbanList
        :boards="filteredParentBoards"
        @select="selectBoard"
        @edit="onEditBoard"
        @new="showNewBoardModal"
        @delete="onDeleteBoard"
      />
    </div>

    <ChatViewVue
      class="h-full"
      @chats="onChatEditDone"
      @sub-task="createSubTask"
      @sub-tasks="createSubTasks"
      @chat="$projects.setActiveChat($event)"
      :kanban="activeBoard"
      :chat="$projects.activeChat"
      v-if="$projects.activeChat"
    />
    <div class="flex flex-col h-full" v-if="!$projects.activeChat && showKanban">
      <div class="flex gap-4 items-center">
        <div class="flex gap-2 items-center">
          <div tabindex="0" class="text-xl py-1 px-2 cursor-pointer flex items-center gap-2" @click="toggleDropdown">
            <button class="btn btn-sm" @click="selectBoard(parentBoard?.title)">
              <i class="fa-solid fa-caret-left"></i>
            </button>
            {{ activeBoard?.title }}
          </div>
        </div>
        <div class="grow"></div>
        <div class="flex gap-2 items-center">
          <div class="grow input input-sm input-bordered flex items-center gap-2">
            <input type="text" :class="{ hidden: !searchVisible }" v-model="filter" class="grow" placeholder="Search..." />
            <span class="cursor-pointer" v-if="filter" @click.stop="[filter = '', searchVisible = false]">
              <i class="fa-regular fa-circle-xmark"></i>
            </span>
            <span v-else><i class="fa-solid fa-filter click" @click="searchVisible = !searchVisible"></i></span>
          </div>
          <button class="btn btn-sm" @click="showColumnModal = true">
            <i class="fa-solid fa-table-columns"></i>
          </button>
          <div class="dropdown dropdown-left">
            <div tabindex="0" class="btn btn-sm mt-1">
              <i class="fa-solid fa-ellipsis-vertical"></i>
            </div>
            <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
              <li @click="addNewFile"><a><i class="fa-solid fa-plus"></i> File</a></li>
              <li @click="showColumnModal = true"><a><i class="fa-solid fa-plus"></i> Column</a></li>
              <li @click="showNewBoardModal"><a><i class="fa-solid fa-plus"></i> Board</a></li>
              <li @click="showChildrenBoards = !showChildrenBoards"><a><i class="fa-solid fa-eye"></i> Show Boards</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="mt-3 grow relative flex flex-col gap-2">
        <div class="transition-all pb-2" v-if="showChildrenBoards">
          <KanbanList
            class="mb-2"
            :boards="childBoards"
            :options="{ addNew: false }"
            @select="selectBoard"
            @edit="onEditBoard"
            @new="showNewBoardModal"
          />
        </div>
        
        <draggable
          v-model="filteredColumns"
          group="columns"
          itemKey="id"
          :disabled="$ui.isMobile"
          @end="onColumnTaskListChanged"
          class="min-h-60 grid grid-flow-col overflow-x-scroll relative gap-2 justify-start"
        >
          <template #item="{ element: column }">
            <div class="bg-info/20 rounded-lg px-3 py-3 w-80 rounded overflow-auto h-full flex flex-col"
              :class="column.color && 'border-t-4'"
              :style="{ borderColor: column.color }"
            >
              <div class="group font-semibold font-sans tracking-wide text-sm flex gap-2 items-center">
                <div class="cursor-pointer w-6 h-6 flex items-center justify-center rounded-md group shadow-lg bg-base-100" 
                  :style="{ backgroundColor: column.color }" @click="openColumnPropertiesModal(column)">
                  <span class="hidden group-hover:block">
                    <i class="fa-solid fa-pen-to-square"></i>
                  </span>
                </div>
                <div class="flex gap-2 items-center grow">
                  <div>{{column.title}}</div>
                </div>
                <div class="flex gap-2 items-center">
                  <div class="dropdown dropdown-end">
                    <div tabindex="0" role="button" class="btn btn-sm m-1 flex items-center">
                      <span v-if="column.tasks?.length">({{ column.tasks.length }})</span>
                      <i class="mt-1 fa-solid fa-plus"></i>
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li class="flex gap-2" @click="newTask(column.title, 'chat')">
                        <a><ChatIcon mode="chat" /> Chat</a>
                      </li>
                      <li class="flex gap-2" @click="newTask(column.title, 'task')">
                        <a><ChatIcon mode="task" /> Document</a>
                      </li>
                      <li class="flex gap-2" @click="newTask(column.title, 'topic')">
                        <a><ChatIcon mode="topic" /> Discussion</a>
                      </li>
                      <li class="flex gap-2" @click="newTask(column.title, 'prview')">
                        <a><ChatIcon mode="prview" /> Changes review</a>
                      </li>
                      <li class="flex gap-2" @click="importTask(column.title)">
                        <a>Import task</a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
              <div class="grow overflow-y-auto">
                <draggable
                  v-model="column.tasks"
                  group="tasks"
                  itemKey="id"
                  :disabled="$ui.isMobile"
                  @end="onColumnTaskListChanged(column)"
                  class="mt-3"
                >
                  <template #item="{ element: task }">
                    <task-card
                      v-if="taskMatchesFilter(task)"
                      :task="task"
                      :itemKey="'id'"
                      class="cursor-pointer bg-base-100 overflow-hidden mt-2"
                      :class="[lastUpdatedTask.id == task.id ? 'border boder-primary border-dashed':'',
                        (column.showSubTasks !== false) || !task.parent_id ? '' : 'hidden'
                      ]"
                      @click="openChat(task)"
                    />
                  </template>
                </draggable>
              </div>
            </div>
          </template>
        </draggable>
      </div>
    </div>
    <modal v-if="showBoardModal">
      <h2 class="font-bold text-3xl">{{ editBoard ? 'Edit Board' : 'Add New Board' }}</h2>
      <div class="collapse bg-contain"
        :style="`background-image:url('${ newBoardBackground }')`"
      >
        <input type="radio" name="newboard"  v-model="newBoardType" value="manual" />
        <div class="hidden collapse-title text-xl font-medium"><i class="fa-solid fa-gear"></i> Manual settings</div>
        <div class="collapse-content">
          <div class="text-xl text-info font-bold" v-if="activeBoard">Parent {{ activeBoard.title }}</div>
          <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardDescription" placeholder="Enter board description" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardBackground" placeholder="Enter board backgorund image" class="input input-bordered w-full mt-2"/>
          <select v-model="newBoardParent" class="select select-bordered w-full mt-2">
            <option v-for="board in parentBoards" :value="board.id">{{ board.title }}</option>
          </select>
        </div>
      </div>
      <div class="collapse hidden">
        <input type="radio" name="newboard" v-model="newBoardType" value="issue" />
        <div class="collapse-title text-xl font-medium"><i class="fa-solid fa-link"></i> From issue</div>
        <div class="collapse-content">
          <input type="text" v-model="newBoardIssueLink" placeholder="Enter isue url" class="input input-bordered w-full mt-2"/>
        </div>
      </div>

      <div class="modal-action">
        <button class="btn" @click="addOrUpdateBoard" :disabled="isBoardNameTaken || !newBoardName">Save</button>
        <button class="btn" @click="showBoardModal = false">Cancel</button>
      </div>
    </modal>
    <modal v-if="showColumnModal">
      <h2 class="font-bold text-lg">Add/Edit Column</h2>
      <div class="flex gap-1 items-center">
        <VSwatches v-model="columnColor" class="h-full mt-1" />
        <input type="text" v-model="columnTitle" placeholder="Enter column name"
          class="grow input input-bordered w-full"/>
        
      </div>
      <span v-if="editColumnError" class="text-error">{{ editColumnError }}</span>
      <div class="modal-action">
        <button class="btn" @click="addOrUpdateColumn">OK</button>
        <button class="btn" @click="showColumnModal = false">Cancel</button>
        <button class="btn btn-error" @click="deleteColumn">Delete</button>
        <div class="text-error text-xs" v-if="confirmDeleteColumn">
          Are you sure you want to delete this column? 
          All tasks will be removed.
        </div>
      </div>
      <div class="badge badge-error" v-if="editColumnError">{{ editColumnError }}</div>
    </modal>
    <modal v-if="showImportModalForColumn">
      <h2 class="font-bold text-lg">Import Task</h2>
      <div class="form-control">
        <label class="label cursor-pointer">
          <span class="label-text">Import from clipboard</span> 
          <input type="radio" name="importOptions" value="clipboard" v-model="importOption" class="radio" />
        </label>
        <label class="label cursor-pointer">
          <span class="label-text">Import from URL</span> 
          <input type="radio" name="importOptions" value="url" v-model="importOption" class="radio" />
        </label>
        <input v-if="importOption === 'url'" type="text" v-model="importUrl" placeholder="Paste URL here" class="input input-bordered w-full mt-2"/>
      </div>
      <div class="modal-action">
        <button class="btn" @click="confirmImportTask">Import</button>
        <button class="btn" @click="showImportModalForColumn = false">Cancel</button>
      </div>
    </modal>
  </div>
</template>

<script>
const ALL_BOARD_TITLE_ID = '$ALL'
const FILES_COLUMN = '__files__'
export default {
  data() {
    return {
      boardFilter: '',
      filter: null,
      showBoardModal: false,
      showColumnModal: false,
      newBoardType: 'manual',
      newBoardIssueLink: '',
      newBoardName: '',
      newBoardDescription: '',
      newBoardBackground: '',
      newBoardBranch: '',
      newBoardParent: null,
      columnTitle: '',
      columnColor: '#000000',
      isDropdownOpen: false,
      selectedColumn: null,
      editColumnError: null,
      columns: [],
      selectedTemplate: null,
      showChildrenBoards: false,
      editBoard: null,
      originalBoardName: null,
      filteredColumns: [],
      confirmDeleteColumn: false,
      showImportModalForColumn: null,
      importOption: 'clipboard',
      importUrl: '',
      searchVisible: false
    }
  },
  created() {
    this.projectChanged()
  },
  computed: {
    topProjects() {
      const children = this.$storex.projects.childProjects
      const parent = this.$project.parentProject
      return parent ? [parent, ...children] : children
    },
    filteredParentBoards() {
      return this.parentBoards.filter(board => 
        board.title.toLowerCase().includes(this.boardFilter.toLowerCase())
      )
    },
    board() {
      return this.$projects.activeBoard
    },
    lastUpdatedTask() {
      return this.visibleTasks.sort((a, b) => 
        (a.updated_at || new Date(1900, 1, 1)) > 
        (b.updated_at || new Date(1900, 1, 1)) ? -1 : 1)
        .slice(0, 1)[0] || {}
    },
    lastUpdatedTasks() {
      return this.chats.sort((a, b) => 
        (a.updated_at || new Date(1900, 1, 1)) > 
        (b.updated_at || new Date(1900, 1, 1)) ? -1 : 1)
        .slice(0, 3) || []
    },
    showKanban() {
      return this.kanban && this.activeKanbanBoard
    },
    kanban() {
      return this.$projects.kanban
    },
    activeKanbanBoard() {
      return this.kanban.boards[this.board]
    },
    chats() {
      const allChats = this.$projects.allChats
      return Object.values(allChats || {}).map(c => ({
        ...c,
        column: c.column || '--none--'
      }))
    },
    chat() {
      return this.$projects.activeChat
    },
    project() {
      return this.$projects.activeProject
    },
    activeBoard() {
      return this.boards[this.$projects.activeBoard]
    },
    boardColumns() {
      return this.boards[this.board]?.columns
    },
    columnList() {
      return (this.boards[this.board]?.columns?.map(c => c.title) || [])
    },
    parentBoard() {
      return this.boards[this.activeBoard?.parent_id]
    },
    boards() {
      const { kanban: { boards }, chats } = this
      return [
        ...Object.keys(boards).map(board => ({
          ...boards[board],
          id: board,
          title: board
        }))
      ].reduce((acc, b) => ({ ...acc, [b.id]: {
        ...b,
        tasks: chats.filter(c => !c.message_id && (b.id === ALL_BOARD_TITLE_ID || c.board === b.id))
      }}), {})
    },
    parentBoards() {
      return Object.values(this.boards).filter(b => !b.parent_id)
    },
    childBoards() {
      return Object.values(this.boards).filter(b => b.parent_id === this.activeBoard?.id)
    },
    visibleTasks() {
      return this.filteredColumns.reduce((a, b) => a.concat(b.tasks || []), [])
    },
    templates() {
      return this.$projects.kanbanTemplates
    },
    isBoardNameTaken() {
      return this.newBoardName && this.newBoardName !== this.originalBoardName && this.kanban.boards[this.newBoardName]
    }
  },
  watch: {
    filter(newValue, oldValue) {
      if ((!newValue && oldValue) || newValue?.length > 3) {
        this.buildKanban()
      }
    },
    project() {
      this.projectChanged()
    },
    chats(newValue, oldValue) {
      if (newValue.map(c => c.id).sort().join()
      !== oldValue.map(c => c.id).sort().join())
      this.buildColumns()
    },
    kanban() {
      this.buildKanban()
    }
  },
  methods: {
    buildFilteredColumns() {
      if (!this.filter) {
        this.filteredColumns = this.columns
      } else {
        const filterText = this.filter.toLowerCase()
        this.filteredColumns = this.columns.map(column => {
          const filteredTasks = column.tasks.filter(task => {
            const taskNameMatches = task.name.toLowerCase().includes(filterText)
            const messageContentMatches = task.messages?.some(message =>
              message.content.toLowerCase().includes(filterText)
            )
            return taskNameMatches || messageContentMatches
          })
          return { ...column, tasks: filteredTasks }
        })
      }
    },
    async projectChanged() {
      await this.$projects.loadKanban()
      this.selectBoard()
      this.buildKanban()
    },
    toggleDropdown() {
      this.isDropdownOpen = !this.isDropdownOpen
    },
    async selectBoard(board) {
      this.$projects.setActiveBoard(board)
      this.isDropdownOpen = false
      await this.$projects.loadChats()
      if (board && this.kanban.boards[board] && !this.kanban.boards[board].active) {
        Object.keys(this.kanban.boards)
          .filter(b => this.kanban.boards[b])
          .forEach(b => this.kanban.boards[b].active = (b === board))
        this.kanban.boards[board].last_update = new Date().toISOString()
        this.saveKanban()
      }
      this.buildKanban()
      this.showChildrenBoards = !!this.childBoards?.length
    },
    async editKanban(board) {
      if (!this.newBoardName.trim()) {
        return
      }
      board.title = this.newBoardName
      board.description = this.newBoardDescription
      board.background = this.newBoardBackground
      board.last_update = new Date().toISOString()
      await this.saveKanban()
    },
    async createNewChat(base) {
      return this.$projects.createNewChat({
        ...base,
        id: uuidv4(),
        board: this.board || 'Default',
      })
    },
    addNewFile() {
      this.newTask(FILES_COLUMN)
    },
    newTask(column, mode) {
      this.createNewChat({
        column,
        name: 'New Task',
        mode: mode || 'chat',
        profiles: []
      })
    },
    async importTask(column) {
      this.showImportModalForColumn = column
    },
    async confirmImportTask() {
      const column = this.activeBoard?.columns?.find(c => c.title === this.columnTitle)
      if (this.importOption === 'clipboard') {
        const clipboardContent = await navigator.clipboard.readText()
        const existingChat = JSON.parse(clipboardContent)
        const newChat = await this.createNewChat({
          ...existingChat,
          id: null,
          column
        })
        this.$projects.saveChat(newChat)
      } else if (this.importOption === 'url') {
        const chat = {
          board: this.board || 'Default',
          column: this.showImportModalForColumn,
          name: 'Import from url',
          mode: 'chat',
          url: this.importUrl
        }
        await this.$projects.createNewChatFromUrl(chat)
      }
      this.showImportModalForColumn = null
      this.importUrl = null
    },
    async buildKanban() {
      if (this.kanban) {
        this.buildColumns()
      }
    },
    buildColumns() {
      const columnTitles = this.columnList
      const cloumnChats = this.kanban.boards[this.board]?.columns?.chats || []
      this.columns = columnTitles
        .map((col, ix) => {
          const boardColumn = this.boards[this.board]?.columns?.find(bc => bc.title === col)||{}
          const getChatIndex = c => {
            return cloumnChats.findIndex(kc => kc.id === c.id)
          }
          return {
            title: col,
            ...boardColumn,
            tasks: this.activeBoard.tasks
              .filter(t => (t.column || '--none--') === col)
              .sort((a, b) => getChatIndex(a) < getChatIndex(b) ? -1 : 1),
            position: ix
          }
        }).sort((a, b) => a.position < b.position ? -1: 1)
        || []
        this.buildFilteredColumns()
    },
    async onColumnTaskListChanged() {
      if (this.$ui.isMobile) {
        return
      }
      const kboard = this.kanban.boards[this.board]
      kboard.columns = await Promise.all(this.filteredColumns.map(async (column, ix) => {
        const kcolumn = kboard.columns.find(kc => kc.id === column.id)
        kcolumn.chats = column.tasks.map(t => t.id)
        await Promise.all(column.tasks.filter(t => t.column !== column.title)
          .map(task => this.$storex.projects.saveChatInfo({ ...task, column: column.title })))
        return kcolumn
      }))
      kboard.last_update = new Date().toISOString()
      this.saveKanban()
    },
    async openChat(element) {
      if (element.id === -1) {
        this.newChat()
      } else {
        await this.$projects.setActiveChat(element)
      }
    },
    async onChatEditDone(board) {
      if (this.board !== board) {
        this.selectBoard(board)
      }
      await this.$projects.setActiveChat()
      this.buildKanban()
    },
    async createSubTask({ parent, name, description, project_id, parent_id, message_id, file_list }) {
      const chat = await this.createNewChat({
        board: parent.board,
        name,
        column: parent.column,
        parent_id: parent_id || parent.id,
        message_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list
      })
      
      this.$projects.saveChat(chat)
      if (description) {
        this.$storex.projects.chatWihProject(chat)
      }
    },
    async createSubTasks(event) {
      this.$projects.createSubtasks(event)
    },
    async addOrUpdateColumn() {
      this.columnTitle = this.columnTitle.trim()
      if (!this.columnTitle) {
        return this.resetColumnModal()
      }
      const existingColumnTitle = this.activeKanbanBoard.columns.find(c => c.title === this.columnTitle)
      if (existingColumnTitle && existingColumnTitle.id !== this.selectedColumn?.id) {
        this.editColumnError = 'Name already used'
        return
      }
      if (this.selectedColumn) {
        this.selectedColumn.title = this.columnTitle
        this.selectedColumn.color = this.columnColor
      } else {
        const newColumn = {
          id: uuidv4(),
          title: this.columnTitle,
          color: this.columnColor
        }
        this.activeBoard.columns.push(newColumn)
      }
      this.activeBoard.last_update = new Date().toISOString()
      await this.saveKanban()
      this.resetColumnModal()
      this.buildKanban()
    },
    async deleteColumn() {
      if (this.confirmDeleteColumn) {
        this.resetColumnModal()
        this.activeKanbanBoard.columns = this.activeKanbanBoard.columns.filter(
          column => column.id !== this.selectedColumn.id
        )
        await this.saveKanban()
      }
      this.confirmDeleteColumn = !this.confirmDeleteColumn
    },
    resetColumnModal() {
      this.showColumnModal = false
      this.columnTitle = ''
      this.columnColor = '#000000'
      this.selectedColumn = null
      this.editColumnError = null
    },
    async addOrUpdateBoard() {
      const oldBoardName = this.originalBoardName
      const boardName = this.newBoardName.trim()
      let board = this.editBoard ? this.kanban.boards[oldBoardName] :
                                    {
                                      title: boardName,
                                      columns: [],
                                    }
      if (this.editBoard && boardName !== this.originalBoardName) {
        delete this.kanban.boards[oldBoardName]
        board.title = boardName
        this.chats.forEach(chat => {
          if (chat.board === oldBoardName) {
            chat.board = boardName
            this.$projects.saveChatInfo(chat)
          }
        })
      }
      
      this.kanban.boards[boardName] = board 
      board.description = this.newBoardDescription?.trim()
      board.background = this.newBoardBackground?.trim()

      await this.saveKanban()
      this.showBoardModal = false
      this.resetNewBoardInfo()
      this.buildKanban()
    },
    resetNewBoardInfo () {
      this.newBoardName = ''
      this.newBoardDescription = ''
      this.newBoardBackground = ''
      this.newBoardBranch = ''
      this.selectedTemplate = null
      this.newBoardIssueLink = ''
    },
    openColumnPropertiesModal(column) {
      this.selectedColumn = this.activeKanbanBoard.columns.find(c => c.id === column.id)
      this.columnTitle = column?.title
      this.columnColor = column?.color || '#000000'
      this.showColumnModal = true
    },
    async saveKanban() {
      await this.$projects.saveKanban()
    },
    showNewBoardModal() {
      this.newBoardName = null
      this.newBoardDescription = null
      this.showBoardModal = true
    },
    taskMatchesFilter(task) {
      const filterText = this.filter?.toLowerCase() || ''
      const taskNameMatches = task.name.toLowerCase().includes(filterText)
      const messageContentMatches = task.messages?.some(message =>
        message.content.toLowerCase().includes(filterText)
      )
      return taskNameMatches || messageContentMatches
    },
    onEditBoard(board) {
      this.editBoard = board
      this.originalBoardName = board.title
      this.newBoardBackground = board.background
      this.newBoardDescription = board.description
      this.newBoardName = board.title
      this.showBoardModal = true
    },
    onDeleteBoard(board) {
      this.$projects.deleteBoard(board)
    }
  }
}
</script>