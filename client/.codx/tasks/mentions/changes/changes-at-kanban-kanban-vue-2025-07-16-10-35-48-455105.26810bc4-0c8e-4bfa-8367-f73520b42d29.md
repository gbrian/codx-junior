# [[{"id": "26810bc4-0c8e-4bfa-8367-f73520b42d29", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": ["skip_knowledge"], "file_list": [], "profiles": ["Vue files", "daisyui_components"], "users": [], "name": "changes-at-kanban-kanban-vue-2025-07-16-10-35-48-455105", "description": "The conversation involved altering a Vue component for a kanban board application. Key changes included adding a search input to filter parent boards, replacing basic HTML elements with DaisyUI components, and adhering to best practices for Vue files such as structuring data methods, computed properties, and methods correctly. The updated script set up import section, set default values in the data method, and ensured optimal reactivity and Vue store access using TailwindCSS for styling. Additionally, deprecated or unnecessary elements and comments were removed to streamline the component.", "created_at": "2025-07-16 10:35:43.186729", "updated_at": "2025-07-16T10:39:51.345496", "mode": "chat", "kanban_id": "", "column_id": "", "board": "mentions", "column": "changes", "chat_index": 0, "url": "", "branch": "", "file_path": "", "model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "16ca8b16-1f55-468d-8314-05ec4b8319c6", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-07-16 10:35:43.184900", "updated_at": "2025-07-16 10:35:43.184925", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false}]]

        Apply codx comments and rewrite full content.
        Return only the content without any further decoration or comments.
        Do not surround response with '```' marks, just content.
        Remove codx comments from the final version.
        Do not return the <document> tags but respect tags present of the original content.
        
## [[{"doc_id": "3bb9dcb7-e481-4aaf-82ce-79a84e51a824", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-07-16 10:35:43.184900", "updated_at": "2025-07-16 10:35:43.184925", "images": [], "files": ["/shared/codx-junior/client/src/components/kanban/Kanban.vue"], "meta_data": {}, "profiles": ["daisyui_components", "Vue files"], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false}]]

                    Given this document:
                    <document>

                    <script setup>
import draggable from "vuedraggable"
import TaskCard from "./TaskCard.vue"
import ChatViewVue from "../../views/ChatView.vue"
import { v4 as uuidv4 } from "uuid"
import VSwatches from "../VSwatches.vue"
import KanbanList from "./KanbanList.vue"
</script>

