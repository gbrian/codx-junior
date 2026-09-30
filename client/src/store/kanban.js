import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { v4 as uuidv4 } from 'uuid'

export const namespaced = true

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
      acc[id] = { ...boards[id], id, title: id }
      return acc
    }, {})
  },

  allBoards: (_, getters) => {
    const { boards = {} } = getters.kanban
    return Object.keys(boards)
      .filter(title => boards[title] !== null)
      .map(title => ({
        ...boards[title],
        id: title,
        title
      }))
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
        .sort((a, b) => (a.pinned || getChatIndex(a) < getChatIndex(b) ? -1 : 1))

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

  childBoards: (state, getters) => {
    return getters.allBoards.filter(b => b.parent_id === state.activeBoard)
  },

  parentBoard: (state, getters) => {
    const active = getters.activeKanbanBoard
    return getters.allBoards.find(b => b.id === active?.parent_id) || null
  },

  parentBoardOptions: (_, getters) => getters.allBoards,

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
      const validBoard = boardName && getKanban().boards?.[boardName] ? boardName : null
      mutations.setActiveBoard(state, validBoard)
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

    async newTask({ state }, { mode, column, name, profiles, board }) {
      const chat = await $storex.chats.createNewChat({
        id: uuidv4(),
        mode: mode || 'chat',
        profiles: profiles || [],
        messages: [],
        name: name || null,
        board: board || state.activeBoard,
        column: column || null
      })
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

    async addBoard({ state }, { title, description, background, parent_id, project_id, columns }) {
      const kanban = getKanban()
      if (!kanban) return

      title = title?.trim()
      if (!title || kanban.boards?.[title]) return

      if (!kanban.boards) kanban.boards = {}
      kanban.boards[title] = {
        id: uuidv4(),
        title,
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
      if (!newName) return

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
      if (!board) return
      board.bookmark = !board.bookmark
      await $storex.kanban.saveKanban()
    },
  }
)