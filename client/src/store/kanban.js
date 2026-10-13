import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { v4 as uuidv4 } from 'uuid'

export const namespaced = true

// Reserved id/title of the virtual board that groups every board-less chat.
// Boards are keyed by title, so the virtual board reuses its title as id.
export const NO_BOARD_ID = 'No board'

// Portable board document contract used by export/import.
export const BOARD_EXPORT_FORMAT = 'codx-junior-board'
export const BOARD_EXPORT_VERSION = 1

export const state = () => ({
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

// ─── Board export / import helpers ────────────────────────────────────────────

// Normalize a filesystem path (drop a trailing slash) for prefix comparison.
function normalizeProjectPath(path) {
  if (!path) return path
  return path.endsWith('/') ? path.slice(0, -1) : path
}

/**
 * Rewrite an absolute path that points inside the *source* project so it points
 * inside the *target* project instead. Paths outside the source project are
 * returned untouched, so shared/external references survive the import.
 */
function remapProjectPath(path, sourcePath, targetPath) {
  if (!path || !sourcePath || !targetPath) return path
  const source = normalizeProjectPath(sourcePath)
  const target = normalizeProjectPath(targetPath)
  if (path === source) return target
  if (path.startsWith(`${source}/`)) return `${target}${path.slice(source.length)}`
  return path
}

function remapPathList(list, sourcePath, targetPath) {
  if (!Array.isArray(list)) return []
  return list.map(path => remapProjectPath(path, sourcePath, targetPath))
}

// A board key/title that is free in the target project ("Title", "Title (2)"…).
function findFreeBoardTitle(kanban, baseTitle) {
  const boards = kanban.boards || {}
  const clean = (baseTitle || 'Imported board').trim() || 'Imported board'
  if (clean !== NO_BOARD_ID && !boards[clean]) return clean
  let index = 2
  let candidate = `${clean} (${index})`
  while (boards[candidate]) {
    index += 1
    candidate = `${clean} (${index})`
  }
  return candidate
}

/**
 * Adapt one exported chat to the import target project.
 *
 * EVERY field that is bound to the project the chat was created in is
 * retargeted here:
 *  - owner_project_id / project_id                 -> target project
 *  - parent_id / linked_chat_ids / chat_links       -> remapped new chat ids
 *  - absolute file paths (file_list + message files)-> target project root
 *  - board / sprint membership                      -> the imported board
 *  - session_id (AI log link of the source project) -> cleared
 */
function adaptImportedChat({
  sourceChat,
  idMap,
  boardTitle,
  boardType,
  projectId,
  columnTitles,
  sourcePath,
  targetPath
}) {
  // Deep clone so in-memory store objects are never mutated by the import.
  const chat = JSON.parse(JSON.stringify(sourceChat))

  delete chat.file_path
  chat.session_id = null

  chat.id = idMap[sourceChat.id]
  chat.owner_project_id = projectId
  chat.project_id = projectId

  // Inter-task links (parent/child + threads) between imported chats only.
  chat.parent_id = sourceChat.parent_id ? (idMap[sourceChat.parent_id] || null) : null
  chat.parent_owner_project_id = sourceChat.parent_id ? projectId : null
  chat.parent_project_id = sourceChat.parent_id ? projectId : null
  chat.message_id = sourceChat.message_id || null

  // Board / sprint membership.
  chat.board = boardTitle
  if (boardType === 'sprint') {
    chat.sprints = [boardTitle]
    chat.status = sourceChat.status || 'todo'
  } else {
    // Kanban tasks drop foreign sprint membership (only this board is imported)
    chat.sprints = []
    // Resolve the destination column to one that exists on the imported board.
    chat.column = columnTitles.includes(sourceChat.column)
      ? sourceChat.column
      : (columnTitles[0] || 'tasks')
  }

  // Cross-chat links.
  chat.linked_chat_ids = (sourceChat.linked_chat_ids || [])
    .map(id => idMap[id])
    .filter(Boolean)
  chat.chat_links = (sourceChat.chat_links || [])
    .map(link => ({ chat_id: idMap[link.chat_id], project_id: projectId }))
    .filter(link => link.chat_id)

  // Project-bound file references.
  chat.file_list = remapPathList(sourceChat.file_list, sourcePath, targetPath)
  chat.messages = (sourceChat.messages || []).map(message => ({
    ...message,
    files: remapPathList(message.files, sourcePath, targetPath)
  }))

  return chat
}

// Link imported kanban tasks into their board column. Sprint membership is
// already carried on the chat (`sprints`), so sprint boards are skipped.
function linkChatsToColumns(board, imported) {
  if (!board) return
  const columnByTitle = {}
  ;(board.columns || []).forEach(col => { columnByTitle[col.title] = col })

  imported.forEach(({ chat }) => {
    const columnTitle = chat.column || 'tasks'
    let column = columnByTitle[columnTitle]
    if (!column) {
      column = {
        id: uuidv4(),
        title: columnTitle,
        color: null,
        // Profiles tasks created in this column should inherit
        profiles: [],
        project_id: board.project_id,
        chats: []
      }
      board.columns = [...(board.columns || []), column]
      columnByTitle[columnTitle] = column
    }
    if (!(column.chats || []).includes(chat.id)) {
      column.chats = [...(column.chats || []), chat.id]
    }
  })
}

// ─── Sprint column helpers ────────────────────────────────────────────────────

// Default sprint columns mirror the canonical task statuses. They are the
// fallback for boards that were never customized (and for the virtual
// "No board" board). Once a board's columns are edited they are persisted on
// `board.columns`, each one carrying the chat `status` it groups (and an
// optional Font Awesome `icon`).
function defaultSprintColumns() {
  return $storex.chats.statusList.map(status => ({
    id: status.value,
    title: status.label,
    icon: status.icon,
    color: null,
    profiles: [],
    status: status.value
  }))
}

// The chat status a sprint column writes: the explicit `status`, or the UI
// `title` when no status was defined.
function sprintColumnStatus(column) {
  return column?.status || column?.title
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
      users: [],
      columns: [],
      last_update: lastUpdate
    }
  },

  // Only expose the virtual board while it holds content. The active board now
  // lives in the components, so the store no longer needs to keep it listed
  // just because it is selected (boardById resolves it either way).
  virtualBoards: (state, getters) => {
    return getters.noBoardChats.length ? [getters.virtualBoard] : []
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
        type: boards[title]?.type || 'kanban',
        // Board participants (user list) — optional
        users: boards[title]?.users || []
      }))
    // The virtual "No board" board is always appended last
    return [...storedBoards, ...getters.virtualBoards]
  },

  // Resolve a board by its id/title. The virtual "No board" board always
  // resolves (even with no chats) so a component can keep it selected.
  boardById: (state, getters) => (boardId) => {
    if (!boardId) return null
    if (boardId === NO_BOARD_ID) return getters.virtualBoard
    return getters.allBoards.find(b => b.id === boardId) || null
  },

  isVirtualBoard: (state, getters) => (boardId) => boardId === NO_BOARD_ID,

  isSprintBoard: (state, getters) => (boardId) =>
    getters.boardById(boardId)?.type === 'sprint',

  boardType: (state, getters) => (boardId) =>
    getters.boardById(boardId)?.type || 'kanban',

  // Tasks that belong to a board (chat.board === boardId). The virtual board
  // instead exposes every board-less chat.
  boardChats: (state, getters) => (boardId) => {
    if (!boardId) return []
    if (boardId === NO_BOARD_ID) {
      return getters.noBoardChats.map(c => ({ ...c, column: c.column || '--none--' }))
    }
    const allChats = Object.values($storex.chats.chats || {})
    return allChats
      .filter(c => c.board === boardId)
      .map(c => ({ ...c, column: c.column || '--none--' }))
  },

  columnList: (state, getters) => (boardId) => {
    const kanbanColumns = getters.boardById(boardId)?.columns?.map(c => c.title) || []
    const chatColumns = getters.boardChats(boardId).map(c => c.column)
    return [...new Set([...kanbanColumns, ...chatColumns])]
  },

  // Build the kanban columns (with their tasks) for a board.
  buildViewColumns: (state, getters) => (boardId, filterText) => {
    const board = getters.boardById(boardId)
    const columnChats = board?.columns?.chats || []

    const getChatIndex = (c) => columnChats.findIndex(kc => kc.id === c.id)

    const builtColumns = getters.columnList(boardId).map((col, ix) => {
      const storeColumn = board?.columns?.find(bc => bc.title === col) || {}
      const tasks = getters.boardChats(boardId)
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
        // Profiles tasks created in this column inherit by default
        profiles: storeColumn.profiles || [],
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
  // A sprint is a board with type === 'sprint'. Its columns map a UI `title`, an
  // `icon` and a `color` to the chat `status` they group; boards that were never
  // edited (and the virtual board) fall back to the canonical status order.

  // Real sprint boards only — the virtual board must not be a switch target
  sprintBoards: (_, getters) =>
    getters.allBoards.filter(b => b.type === 'sprint' && !b.virtual),

  // Tasks that belong to a sprint (chat.sprints includes the board id).
  sprintBoardChats: (state, getters) => (boardId) => {
    if (!boardId) return []
    if (boardId === NO_BOARD_ID) return getters.noBoardChats

    const allChats = Object.values($storex.chats.chats || {})
    return allChats
      .filter(c => (c.sprints || []).includes(boardId))
      .map(c => ({ ...c, status: c.status || 'todo' }))
  },

  // The sprint columns for a board. Customized boards persist their columns on
  // `board.columns` ({ id, title, icon, color, status }); boards that were never
  // edited (and the virtual board) fall back to the canonical statuses.
  //
  // Sprint boards work by changing a task's `status` field, so each column
  // groups every task whose `status` matches the column `status` (or its
  // `title` when no status was defined).
  sprintColumns: (state, getters) => (boardId) => {
    const board = getters.boardById(boardId)
    const tasks = getters.sprintBoardChats(boardId)

    const custom = board?.columns?.length ? board.columns : null
    const columns = custom || defaultSprintColumns()

    return columns.map((col, ix) => {
      // The chat status this column groups (falls back to the UI title)
      const status = sprintColumnStatus(col)
      const isStatus = $storex.chats.statusList.some(s => s.value === status)
      const config = $storex.chats.statusConfig(status)

      const columnTasks = tasks
        .filter(t => t.status === status)
        .sort((a, b) => {
          const ao = a.sort_index ?? Number.MAX_SAFE_INTEGER
          const bo = b.sort_index ?? Number.MAX_SAFE_INTEGER
          if (ao !== bo) return ao - bo
          return (a.updated_at || '') < (b.updated_at || '') ? 1 : -1
        })

      return {
        id: col.id || status,
        status,
        title: col.title || config.label,
        // A custom icon wins; canonical statuses otherwise keep their icon.
        // Columns without an icon fall back to the colour dot (board column).
        icon: col.icon || (isStatus ? config.icon : null),
        textColor: isStatus ? config.textColor : null,
        borderColor: isStatus ? config.borderColor : null,
        color: col.color || null,
        // Profiles tasks created in this column inherit by default
        profiles: col.profiles || [],
        position: ix,
        tasks: columnTasks
      }
    })
  },

  childBoards: (state, getters) => (boardId) =>
    getters.allBoards.filter(b => b.parent_id === boardId),

  parentBoard: (state, getters) => (boardId) => {
    const board = getters.boardById(boardId)
    if (!board?.parent_id) return null
    return getters.allBoards.find(b => b.id === board.parent_id) || null
  },

  // The virtual board can never be a parent board
  parentBoardOptions: (_, getters) => getters.allBoards.filter(b => !b.virtual),

  bookmarkedBoards: (_, getters) => getters.allBoards.filter(b => b.bookmark),

  isLoading: (state) => state.loadingChats > 0,
})

// ─── Mutations ────────────────────────────────────────────────────────────────

export const mutations = mutationTree(state, {
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
      mutations.setFilter(state, null)
      await $storex.kanban.loadKanban()
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

    async addColumn({ state }, { boardId, title, color, project_id, profiles }) {
      const board = getKanban().boards?.[boardId]
      if (!board) return
      title = title?.trim()
      if (!title) return

      const exists = board.columns?.find(c => c.title === title)
      if (exists) return

      mutations.addColumn(state, {
        boardId,
        column: {
          id: uuidv4(),
          title,
          color: color || null,
          // Profiles tasks created in this column inherit by default
          profiles: profiles || [],
          project_id: project_id || null,
          chats: []
        }
      })
      await $storex.kanban.saveKanban()
    },

    async updateColumn({ state }, { boardId, id, title, color, project_id, profiles }) {
      const board = getKanban().boards?.[boardId]
      if (!board) return

      const updates = {
        title: title?.trim(),
        color: color !== undefined ? color : undefined,
        project_id: project_id !== undefined ? project_id : undefined
      }
      // Only touch `profiles` when the caller provides it, so an unrelated
      // column update never wipes the profiles the column defines.
      if (profiles !== undefined) updates.profiles = profiles

      mutations.updateColumn(state, {
        boardId,
        columnId: id,
        updates
      })
      await $storex.kanban.saveKanban()
    },

    async deleteColumn({ state, getters }, { boardId, title }) {
      const board = getKanban().boards?.[boardId]
      if (!board) return

      const col = getters.buildViewColumns(boardId, null).find(c => c.title === title)
      if (col?.tasks?.length) {
        await Promise.all(col.tasks.map(chat => $storex.chats.deleteChat(chat)))
      }

      mutations.removeColumn(state, {
        boardId,
        columnTitle: title
      })
      await $storex.kanban.saveKanban()
    },

    async syncColumnOrder({ state, getters }, { boardId, viewColumns }) {
      const kanban = getKanban()
      const board = kanban.boards?.[boardId]
      if (!board) return

      const newColumns = await Promise.all(
        viewColumns.map(async (viewCol) => {
          const storeCol = getters.boardById(boardId)?.columns?.find(
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
            // Keep the profiles tasks created in this column inherit
            profiles: storeCol.profiles || viewCol.profiles || [],
            project_id: storeCol.project_id || viewCol.project_id || null,
            showSubTasks: storeCol.showSubTasks,
            chats: (viewCol.tasks || []).map(t => t.id)
          }
        })
      )

      mutations.reorderColumns(state, {
        boardId,
        columns: newColumns
      })
      await $storex.kanban.saveKanban()
    },

    // Persist a new column ORDER for a SPRINT board.
    //
    // Sprint columns live on `board.columns` ({ id, title, icon, color, status })
    // and group their tasks by the chat `status` they map to, so the kanban
    // `syncColumnOrder` cannot be reused here: no task has to move between
    // columns, only the column order itself changes.
    async syncSprintColumnOrder({ state }, { boardId, columns } = {}) {
      const board = getKanban().boards?.[boardId]
      if (!board || !columns?.length) return

      // Boards that were never customized keep their columns in code, so the
      // canonical statuses are materialized first (this gives them stable ids
      // and makes the chosen order survive a reload).
      if (!board.columns?.length) {
        await $storex.kanban.materializeSprintColumns({ boardId })
      }

      const stored = board.columns || []
      const reordered = []
      // Map the reordered view columns (id / status / title) back to their
      // persisted configuration, keeping every extra stored field.
      columns.forEach(col => {
        const storedCol = stored.find(c =>
          (col.id && c.id === col.id) ||
          (col.status && sprintColumnStatus(c) === col.status) ||
          (col.title && c.title === col.title)
        )
        if (storedCol && !reordered.includes(storedCol)) reordered.push(storedCol)
      })
      // Never drop a column: anything missing from the view keeps its position
      stored.forEach(col => {
        if (!reordered.includes(col)) reordered.push(col)
      })
      if (!reordered.length) return

      // The mutation signature is (state, payload), so `state` MUST be passed as
      // the first argument. Omitting it makes the payload land in `state` and the
      // destructuring of `{ boardId, columns }` throw, aborting the action before
      // the board is written and saved (the reorder then reverts on reload).
      mutations.reorderColumns(state, { boardId, columns: reordered })
      await $storex.kanban.saveKanban()
    },

    async moveTask({ state }, { taskId, toColumn }) {
      const task = $storex.chats.chats?.[taskId]
      if (!task) return
      await $storex.chats.saveChatInfo({ ...task, column: toColumn })
    },

    // Persist a new task order within a column using sort_index on each chat
    async reorderTasksInColumn({ state, getters }, { boardId, columnTitle, taskIds }) {
      const tasks = getters.boardChats(boardId).filter(t => t.column === columnTitle)
      await Promise.all(
        taskIds.map((id, index) => {
          const task = tasks.find(t => t.id === id)
          if (!task) return Promise.resolve()
          return $storex.chats.saveChatInfo({ ...task, sort_index: index })
        })
      )
    },

    async newTask({ state }, { mode, column, name, profiles, board, llm_model, parentId, project_id }) {
      const activeProject = $storex.projects.activeProject
      const parentChat = parentId ? $storex.chats.chats?.[parentId] : null
      const chat = await $storex.chats.createNewChat({
        id: uuidv4(),
        mode: mode || parentChat?.mode || 'chat',
        profiles: profiles || [],
        messages: [],
        name: name || null,
        board: board || parentChat?.board || null,
        column: column || parentChat?.column || null,
        parent_id: parentChat?.id || null,
        project_id: project_id || parentChat?.project_id || null,
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

    // Add existing tasks to a sprint (adds the board id to chat.sprints)
    async addTasksToSprint({ state }, { taskIds, sprintId } = {}) {
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

    // Remove a task from a sprint (keeps the task itself)
    async removeTaskFromSprint({ state }, { taskId, sprintId } = {}) {
      const chat = $storex.chats.chats?.[taskId]
      // The virtual board has no membership to remove
      if (!sprintId || sprintId === NO_BOARD_ID || !chat) return
      const sprints = (chat.sprints || []).filter(id => id !== sprintId)
      await $storex.chats.updateChatInfo({ chat, updates: { sprints } })
    },

    // Create a task (or subtask) directly on a sprint, in its first column
    async newSprintTask({ state, getters }, { name, status, mode, profiles, project_id, llm_model, parentId, sprintId } = {}) {
      // The virtual "No board" board is read-only: it surfaces existing orphan
      // chats, it must not create sprint tasks. Board/column are required by the
      // backend, so creation is disabled for it at the UI level too.
      if (!sprintId || sprintId === NO_BOARD_ID) return null

      const activeProject = $storex.projects.activeProject
      const parentChat = parentId ? $storex.chats.chats?.[parentId] : null

      // The sprint board's columns are its task statuses; the first column is
      // the default landing column. Subtasks inherit board/column from the
      // parent, root tasks fall back to the first column's status.
      const firstColumn = getters.sprintColumns(sprintId)?.[0]
      const taskStatus = status || firstColumn?.status || 'todo'

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

    // ── Sprint columns (add / edit / remove) ─────────────────────────────────
    // Sprint columns are stored on `board.columns` as
    // { id, title, icon, color, status } where `status` is the chat.status the
    // column groups (it falls back to the title when omitted) and `icon` is an
    // optional Font Awesome class. Boards without stored columns fall back to the
    // canonical statuses, so the defaults are materialized before any edit.

    async materializeSprintColumns({ state }, { boardId } = {}) {
      const board = getKanban().boards?.[boardId]
      if (!board || board.columns?.length) return board

      // `id` mirrors the status value so a column's identity is stable across
      // the fallback → persisted transition (keeps canvas reorder in sync).
      board.columns = defaultSprintColumns().map(col => ({
        id: col.id,
        title: col.title,
        icon: col.icon || null,
        color: col.color || null,
        // Profiles tasks created in this column inherit by default
        profiles: col.profiles || [],
        status: col.status,
        chats: []
      }))
      board.last_update = new Date().toISOString()
      await $storex.kanban.saveKanban()
      return board
    },

    // Add a column: `title` labels it in the UI, `status` is the chat status its
    // tasks get (defaults to the title when omitted) and `icon` is optional.
    async addSprintColumn({ state }, { boardId, title, status, icon, color, profiles } = {}) {
      const board = getKanban().boards?.[boardId]
      if (!board) return
      title = title?.trim()
      if (!title) return
      const columnStatus = status?.trim() || title

      // Keep the existing (default) columns before appending the new one
      await $storex.kanban.materializeSprintColumns({ boardId })

      // Two columns must not write the same chat status (the same tasks would
      // be listed twice). The dialog validates this too — this is the guard.
      if (board.columns.some(c => sprintColumnStatus(c) === columnStatus)) return

      board.columns = [
        ...(board.columns || []),
        {
          id: uuidv4(),
          title,
          icon: icon || null,
          color: color || null,
          // Profiles tasks created in this column inherit by default
          profiles: profiles || [],
          status: columnStatus,
          chats: []
        }
      ]
      board.last_update = new Date().toISOString()
      await $storex.kanban.saveKanban()
    },

    // Update a column (title / status / icon / color / profiles). Changing the
    // status a column writes migrates its tasks so the cards follow the column.
    async updateSprintColumn({ state, getters }, { boardId, id, title, icon, color, status, profiles } = {}) {
      const board = getKanban().boards?.[boardId]
      if (!board) return

      // Default columns are persisted on first edit (boards start column-less)
      await $storex.kanban.materializeSprintColumns({ boardId })

      const column = board.columns.find(c =>
        c.id === id || sprintColumnStatus(c) === id || c.title === id)
      if (!column) return

      const previousStatus = sprintColumnStatus(column)
      const nextTitle = title !== undefined ? (title?.trim() || column.title) : column.title
      // An explicit status wins; otherwise fall back to the (new) title
      const nextStatus = status !== undefined
        ? (status?.trim() || nextTitle)
        : (column.status || nextTitle)

      // Changing the status re-groups the column, so move its tasks along
      if (nextStatus !== previousStatus) {
        const tasks = getters.sprintBoardChats(boardId)
          .filter(t => (t.status || 'todo') === previousStatus)
        await Promise.all(tasks.map(t =>
          $storex.chats.updateChatInfo({ chat: t, updates: { status: nextStatus } })
        ))
      }

      column.title = nextTitle
      column.status = nextStatus
      if (icon !== undefined) column.icon = icon || null
      if (color !== undefined) column.color = color || null
      // Only touch `profiles` when the caller provides it
      if (profiles !== undefined) column.profiles = profiles || []
      board.last_update = new Date().toISOString()
      await $storex.kanban.saveKanban()
    },

    async removeSprintColumn({ state, getters }, { boardId, id, reassignTo } = {}) {
      const board = getKanban().boards?.[boardId]
      if (!board) return

      // Default columns are persisted on first edit (boards start column-less)
      await $storex.kanban.materializeSprintColumns({ boardId })
      // A board must keep at least one column
      if (board.columns.length <= 1) return

      const column = board.columns.find(c =>
        c.id === id || sprintColumnStatus(c) === id || c.title === id)
      if (!column) return

      const status = sprintColumnStatus(column)
      const remaining = board.columns.filter(c => c !== column)
      // Where the column's tasks go: the requested target or the first column left
      const target = remaining.find(c => sprintColumnStatus(c) === reassignTo) || remaining[0]
      const targetStatus = sprintColumnStatus(target)

      // Move the tasks so the removed column never loses them
      const tasks = getters.sprintBoardChats(boardId)
        .filter(t => (t.status || 'todo') === status)
      await Promise.all(tasks.map(t =>
        $storex.chats.updateChatInfo({ chat: t, updates: { status: targetStatus } })
      ))

      board.columns = remaining
      board.last_update = new Date().toISOString()
      await $storex.kanban.saveKanban()
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

    async addBoard({ state }, { title, description, background, parent_id, project_id, columns, type, users }) {
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
        users: users || [],
        columns: columns || [],
        last_update: new Date().toISOString()
      }

      await $storex.kanban.saveKanban()
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
        // Do not silently overwrite an existing board
        if (kanban.boards?.[newName]) return
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

      const existing = kanban.boards[newName] || {}
      kanban.boards[newName] = {
        ...existing,
        title: newName,
        type: boardType,
        description: board.description !== undefined ? board.description : (existing.description || ''),
        background: board.background !== undefined ? board.background : (existing.background || ''),
        parent_id: board.parent_id !== undefined ? board.parent_id : (existing.parent_id || null),
        project_id: board.project_id !== undefined ? board.project_id : (existing.project_id || null),
        users: board.users !== undefined ? board.users : (existing.users || [])
      }

      await $storex.kanban.saveKanban()
    },

    /**
     * Delete a board (kanban or sprint).
     *
     * @param {object} payload
     * @param {object|string} payload.board  Board object (or its id/title).
     * @param {boolean} [payload.deleteChats=true]  When true, the board's tasks
     *   are deleted from the project. When false they are kept and DETACHED
     *   from the board:
     *     - kanban: `board` and `column` are cleared (they fall back to the
     *       virtual "No board" board);
     *     - sprint: the board id is removed from each task's `sprints`.
     *   The UI only offers this choice for kanban boards; moving a board always
     *   deletes the source tasks (they were copied to the target project).
     * @returns {Promise<string|null>} The board id to fall back to.
     */
    async deleteBoard({ state }, { board, deleteChats = true } = {}) {
      const kanban = getKanban()
      const boardTitle = board?.title || board?.id || board
      if (!boardTitle || !kanban.boards?.[boardTitle]) return

      const boardType = board?.type || kanban.boards[boardTitle]?.type || 'kanban'
      const allChats = Object.values($storex.chats.chats || {})
      // Kanban tasks carry `chat.board`; sprint tasks carry the id in `sprints`.
      const boardChats = boardType === 'sprint'
        ? allChats.filter(c => (c.sprints || []).includes(boardTitle))
        : allChats.filter(c => c.board === boardTitle)

      if (deleteChats) {
        await Promise.all(boardChats.map(c => $storex.chats.deleteChat(c)))
      } else if (boardType === 'sprint') {
        // Keep the tasks, only remove this sprint from their membership.
        await Promise.all(boardChats.map(c => $storex.chats.updateChatInfo({
          chat: c,
          updates: { sprints: (c.sprints || []).filter(id => id !== boardTitle) }
        })))
      } else {
        // Keep the tasks but detach them from the board (board + column cleared)
        // so they fall back to the virtual "No board" board.
        await Promise.all(boardChats.map(c => $storex.chats.updateChatInfo({
          chat: c,
          updates: { board: '', column: '' }
        })))
      }

      const childBoardsList = Object.values(kanban.boards)
        .filter(b => b && b.parent_id === boardTitle)
      for (const child of childBoardsList) {
        await $storex.kanban.deleteBoard({ board: child, deleteChats })
      }

      mutations.deleteBoard(state, boardTitle)
      await $storex.kanban.saveKanban()

      // Return the board the caller should fall back to (parent or any other)
      return board?.parent_id ||
        Object.keys(kanban.boards).find(k => kanban.boards[k] !== null) ||
        null
    },

    async toggleBookmark({ state }, boardId) {
      const kanban = getKanban()
      const board = kanban.boards?.[boardId]
      // Guarded: the virtual board is not stored, so this is a no-op for it
      if (!board) return
      board.bookmark = !board.bookmark
      await $storex.kanban.saveKanban()
    },

    // ── Board export / import ─────────────────────────────────────────────────

    /**
     * Serialize a board (kanban or sprint) and ALL its tasks into a portable
     * document that can be imported into any project.
     *
     * The chat list endpoints only return a summary (last message), so every
     * task is force-loaded here to guarantee the full message history travels
     * with the export.
     *
     * @returns {object|null} the board document, or null when there is no board.
     */
    async exportBoard({ getters }, { boardId } = {}) {
      const board = getters.boardById(boardId)
      if (!board || board.virtual) return null

      const activeProject = $storex.projects.activeProject
      const tasks = board.type === 'sprint'
        ? getters.sprintBoardChats(boardId)
        : getters.boardChats(boardId)

      const chats = []
      for (const task of tasks) {
        if (!task?.id) continue
        const full = await $storex.chats.loadUninitialized(task)
        chats.push(JSON.parse(JSON.stringify(full || task)))
      }

      return {
        format: BOARD_EXPORT_FORMAT,
        version: BOARD_EXPORT_VERSION,
        exported_at: new Date().toISOString(),
        source: {
          project_id: activeProject?.project_id || null,
          project_name: activeProject?.project_name || null,
          abs_project_path: activeProject?.abs_project_path || null
        },
        board: {
          title: board.title,
          type: board.type || 'kanban',
          description: board.description || '',
          background: board.background || '',
          parent_id: board.parent_id || null,
          users: [...(board.users || [])],
          columns: (board.columns || []).map(col => ({
            id: col.id || null,
            title: col.title,
            icon: col.icon || null,
            color: col.color || null,
            // Profiles tasks created in this column inherit by default
            profiles: [...(col.profiles || [])],
            project_id: col.project_id || null,
            showSubTasks: col.showSubTasks,
            status: col.status || null,
            chats: [...(col.chats || [])]
          }))
        },
        chats
      }
    },

    /**
     * Import a board document into a project (the active one by default),
     * adapting every project-bound setting to the target project.
     *
     * Steps:
     *  1. Resolve a free board title and create the board shell.
     *  2. Make sure every task column exists on the board.
     *  3. Persist each task with a NEW id (parents/links remapped to the new ids).
     *  4. Link the kanban tasks into their board columns and save the board.
     *
     * @returns {{ boardId: string, board: object, importedCount: number }}
     */
    async importBoard({ getters }, { document: doc, project, title } = {}) {
      const payload = typeof doc === 'string' ? JSON.parse(doc) : doc
      if (!payload || payload.format !== BOARD_EXPORT_FORMAT || !payload.board) {
        throw new Error('Invalid board file')
      }

      const targetProject = project || $storex.projects.activeProject
      if (!targetProject?.project_id) {
        throw new Error('No target project selected')
      }

      // Ensure the target project kanban lives in the store (supports importing
      // into a project that is not currently active).
      if (!targetProject.$state?.kanban) {
        await $storex.projects.loadKanban(targetProject)
      }
      const kanban = getKanban(targetProject)
      if (!kanban.boards) kanban.boards = {}

      const boardType = payload.board.type || 'kanban'
      const boardTitle = findFreeBoardTitle(kanban, title || payload.board.title)

      // 1. Board shell (columns kept, tasks linked afterwards).
      kanban.boards[boardTitle] = {
        id: uuidv4(),
        title: boardTitle,
        type: boardType,
        description: payload.board.description || '',
        background: payload.board.background || '',
        // The parent board is NOT part of the export — the imported board is a root.
        parent_id: null,
        project_id: targetProject.project_id,
        users: [...(payload.board.users || [])],
        columns: (payload.board.columns || []).map(col => ({
          id: uuidv4(),
          title: col.title,
          icon: col.icon || null,
          color: col.color || null,
          // Profiles tasks created in this column inherit by default
          profiles: [...(col.profiles || [])],
          project_id: targetProject.project_id,
          showSubTasks: col.showSubTasks,
          // Sprint columns carry the task status they group
          status: col.status || null,
          chats: []
        })),
        last_update: new Date().toISOString()
      }
      const board = kanban.boards[boardTitle]

      const sourceChats = Array.isArray(payload.chats) ? payload.chats : []

      // 2. Guarantee every referenced column exists (kanban only).
      if (boardType !== 'sprint') {
        const known = new Set(board.columns.map(c => c.title))
        sourceChats.forEach(sourceChat => {
          const title = sourceChat?.column
          if (title && !known.has(title)) {
            known.add(title)
            board.columns = [...board.columns, {
              id: uuidv4(),
              title,
              color: null,
              profiles: [],
              project_id: targetProject.project_id,
              chats: []
            }]
          }
        })
      }
      await $storex.projects.saveKanban({ project: targetProject })

      // 3. Allocate the new chat ids first, so inter-task links can be remapped.
      const idMap = {}
      sourceChats.forEach(sourceChat => {
        if (sourceChat?.id) idMap[sourceChat.id] = uuidv4()
      })

      const sourcePath = payload.source?.abs_project_path || null
      const targetPath = targetProject.abs_project_path || null
      const columnTitles = (board.columns || []).map(c => c.title)

      const imported = []
      for (const sourceChat of sourceChats) {
        if (!sourceChat?.id || !idMap[sourceChat.id]) continue
        const chat = adaptImportedChat({
          sourceChat,
          idMap,
          boardTitle,
          boardType,
          projectId: targetProject.project_id,
          columnTitles,
          sourcePath,
          targetPath
        })
        const created = await $storex.chats.importChat(chat)
        if (created) imported.push({ source: sourceChat, chat: created })
      }

      // 4. Link the kanban tasks into their columns (sprint uses `sprints`).
      if (boardType !== 'sprint') {
        linkChatsToColumns(board, imported)
      }
      await $storex.projects.saveKanban({ project: targetProject })

      return {
        boardId: boardTitle,
        board,
        importedCount: imported.length,
        // The project the board now lives in (used by the caller to decide
        // whether the imported board can be focused in the current project).
        project: targetProject
      }
    },

    /**
     * Copy a board (with all its tasks) into another project.
     *
     * Reuses the same project-adapting pipeline as the file export/import: the
     * board is serialized (full message history included) and re-created in the
     * target project with NEW ids, retargeted projects, links, columns and file
     * references. The source board is left untouched.
     *
     * @returns {Promise<{ boardId: string, board: object, importedCount: number }>}
     */
    async copyBoardToProject(_, { boardId, project, title } = {}) {
      if (!boardId) throw new Error('No board selected')

      const targetProject = project || $storex.projects.activeProject
      if (!targetProject?.project_id) throw new Error('No target project selected')

      const document = await $storex.kanban.exportBoard({ boardId })
      if (!document) throw new Error('Nothing to copy')

      return await $storex.kanban.importBoard({
        document,
        project: targetProject,
        title
      })
    },

    /**
     * Move a board to another project: copy it (adapting every project-bound
     * setting) and only THEN remove it from the source project, so a failed
     * transfer never loses data. The virtual "No board" board cannot be moved.
     *
     * @returns {Promise<{ boardId: string, board: object, importedCount: number }>}
     */
    async moveBoardToProject({ getters }, { boardId, project, title } = {}) {
      const sourceBoard = getters.boardById(boardId)
      if (!sourceBoard || sourceBoard.virtual) {
        throw new Error('This board cannot be moved')
      }

      const result = await $storex.kanban.copyBoardToProject({ boardId, project, title })
      // Copy succeeded — now it is safe to drop the source board and its tasks.
      await $storex.kanban.deleteBoard({ board: sourceBoard, deleteChats: true })
      return result
    },
  }
)