<template>
  <div class="h-full px-2" v-if="kanban?.boards">
    <div v-if="!$projects.activeChat && !board">
      <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between">
        <div>Boards Dashboard</div>
        @codx-ok, please-wait...: Add a search inptu to filter parentBoards
        <button class="btn btn-sm btn-warning btn-outline" @click="showNewBoardModal">
          New kanban
        </button>
      </h1>
      <KanbanList
        :boards="parentBoards"
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
        <div class="flex gap-2">
          <div class="grow input input-sm input-bordered flex items-center gap-2">
            <input type="text" v-model="filter" class="grow" placeholder="Search tasks" />
            <span class="cursor-pointer" v-if="filter" @click.stop="filter = ''">
              <i class="fa-regular fa-circle-xmark"></i>
            </span>
            <span v-else><i class="fa-solid fa-filter"></i></span>
          </div>
          <button class="btn btn-sm btn-outline" @click="showColumnModal = true" v-if="columnList?.length">
            <i class="fa-solid fa-plus"></i>
            <span class="text-xs md:text-md">Column</span>
          </button>
          <button class="btn btn-sm btn-warning btn-outline" @click="showChildrenBoards = !showChildrenBoards" v-if="columnList?.length">
            <i class="fa-solid fa-caret-up" v-if="showChildrenBoards"></i>
            <i class="fa-solid fa-caret-down" v-else></i>
            <span class="text-xs md:text-md">Boards</span>
          </button>
          <button class="btn btn-sm btn-info btn-outline tooltip" data-tip="Changes details"
            @click="$ui.setActiveTab('prview')">
            <i class="fa-solid fa-code-compare"></i>
            Changes
          </button>
          
        </div>
      </div>
      <div class="mt-3 grow relative">
        <button class="btn btn-sm btn-wide btn-primary" @click="showColumnModal = true" v-if="!columnList?.length">
          <i class="fa-solid fa-plus"></i>
          <span class="text-xs md:text-md">Column</span>
        </button>
        <div class="transition-all pb-2" v-if="showChildrenBoards">
          <KanbanList
            class="mb-2"
            :boards="childBoards"
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
                      <li class="flex gap-2" @click="newTask(column.title)">
                        <a>New task</a>
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
      <h2 class="font-bold text-3xl">Add New Board</h2>
      <div class="collapse">
        <input type="radio" name="newboard"  v-model="newBoardType" value="manual" />
        <div class="collapse-title text-xl font-medium"><i class="fa-solid fa-gear"></i> Manual settings</div>
        <div class="collapse-content">
          <div class="text-xl text-info font-bold" v-if="activeBoard">Parent {{ activeBoard.title }}</div>
          <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardDescription" placeholder="Enter board description" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardBranch" placeholder="Enter branch name" class="input input-bordered w-full mt-2"/>
          <select v-model="selectedTemplate" class="select select-bordered w-full mt-2">
            <option disabled value="">Select a Template</option>
            <option v-for="template in templates" :key="template.name" :value="template">{{ template.name }}</option>
          </select>
        </div>
      </div>
      <div class="collapse">
        <input type="radio" name="newboard" v-model="newBoardType" value="issue" />
        <div class="collapse-title text-xl font-medium"><i class="fa-solid fa-link"></i> From issue</div>
        <div class="collapse-content">
          <input type="text" v-model="newBoardIssueLink" placeholder="Enter isue url" class="input input-bordered w-full mt-2"/>
        </div>
      </div>

      <div class="modal-action">
        <button class="btn" @click="addBoard">OK</button>
        <button class="btn" @click="showBoardModal = false">Cancel</button>
      </div>
    </modal>
    <modal v-if="showColumnModal">
      <h2 class="font-bold text-lg">Add/Edit Column</h2>
      <div class="flex gap-1 items-center">
        <input type="text" v-model="columnTitle" placeholder="Enter column name"
          class="grow input input-bordered w-full"/>
        <VSwatches v-model="columnColor" class="h-full mt-1" />
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

