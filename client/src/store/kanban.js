import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { v4 as uuidv4 } from 'uuid'

export const namespaced = true

// Reserved id/title of the virtual board that groups every board-less chat.
// Boards are keyed by title, so the virtual board reuses its title as id.
export const NO_BOARD_ID = 'No board'

export const state = () => ({
  activeBoard: null,
  filter: null,
  loadingChats: 0,
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getKanban(project) {
  const targetProject = project || $storex.projects.activeProject
  return targetProject?.$state?.kanban || { boards: {} }
}

function getActiveProject(project) {
  return project || $storex.projects.activeProject
}

// ─── Getters ─────────────────────────────────────────────────────────────────

export const getters = getterTree(state, {
  kanban: () => getKanban(),

  rawBoards: () => {
    const { boards = {} } = getKanban()
    return Object.keys(boards).reduce((acc, id) => {
      acc[id] = { ...boards[id], id, title: id, type: boards[id]?.type || 'kanban' }
      return acc
    }, {})
  },

  // ── Virtual "No board" board ────────────────────────────────────────────────
  // Chats that are not associated with any board. Templates and channel-mode
  // chats are excluded because they are not real work items.
  noBoardChats: () => {
    const allChats = Object.values($storex.chats.chats || {})
    return allChats
      .filter(c => c?.id && !c.board && !c.is_template && c.mode !== 'channel')
      // Board-less chats have no column; they are grouped by task status instead
      .map(c => ({ ...c, status: c.status || 'todo' }))
  },

  // Synthetic, non-persisted board describing the board-less group. It is typed
  // as a 'sprint' so the board view renders it with the fixed status columns.
  virtualBoard: (_, getters) => {
    const chats = getters.noBoardChats
    const lastUpdate = chats.reduce((latest, c) => {
      const ts = c.updated_at || c.lastMessageAt || null
      return ts && ts > (latest || '') ? ts : latest
    }, null)

    return {
      id: NO_BOARD_ID,
      title: NO_BOARD_ID,
      type: 'sprint',
      virtual: true,
      description: 'Chats not associated with any board',
      background: '',
      parent_id: null,
      project_id: null,
      bookmark: false,
      columns: [],
      last_update: lastUpdate
    }
  },

  // Only expose the virtual board while it holds content, or while it is active
  // (so an empty picker is not cluttered and the open board never disappears).
  virtualBoards: (state, getters) => {
    if (!getters.noBoardChats.length && state.activeBoard !== NO_BOARD_ID) {
      return []
    }
    return [getters.virtualBoard]
  },

  allBoards: (_, getters) => {
    const { boards = {} } = getters.kanban
    const storedBoards = Object.keys(boards)
      .filter(title => boards[title] !== null)
      .map(title => ({
        ...boards[title],
        id: title,
        title,
        // Boards are 'kanban' unless explicitly created as a 'sprint'
        type: boards[title]?.type || 'kanban'
      }))
    // The virtual "No board" board is always appended last
    return [...storedBoards, ...getters.virtualBoards]
  },

  activeBoard: (state, getters) => {
    return getters.rawBoards[state.activeBoard] || null
  },

  activeKanbanBoard: (state, getters) => {
    if (!state.activeBoard) return null
    return getters.allBoards.find(b => b.id === state.activeBoard) || null
  },

  boardChats: (state) => {
    const allChats = Object.values($storex.chats.chats || {})
    return allChats
      .filter(c => c.board === state.activeBoard)
      .map(c => ({ ...c, column: c.column || '--none--' }))
  },

  columnList: (state, getters) => {
    const kanbanColumns = getters.activeKanbanBoard?.columns?.map(c => c.title) || []
    const chatColumns = getters.boardChats.map(c => c.column)
    return [...new Set([...kanbanColumns, ...chatColumns])]
  },

  viewColumns: (state, getters) => {
    return getters.buildViewColumns(null)
  },

  buildViewColumns: (state, getters) => (filterText) => {
    const board = getters.activeKanbanBoard
    const columnChats = board?.columns?.chats || []

    const getChatIndex = (c) => columnChats.findIndex(kc => kc.id === c.id)

    const builtColumns = getters.columnList.map((col, ix) => {
      const storeColumn = board?.columns?.find(bc => bc.title === col) || {}
      const tasks = getters.boardChats
        .filter(t => t.column === col)
        .sort((a, b) => {
          // Respect explicit sort_index if present, then fall back to pinned / chat index
          if (a.sort_index !== undefined && b.sort_index !== undefined) {
            return a.sort_index - b.sort_index
          }
          return a.pinned || getChatIndex(a) < getChatIndex(b) ? -1 : 1
        })

      const filtered = filterText
        ? tasks.filter(task =>
            Object.keys(task)
              .reduce((acc, k) => `${acc} ${JSON.stringify(task[k])}`, '')
              .toLowerCase()
              .includes(filterText.toLowerCase())
          )
        : tasks

      return {
        id: storeColumn.id || col,
        title: col,
        color: storeColumn.color || null,
        showSubTasks: storeColumn.showSubTasks,
        project_id: storeColumn.project_id || null,
        valid: !!storeColumn.id,
        position: ix,
        project: $storex.projects.allProjectsById[storeColumn.project_id] || null,
        tasks: filtered
      }
    }).sort((a, b) => (a.position < b.position ? -1 : 1))

    return builtColumns
  },

  // ── Sprint boards ──────────────────────────────────────────────────────────
  // A sprint is a board with type === 'sprint'. Its columns are FIXED and come
  // from CHAT_STATUS_CONFIG order (see chats store) — they are the task status.

  // Real sprint boards only — the virtual board must not be a switch target
  sprintBoards: (_, getters) =>
    getters.allBoards.filter(b => b.type === 'sprint' && !b.virtual),

  activeBoardType: (state, getters) =>
    getters.activeKanbanBoard?.type || 'kanban',

  isSprintBoard: (state, getters) =>
    getters.activeKanbanBoard?.type === 'sprint',

  // True when the active board is the synthetic "No board" board
  isVirtualBoard: (state, getters) =>
    !!getters.activeKanbanBoard?.virtual,

  // Tasks that belong to the active sprint (chat.sprints includes the board id).
  // The virtual board instead exposes every board-less chat.
  sprintBoardChats: (state, getters) => {
    const boardId = state.activeBoard
    if (!boardId) return []
    if (boardId === NO_BOARD_ID) return getters.noBoardChats

    const allChats = Object.values($storex.chats.chats || {})
    return allChats
      .filter(c => (c.sprints || []).includes(boardId))
      .map(c => ({ ...c, status: c.status || 'todo' }))
  },

  // One column per task status, following the canonical status order
  sprintColumns: (state, getters) => {
    const tasks = getters.sprintBoardChats
    return $storex.chats.statusList.map((status, ix) => {
      const columnTasks = tasks
        .filter(t => t.status === status.value)
        .sort((a, b) => {
          const ao = a.sort_index ?? Number.MAX_SAFE_INTEGER
          const bo = b.sort_index ?? Number.MAX_SAFE_INTEGER
          if (ao !== bo) return ao - bo
          return (a.updated_at || '') < (b.updated_at || '') ? 1 : -1
        })

      return {
        id: status.value,
        value: status.value,
        title: status.label,
        icon: status.icon,
        textColor: status.textColor,
        borderColor: status.borderColor,
        position: ix,
        tasks: columnTasks
      }
    })
  },

  childBoards: (state, getters) => {
    return getters.allBoards.filter(b => b.parent_id === state.activeBoard)
  },

  parentBoard: (state, getters) => {
    const active = getters.activeKanbanBoard
    return getters.allBoards.find(b => b.id === active?.parent_id) || null
  },

  // The virtual board can never be a parent board
  parentBoardOptions: (_, getters) => getters.allBoards.filter(b => !b.virtual),

  bookmarkedBoards: (_, getters) => getters.allBoards.filter(b => b.bookmark),

  lastUpdatedTask: (_, getters) => {
    const tasks = getters.viewColumns.reduce((a, col) => a.concat(col.tasks || []), [])
    return tasks.sort((a, b) =>
      (a.updated_at || new Date(1900, 1, 1)) > (b.updated_at || new Date(1900, 1, 1)) ? -1 : 1
    )[0] || {}
  },

  isLoading: (state) => state.loadingChats > 0,
})

// ─── Mutations ────────────────────────────────────────────────────────────────

export const mutations = mutationTree(state, {
  setActiveBoard(state, boardName) {
    state.activeBoard = boardName || null
  },

  setFilter(state, filter) {
    state.filter = filter || null
  },

  incrementLoading(state) {
    state.loadingChats += 1
  },

  decrementLoading(state) {
    state.loadingChats = Math.max(0, state.loadingChats - 1)
  },

  updateBoard(state, { boardId, updates }) {
    const kanban = getKanban()
    if (kanban.boards[boardId]) {
      kanban.boards[boardId] = {
        ...kanban.boards[boardId],
        ...updates
      }
    }
  },

  deleteBoard(state, boardId) {
    const kanban = getKanban()
    if (kanban.boards[boardId]) {
      delete kanban.boards[boardId]
    }
  },

  addColumn(state, { boardId, column }) {
    const kanban = getKanban()
    const board = kanban.boards[boardId]
    if (board) {
      board.columns = [...(board.columns || []), column]
      board.last_update = new Date().toISOString()
    }
  },

  updateColumn(state, { boardId, columnId, updates }) {
    const kanban = getKanban()
    const board = kanban.boards[boardId]
    if (board?.columns) {
      const col = board.columns.find(c => c.id === columnId || c.title === updates.title)
      if (col) {
        Object.assign(col, updates)
        board.last_update = new Date().toISOString()
      }
    }
  },

  removeColumn(state, { boardId, columnTitle }) {
    const kanban = getKanban()
    const board = kanban.boards[boardId]
    if (board?.columns) {
      board.columns = board.columns.filter(c => c.title !== columnTitle)
      board.last_update = new Date().toISOString()
    }
  },

  reorderColumns(state, { boardId, columns }) {
    const kanban = getKanban()
    const board = kanban.boards[boardId]
    if (board) {
      board.columns = columns
      board.last_update = new Date().toISOString()
    }
  },

  setColumnsChats(state, { boardId, columnChats }) {
    const kanban = getKanban()
    const board = kanban.boards[boardId]
    if (board) {
      board.columns = board.columns?.map(col => ({
        ...col,
        chats: columnChats[col.title] || col.chats || []
      })) || []
      board.last_update = new Date().toISOString()
    }
  },
})

// ─── Actions ─────────────────────────────────────────────────────────────────

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init() {
    },

    async onActiveProjectChanged() {
      // Called by projects store when activeProject changes
      mutations.setActiveBoard(state, null)
      mutations.setFilter(state, null)
      await $storex.kanban.loadKanban()
    },

    async setActiveBoard({ state }, boardName) {
      const kanban = getKanban()
      if (!kanban || !kanban.boards) {
        await $storex.kanban.loadKanban()
      }
      // The virtual "No board" board is not stored in kanban.boards, so it must
      // be accepted explicitly as a valid target.
      const isValid = !!boardName && (boardName === NO_BOARD_ID || !!getKanban().boards?.[boardName])
      mutations.setActiveBoard(state, isValid ? boardName : null)
    },

    async loadKanban({ state }, project) {
      const targetProject = getActiveProject(project)
      if (!targetProject?.$api) return
      const kanban = await targetProject.$api.chats.kanban.load()
      if (!targetProject.$state) return
      targetProject.$state.kanban = kanban
      return kanban
    },

    async saveKanban({ state }, project) {
      const targetProject = getActiveProject(project)
      if (!targetProject?.$api) return
      const data = getKanban(targetProject)
      await targetProject.$api.chats.kanban.save(data)
    },

    async addColumn({ state }, { title, color, project_id }) {
      const board = getKanban().boards?.[state.activeBoard]
      if (!board) return
      title = title?.trim()
      if (!title) return

      const exists = board.columns?.find(c => c.title === title)
      if (exists) return

      mutations.addColumn(state, {
        boardId: state.activeBoard,
        column: {
          id: uuidv4(),
          title,
          color: color || null,
          project_id: project_id || null,
          chats: []
        }
      })
      await $storex.kanban.saveKanban()
    },

    async updateColumn({ state }, { id, title, color, project_id }) {
      const board = getKanban().boards?.[state.activeBoard]
      if (!board) return

      mutations.updateColumn(state, {
        boardId: state.activeBoard,
        columnId: id,
        updates: {
          title: title?.trim(),
          color: color !== undefined ? color : undefined,
          project_id: project_id !== undefined ? project_id : undefined
        }
      })
      await $storex.kanban.saveKanban()
    },

    async deleteColumn({ state, getters }, { title }) {
      const board = getKanban().boards?.[state.activeBoard]
      if (!board) return

      const col = getters.viewColumns.find(c => c.title === title)
      if (col?.tasks?.length) {
        await Promise.all(col.tasks.map(chat => $storex.chats.deleteChat(chat)))
      }

      mutations.removeColumn(state, {
        boardId: state.activeBoard,
        columnTitle: title
      })
      await $storex.kanban.saveKanban()
    },

    async syncColumnOrder({ state, getters }, viewColumns) {
      const kanban = getKanban()
      const board = kanban.boards?.[state.activeBoard]
      if (!board) return

      const newColumns = await Promise.all(
        viewColumns.map(async (viewCol) => {
          const storeCol = getters.activeKanbanBoard?.columns?.find(
            c => c.id === viewCol.id || c.title === viewCol.title
          ) || {}

          await Promise.all(
            (viewCol.tasks || [])
              .filter(t => t.column !== viewCol.title)
              .map(task => $storex.chats.saveChatInfo({ ...task, column: viewCol.title }))
          )

          return {
            id: storeCol.id || viewCol.id,
            title: viewCol.title,
            color: storeCol.color || viewCol.color || null,
            project_id: storeCol.project_id || viewCol.project_id || null,
            showSubTasks: storeCol.showSubTasks,
            chats: (viewCol.tasks || []).map(t => t.id)
          }
        })
      )

      mutations.reorderColumns(state, {
        boardId: state.activeBoard,
        columns: newColumns
      })
      await $storex.kanban.saveKanban()
    },

    async moveTask({ state, getters }, { taskId, toColumn }) {
      const task = getters.boardChats.find(t => t.id === taskId)
      if (!task) return
      await $storex.chats.saveChatInfo({ ...task, column: toColumn })
    },

    // Persist a new task order within a column using sort_index on each chat
    async reorderTasksInColumn({ state, getters }, { columnTitle, taskIds }) {
      const tasks = getters.boardChats.filter(t => t.column === columnTitle)
      await Promise.all(
        taskIds.map((id, index) => {
          const task = tasks.find(t => t.id === id)
          if (!task) return Promise.resolve()
          return $storex.chats.saveChatInfo({ ...task, sort_index: index })
        })
      )
    },

    async newTask({ state }, { mode, column, name, profiles, board, llm_model }) {
      const activeProject = $storex.projects.activeProject
      const chat = await $storex.chats.createNewChat({
        id: uuidv4(),
        mode: mode || 'chat',
        profiles: profiles || [],
        messages: [],
        name: name || null,
        board: board || state.activeBoard,
        column: column || null,
        llm_model: llm_model || null,
        owner_project_id: activeProject?.project_id || null,
      })
      return chat
    },

    // ── Sprint actions ───────────────────────────────────────────────────────

    // Create a board of type 'sprint' (columns are implicit statuses)
    async createSprintBoard({ state }, { title, description } = {}) {
      return $storex.kanban.addBoard({
        title,
        description,
        type: 'sprint'
      })
    },

    // Move a task across sprint columns → writes chat.status (NOT chat.column).
    // Works for the virtual board too: it just re-groups the orphan chat.
    async moveSprintStatus({ state }, { taskId, status } = {}) {
      if (!taskId || !status) return
      const chat = $storex.chats.chats?.[taskId]
      if (!chat) return
      if ((chat.status || 'todo') === status) return
      await $storex.chats.updateChatInfo({ chat, updates: { status } })
    },

    // Add existing tasks to the active sprint (adds the board id to chat.sprints)
    async addTasksToSprint({ state }, { taskIds } = {}) {
      const sprintId = state.activeBoard
      // The virtual board is a catch-all, not a sprint — it cannot be joined
      if (!sprintId || sprintId === NO_BOARD_ID || !taskIds?.length) return

      await Promise.all(taskIds.map(async (id) => {
        const chat = $storex.chats.chats?.[id]
        if (!chat) return
        if ((chat.sprints || []).includes(sprintId)) return
        const sprints = Array.from(new Set([...(chat.sprints || []), sprintId]))
        await $storex.chats.updateChatInfo({ chat, updates: { sprints } })
      }))
    },

    // Remove a task from the active sprint (keeps the task itself)
    async removeTaskFromSprint({ state }, { taskId } = {}) {
      const sprintId = state.activeBoard
      const chat = $storex.chats.chats?.[taskId]
      // The virtual board has no membership to remove
      if (!sprintId || sprintId === NO_BOARD_ID || !chat) return
      const sprints = (chat.sprints || []).filter(id => id !== sprintId)
      await $storex.chats.updateChatInfo({ chat, updates: { sprints } })
    },

    // Create a task (or subtask) directly on the active sprint, in its first column
    async newSprintTask({ state, getters }, { name, status, mode, profiles, project_id, llm_model, parentId } = {}) {
      const sprintId = state.activeBoard

      // The virtual "No board" board is read-only: it surfaces existing orphan
      // chats, it must not create sprint tasks. Board/column are required by the
      // backend, so creation is disabled for it at the UI level too.
      if (sprintId === NO_BOARD_ID) return null

      const activeProject = $storex.projects.activeProject
      const parentChat = parentId ? $storex.chats.chats?.[parentId] : null

      const taskStatus = status || 'todo'

      // The sprint board's columns are its task statuses; the first column is
      // the default landing column (To Do). Subtasks inherit board/column from
      // their parent.
      const firstColumn = getters.sprintColumns?.[0]

      // `board` and `column` are required by the backend and must be part of the
      // create payload (before the chat is saved via PUT /api/chats?chat_only=1).
      // Root tasks fall back to this sprint board and its first column so the
      // create never sends null.
      const board = parentChat?.board || sprintId || null
      const column = parentChat?.column || firstColumn?.title || taskStatus

      const chat = await $storex.chats.createNewChat({
        id: uuidv4(),
        mode: mode || parentChat?.mode || 'chat',
        profiles: profiles || [],
        messages: [],
        name: name || null,
        status: taskStatus,
        sprints: [sprintId],
        parent_id: parentChat?.id || null,
        board,
        column,
        llm_model: llm_model || null,
        owner_project_id: parentChat?.owner_project_id || activeProject?.project_id || null,
        project_id: project_id || parentChat?.project_id,
      })

      // Defensive: guarantee membership/status via the metadata endpoint even if
      // the create payload path ignored those fields.
      if (chat?.id) {
        await $storex.chats.updateChatInfo({
          chat,
          updates: { sprints: [sprintId], status: taskStatus, board, column }
        })
      }
      return chat
    },

    async createSubTask({ state }, {
      parent, name, mode, description, project_id, parent_id,
      message_id, file_list, activateChat, child_index, column, profiles
    }) {
      const chat = await $storex.chats.createNewChat({
        id: uuidv4(),
        board: parent.board,
        name,
        mode,
        profiles: profiles || [],
        column: column || parent.column,
        parent_id: parent_id || parent.id,
        message_id,
        project_id: project_id || parent.project_id,
        owner_project_id: parent.owner_project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list,
        child_index
      })

      if (activateChat !== false) {
        await $storex.chats.setActiveChat(chat)
      }

      await $storex.chats.saveChat(chat)
      if (description) $storex.projects.chatWihProject(chat)
      return chat
    },

    async addBoard({ state }, { title, description, background, parent_id, project_id, columns, type }) {
      const kanban = getKanban()
      if (!kanban) return

      title = title?.trim()
      // The virtual board id/title is reserved
      if (!title || title === NO_BOARD_ID || kanban.boards?.[title]) return

      if (!kanban.boards) kanban.boards = {}
      kanban.boards[title] = {
        id: uuidv4(),
        title,
        type: type || 'kanban',
        description: description || '',
        background: background || '',
        parent_id: parent_id || null,
        project_id: project_id || null,
        columns: columns || [],
        last_update: new Date().toISOString()
      }

      await $storex.kanban.saveKanban()
      mutations.setActiveBoard(state, title)
      return kanban.boards[title]
    },

    async saveBoard({ state }, { originalTitle, board }) {
      const kanban = getKanban()
      const oldName = originalTitle
      const newName = board.title?.trim()
      // The virtual board id/title is reserved and cannot be taken over
      if (!newName || newName === NO_BOARD_ID) return

      // Preserve board type (kanban | sprint) across edits and renames
      const boardType = board.type
        || kanban.boards?.[oldName]?.type
        || kanban.boards?.[newName]?.type
        || 'kanban'

      if (oldName && oldName !== newName) {
        const allChats = Object.values($storex.chats.chats || {})
        await Promise.all(
          allChats
            .filter(c => c.board === oldName)
            .map(c => $storex.chats.saveChatInfo({ ...c, board: newName }))
        )
        delete kanban.boards[oldName]
        Object.values(kanban.boards)
          .filter(b => b && b.parent_id === oldName)
          .forEach(b => (b.parent_id = newName))
      }

      kanban.boards[newName] = {
        ...kanban.boards[newName],
        title: newName,
        type: boardType,
        description: board.description || '',
        background: board.background || '',
        parent_id: board.parent_id || null,
        project_id: board.project_id || null
      }

      await $storex.kanban.saveKanban()

      if (oldName && oldName !== newName && state.activeBoard === oldName) {
        mutations.setActiveBoard(state, newName)
      }
    },

    async deleteBoard({ state }, board) {
      const kanban = getKanban()
      const boardTitle = board?.title || board
      if (!boardTitle || !kanban.boards?.[boardTitle]) return

      const boardChats = Object.values($storex.chats.chats || {})
        .filter(c => c.board === boardTitle)
      await Promise.all(boardChats.map(c => $storex.chats.deleteChat(c)))

      const childBoardsList = Object.values(kanban.boards)
        .filter(b => b && b.parent_id === boardTitle)
      for (const child of childBoardsList) {
        await $storex.kanban.deleteBoard(child)
      }

      mutations.deleteBoard(state, boardTitle)
      await $storex.kanban.saveKanban()

      if (state.activeBoard === boardTitle) {
        const fallback = board.parent_id || Object.keys(kanban.boards).find(k => kanban.boards[k] !== null) || null
        mutations.setActiveBoard(state, fallback)
      }
    },

    async toggleBookmark({ state }, boardTitle) {
      const kanban = getKanban()
      const board = kanban.boards?.[boardTitle || state.activeBoard]
      // Guarded: the virtual board is not stored, so this is a no-op for it
      if (!board) return
      board.bookmark = !board.bookmark
      await $storex.kanban.saveKanban()
    },
  }
)