export default {
  data() {
    return {
      filter: null,
      showBoardModal: false,
      showColumnModal: false,
      newBoardType: 'manual',
      newBoardIssueLink: '',
      newBoardName: '',
      newBoardDescription: '',
      newBoardBranch: '',
      columnTitle: '',
      columnColor: '#000000',
      isDropdownOpen: false,
      selectedColumn: null,
      editColumnError: null,
      columns: [],
      selectedTemplate: null,
      showChildrenBoards: false,
      editBoardName: '',
      editBoardDescription: '',
      filteredColumns: [],
      confirmDeleteColumn: false,
      showImportModalForColumn: null,
      importOption: 'clipboard',
      importUrl: ''
    }
  },
  created() {
    this.projectChanged()
  },
  computed: {
    board() {
      return this.$projects.activeBoard
    },
    lastUpdatedTask() {
      return this.visibleTasks.sort((a, b) => 
        (a.updated_at || new Date(1900, 1, 1, 0, 0, 0, 0)) > 
        (b.updated_at || new Date(1900, 1, 1, 0, 0, 0, 0)) ? -1 : 1)
        .slice(0, 1)[0] || {}
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
      return this.boards[this.board]?.columns?.map(c => c.title) || []
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
        tasks: chats.filter(c => b.id === ALL_BOARD_TITLE_ID || c.board === b.id)
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
          .forEach(b => this.kanban.boards[b].active = (b === board))
        this.saveKanban()
      }
      this.buildKanban()
      this.showChildrenBoards = !!this.childBoards?.length
    },
    async editKanban() {
      if (!this.editBoardName.trim()) {
        return
      }
      const board = this.$projects.activeBoard
      if (board) {
        board.title = this.editBoardName
        board.description = this.editBoardDescription
        await this.saveKanban(true)
      }
    },
    async createNewChat(base) {
      return this.$projects.createNewChat({
        ...base,
        id: uuidv4(),
        board: this.board || "Default",
      })
    },
    newTask(column) {
      this.createNewChat({
        column,
        name: "New Task",
        mode: 'chat',
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
      this.saveKanban(true)
    },
    async openChat(element) {
      if (element.id === -1) {
        this.newChat()
      } else {
        await this.$projects.setActiveChat(element)
      }
    },
    async onChatEditDone() {
      await this.$projects.setActiveChat()
      this.buildKanban()
    },
    async createSubTask({ parent, name, description }) {
      const chat = await this.createNewChat({
        board: parent.board,
        name,
        column: parent.column,
        parent_id: parent.id,
        project_id: parent.project_id,
        messages: [{ role: "user", content: description }]
      })
      this.$projects.saveChat(chat)
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
      await this.saveKanban(true)
      this.resetColumnModal()
      this.buildKanban()
    },
    async deleteColumn() {
      if (this.confirmDeleteColumn) {
        this.activeKanbanBoard.columns = this.activeKanbanBoard.columns.filter(
          column => column.id !== this.selectedColumn.id
        )
        await this.saveKanban(true)
        this.resetColumnModal()
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
    async addBoard() {
      if (this.newBoardType === 'issue') {
        this.$session.addInfo("Isssue")
        return
      }
      const boardName = this.newBoardName.trim()
      if (boardName && !this.boards[boardName]) {
        const selectedTemplate = this.selectedTemplate
        await this.$projects.addBoard({
          title: boardName,
          parent_id: this.activeBoard?.id,
          description: this.newBoardDescription.trim() || selectedTemplate.description,
          columns: selectedTemplate?.columns || [],
        })
      }
      this.showBoardModal = false
      this.buildKanban()
    },
    resetNewBoardInfo () {
      this.newBoardName = ''
      this.newBoardDescription = ''
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
    async saveKanban(setUpdate) {
      if (setUpdate) {
        this.activeKanbanBoard.last_update = new Date().toISOString()
      }
      await this.$projects.saveKanban()
    },
    showNewBoardModal() {
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
    onEditBoard ({ board, title, description, remote_url }) {
      const existingBoard = this.kanban.boards[board.title]
      delete this.kanban.boards[board.title]
      this.kanban.boards[title] = {
        ...existingBoard,
        title,
        description,
        remote_url
      }
      this.saveKanban()
      if (board.title === this.board) {
        this.selectBoard(title)
      }
    },
    onDeleteBoard (board) {
      this.$projects.deleteBoard(board)
    }
  }
}
</script>

                    </document>

                    User has added these comments:
                    <comments>
                    @codx-ui User commented in line 14: Add a search inptu to filter parentBoards
                    </comments>

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
            
                    
## [[{"doc_id": "bc73425f-6e2b-4e32-9c46-bf09288ba3f9", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-07-16 10:35:43.184900", "updated_at": "2025-07-16 10:35:43.184925", "images": [], "files": [], "meta_data": {"time_taken": 239.70113968849182, "first_chunk_time_taken": 0.00011706352233886719, "model": "gpt-4o"}, "profiles": ["daisyui_components", "Vue files"], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
<script setup>
import draggable from "vuedraggable"
import TaskCard from "./TaskCard.vue"
import ChatViewVue from "../../views/ChatView.vue"
import { v4 as uuidv4 } from "uuid"
import VSwatches from "../VSwatches.vue"
import KanbanList from "./KanbanList.vue"
</script>

<template>
  <div class="h-full px-2" v-if="kanban?.boards">
    <div v-if="!$projects.activeChat && !board">
      <h1 class="px-2 text-2xl font-bold mb-4 flex justify-between">
        <div>Boards Dashboard</div>
        <input type="text" v-model="boardFilter" class="input input-bordered" placeholder="Search boards" />
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
            <input type="text" v-model="filter" class="grow" placeholder="Search tasks" />
            <span class="cursor-pointer" v-if="filter" @click.stop="filter = ''">
              <i class="fa-regular fa-circle-xmark"></i>
            </span>
            <span v-else><i class="fa-solid fa-filter"></i></span>
          </div>
          <button class="btn btn-sm btn-outline" @click="showColumnModal = true" v-if="columnList?.length">
            <i class="fa-solid fa-plus"></i>
            <span class="text-xs md:text-md">Column</span>
          </button>
          <button class="btn btn-sm btn-warning btn-outline" @click="showChildrenBoards = !showChildrenBoards" v-if="columnList?.length">
            <i class="fa-solid fa-caret-up" v-if="showChildrenBoards"></i>
            <i class="fa-solid fa-caret-down" v-else></i>
            <span class="text-xs md:text-md">Boards</span>
          </button>
          <button class="btn btn-sm btn-info btn-outline tooltip" data-tip="Changes details"
            @click="$ui.setActiveTab('prview')">
            <i class="fa-solid fa-code-compare"></i>
            Changes
          </button>
        </div>
      </div>
      <div class="mt-3 grow relative">
        <button class="btn btn-sm btn-wide btn-primary" @click="showColumnModal = true" v-if="!columnList?.length">
          <i class="fa-solid fa-plus"></i>
          <span class="text-xs md:text-md">Column</span>
        </button>
        <div class="transition-all pb-2" v-if="showChildrenBoards">
          <KanbanList
            class="mb-2"
            :boards="childBoards"
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
                      <li class="flex gap-2" @click="newTask(column.title)">
                        <a>New task</a>
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
      <h2 class="font-bold text-3xl">Add New Board</h2>
      <div class="collapse">
        <input type="radio" name="newboard"  v-model="newBoardType" value="manual" />
        <div class="collapse-title text-xl font-medium"><i class="fa-solid fa-gear"></i> Manual settings</div>
        <div class="collapse-content">
          <div class="text-xl text-info font-bold" v-if="activeBoard">Parent {{ activeBoard.title }}</div>
          <input type="text" v-model="newBoardName" placeholder="Enter board name" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardDescription" placeholder="Enter board description" class="input input-bordered w-full mt-2"/>
          <input type="text" v-model="newBoardBranch" placeholder="Enter branch name" class="input input-bordered w-full mt-2"/>
          <select v-model="selectedTemplate" class="select select-bordered w-full mt-2">
            <option disabled value="">Select a Template</option>
            <option v-for="template in templates" :key="template.name" :value="template">{{ template.name }}</option>
          </select>
        </div>
      </div>
      <div class="collapse">
        <input type="radio" name="newboard" v-model="newBoardType" value="issue" />
        <div class="collapse-title text-xl font-medium"><i class="fa-solid fa-link"></i> From issue</div>
        <div class="collapse-content">
          <input type="text" v-model="newBoardIssueLink" placeholder="Enter isue url" class="input input-bordered w-full mt-2"/>
        </div>
      </div>

      <div class="modal-action">
        <button class="btn" @click="addBoard">OK</button>
        <button class="btn" @click="showBoardModal = false">Cancel</button>
      </div>
    </modal>
    <modal v-if="showColumnModal">
      <h2 class="font-bold text-lg">Add/Edit Column</h2>
      <div class="flex gap-1 items-center">
        <input type="text" v-model="columnTitle" placeholder="Enter column name"
          class="grow input input-bordered w-full"/>
        <VSwatches v-model="columnColor" class="h-full mt-1" />
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
      newBoardBranch: '',
      columnTitle: '',
      columnColor: '#000000',
      isDropdownOpen: false,
      selectedColumn: null,
      editColumnError: null,
      columns: [],
      selectedTemplate: null,
      showChildrenBoards: false,
      editBoardName: '',
      editBoardDescription: '',
      filteredColumns: [],
      confirmDeleteColumn: false,
      showImportModalForColumn: null,
      importOption: 'clipboard',
      importUrl: ''
    }
  },
  created() {
    this.projectChanged()
  },
  computed: {
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
      return this.boards[this.board]?.columns?.map(c => c.title) || []
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
        tasks: chats.filter(c => b.id === ALL_BOARD_TITLE_ID || c.board === b.id)
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
          .forEach(b => this.kanban.boards[b].active = (b === board))
        this.saveKanban()
      }
      this.buildKanban()
      this.showChildrenBoards = !!this.childBoards?.length
    },
    async editKanban() {
      if (!this.editBoardName.trim()) {
        return
      }
      const board = this.$projects.activeBoard
      if (board) {
        board.title = this.editBoardName
        board.description = this.editBoardDescription
        await this.saveKanban(true)
      }
    },
    async createNewChat(base) {
      return this.$projects.createNewChat({
        ...base,
        id: uuidv4(),
        board: this.board || "Default",
      })
    },
    newTask(column) {
      this.createNewChat({
        column,
        name: "New Task",
        mode: 'chat',
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
      this.saveKanban(true)
    },
    async openChat(element) {
      if (element.id === -1) {
        this.newChat()
      } else {
        await this.$projects.setActiveChat(element)
      }
    },
    async onChatEditDone() {
      await this.$projects.setActiveChat()
      this.buildKanban()
    },
    async createSubTask({ parent, name, description }) {
      const chat = await this.createNewChat({
        board: parent.board,
        name,
        column: parent.column,
        parent_id: parent.id,
        project_id: parent.project_id,
        messages: [{ role: "user", content: description }]
      })
      this.$projects.saveChat(chat)
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
      await this.saveKanban(true)
      this.resetColumnModal()
      this.buildKanban()
    },
    async deleteColumn() {
      if (this.confirmDeleteColumn) {
        this.activeKanbanBoard.columns = this.activeKanbanBoard.columns.filter(
          column => column.id !== this.selectedColumn.id
        )
        await this.saveKanban(true)
        this.resetColumnModal()
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
    async addBoard() {
      if (this.newBoardType === 'issue') {
        this.$session.addInfo("Isssue")
        return
      }
      const boardName = this.newBoardName.trim()
      if (boardName && !this.boards[boardName]) {
        const selectedTemplate = this.selectedTemplate
        await this.$projects.addBoard({
          title: boardName,
          parent_id: this.activeBoard?.id,
          description: this.newBoardDescription.trim() || selectedTemplate.description,
          columns: selectedTemplate?.columns || [],
        })
      }
      this.showBoardModal = false
      this.buildKanban()
    },
    resetNewBoardInfo () {
      this.newBoardName = ''
      this.newBoardDescription = ''
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
    async saveKanban(setUpdate) {
      if (setUpdate) {
        this.activeKanbanBoard.last_update = new Date().toISOString()
      }
      await this.$projects.saveKanban()
    },
    showNewBoardModal() {
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
    onEditBoard ({ board, title, description, remote_url }) {
      const existingBoard = this.kanban.boards[board.title]
      delete this.kanban.boards[board.title]
      this.kanban.boards[title] = {
        ...existingBoard,
        title,
        description,
        remote_url
      }
      this.saveKanban()
      if (board.title === this.board) {
        this.selectBoard(title)
      }
    },
    onDeleteBoard (board) {
      this.$projects.deleteBoard(board)
    }
  }
}
</script>