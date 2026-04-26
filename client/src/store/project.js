import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { API } from '../api/api'
import { v4 as uuidv4 } from 'uuid'
import Fuse from 'fuse.js';

export const namespaced = true

const createState = () => ({
  allProjects: [],
  allProjectsById: {},
  chats: [],
  activeChat: null,
  activeProject: null,
  recentProjects: [],
  logs: null,
  formatedLogs: [],
  selectedLog: null,
  autoRefresh: false,
  changesSummary: null,
  selectedProfile: null,
  kanban: null,
  project_branches: {},
  projectLoading: false,
  knowledge: null,
  activeBoard: null,
  kanbanTemplates: [
    {
      name: "Backlog",
      description: "Backlog board",
      columns: [
        { title: "Backlog", color: "#FFC300" },
        { title: "In Development", color: "#DAF7A6" },
        { title: "Completed", color: "#C70039" }
      ]
    },
    {
      name: "Scrum",
      description: "Scrum board",
      columns: [
        { title: "To Do", color: "#FF5733" },
        { title: "In Progress", color: "#33FF57" },
        { title: "Done", color: "#3357FF" }
      ]
    },
  ],
  activeWizards: [],
  ai: {
    models: []
  },
  openedWorkspaces: [],
  projectBarnches: {},
  workspaces: []
})

function getProfiles(project) {
  const { project_id, $state } = project
  return $state?.profiles || $storex.profiles.profilesByProject[project_id]
}

const initProject = async project => {
      try {
          const [_, models ] = await Promise.all([
            project.$api.setActiveProject(project),
            project.$api.projects.ai.models.list()
          ])
          project.$state.ai.models = models
          
          Object.assign(project.$state,  { 
            profiles: await project.$api.profiles.list(), 
            chats: await project.$api.chats.list(),
            knowledge: {},
            _mentionList: null,
            get mentionList() {
              if (!this._mentionList) {
                this._mentionList = buildMentions(project)
              }
              return this._mentionList
            },
            searchMentions(query, limit = 10) {
              const fuseOptions = {
                // isCaseSensitive: false,
                includeScore: false,
                // ignoreDiacritics: false,
                // shouldSort: true,
                // includeMatches: false,
                // findAllMatches: false,
                // minMatchCharLength: 1,
                // location: 0,
                // threshold: 0.6,
                // distance: 100,
                // useExtendedSearch: false,
                // ignoreLocation: false,
                // ignoreFieldNorm: false,
                // fieldNormWeight: 1,
                keys: [
                  "name",
                  "searchIndex",
                  "file"
                ]
              };

              const fuse = new Fuse(this.mentionList, fuseOptions);
              return fuse.search(query).map(r => r.item).slice(0, limit)
            }
          })
      } catch (ex) {
        console.log("Error initializing project", project, ex)
      }
      return project
}

function getProjectDependencies(project) {
    const { project_dependencies } = project
    return project_dependencies?.split(",")
        .map(project_name => $storex.projects.allProjects
          .find(p => p.project_name === project_name))
          .filter(f => !!f) || []
  }

function buildMentions(project) {
  const { $state: {knowledge, profiles }, project_id, parent_id } = project

  return [
    ...$storex.api.userNetwork.map(user => ({ 
      name: user.username,
      user,
      tooltip: `User @${user.username}` 
    })),
    ...profiles.map(profile => ({ 
        name: profile.name,
        profile,
        tooltip: profile.description 
      })),
    ...[
      project,
      $storex.projects.allProjectsById[parent_id],
      ...$storex.projects.allProjects.filter(p => p.parent_id === project_id),
      ...getProjectDependencies(project),
    ]
      .filter(project => project)
      .map(project => ({ name: project.project_name, project, tooltip: `Search in project ${project.project_name}` })),
    ...[
      ...knowledge?.files || [],
      ...knowledge?.pending_files || []
    ]
    .map(file => ({ file,
                    name: file.split('/').reverse()[0],
                    filePath: file.split('/').reverse().slice(0, 3).reverse().join('/')
                  }))
    .map(({ file, name, filePath }) => ({ 
                    name, 
                    file, 
                    searchIndex: filePath,
                    tooltip: `Use file ${filePath}`
                  })),
  ].map(m => ({ 
    ...m,
    avatar: m.user?.avatar || m.profile?.avatar || m.project?.project_icon,
    searchIndex: (m.searchIndex || m.name).toLowerCase(),
    mention: encodeURIComponent(m.name)
  }))
}


export const state = createState

export const mutations = mutationTree(state, {
  setLogs(state, logs) {
    state.logs = logs
  },
  setFormatedLogs(state, formatedLogs) {
    state.formatedLogs = formatedLogs
  },
  setSelectedProfile(state, profile) {
    state.selectedProfile = profile
  },
  setProjectLoading(state, value) {
    state.projectLoading = value
  },
  addWizard(state, wizard) {
    wizard.id = wizard.id || new Date().getTime()
    state.activeWizards.push(wizard)
  },
  removeWizard(state, wizard) {
    state.activeWizards = state.activeWizards.filter(w => w !== wizard)
  },
  addRecentProject(state, project) { // New mutation to update recent projects
    state.recentProjects = [project, ...state.recentProjects.filter(p => p.codx_path !== project.codx_path)].slice(0, 5)
  },
})


function createProjectChat(project, chat) {
  return {
    ...chat,
    get chatLink() {
      return `/project/${project.project_id}/chat/${chat.id}`
    }
  }
}

export const getters = getterTree(state, {
  allParentProjects: () => $storex.api.allProjects.filter(p => !p.parentProject),
  profiles: state => getProfiles(state.activeProject),
  allChats: state => Object.values(state.chats || {}).map(chat =>createProjectChat(state.activeProject, chat)),
  allBoards: state => Object.keys(state.kanban.boards).map(title => ({ title, ...state.kanban.boards[title] })),
  allTags: state => new Set(Object.values(state.chats||{})?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || []),
  allPRs: () => $storex.projects.allChats().filter(c => c.pr_view?.from_branch),
  projectDependencies: state => getProjectDependencies(state.activeProject),
  childProjects: state => state.allProjects.filter(p => 
      p.abs_project_path !== state.activeProject.abs_project_path && p.abs_project_path.startsWith(state.activeProject.abs_project_path))
  ,
  parentProject: state => state.allProjects.find(p =>
    p.abs_project_path !== state.activeProject.abs_project_path && state.activeProject.abs_project_path.startsWith(p.abs_project_path)),
  projectHierarchy: (state) => {
    const hierarchy = state.allProjects.map(project => ({ ...project }))
    return hierarchy.map(project => {
      project.parent_project = hierarchy
                        .filter(pp => project.abs_project_path != pp.abs_project_path) 
                        .find(pp => project.abs_project_path.startsWith(pp.abs_project_path))
      project.sub_projects = hierarchy
                        .filter(pp => project.abs_project_path != pp.abs_project_path)
                        .filter(pp => pp.abs_project_path.startsWith(project.abs_project_path))
      return project
    })
  },
  embeddingsModel: state => state.activeProject?.embeddings_model || 
                                $storex.api.globalSettings?.embeddings_model,
  aiModel: state => state.activeProject?.llm_model || 
                      $storex.api.globalSettings?.llm_model,
  chatModes: state => {
    return {
      "task": { name: "Analyst", profiles: [], icon: "fa-solid fa-user-doctor" },
      "chat": { name: "Developer", profiles: [], icon: "fa-regular fa-comments" },
    }
  },
  branches: state => state.project_branches.branches,
  currentBranch: state => state.project_branches.current_branch,
  mentionList: () => buildMentions($storex.projects.activeProject),
  lastAssistantChats: () =>
        $storex.projects.allChats
          .filter(c => c.board === 'codx-junior')
          .sort((a, b) => a.updated_at > b.updated_at ? -11 : 1).slice(0, 6),
  userList: () => [$storex.users.user, ...$storex.projects.profiles?.map(p => ({ ...p, isProfile: true }))] || [],
  projectApps: state => state.workspaces?.reduce((a, w) => 
                  a.concat(w.apps.map(a => ({ ...a, workspaceName: w.name, key: `${w.name}-${a.name}` }))), [])
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
      await $storex.projects.setAllProjects([])
      state.activeProject = null
      state.activeChat = null

      await $storex.projects.loadAllProjects()
      $storex.ui.setUIready()      
    },
    async loadAllProjects({ state }, withMetrics) {
      if ($storex.api.user) {
        try {
          await API.projects.list(withMetrics)
          await $storex.projects.setAllProjects(API.allProjects)
          if (API.activeProject) {
            try {
              await $storex.projects.setActiveProject(API.activeProject)
            } catch {}
          }
          if (!$storex.projects.activeProject && $storex.projects.allProjects?.length) {
            await $storex.projects.setActiveProject($storex.projects.allProjects[0])
          }
          return $storex.projects.allProjects
        } catch (ex) {
          $storex.session.onError("Error loading projects", ex)
        }
      } 
      $storex.projects.setAllProjects([])
      state.activeProject = null
      state.activeChat = null
    },
    async setActiveProject ({ state }, project) {
      const { project_id, project_name, codx_path } = project
      if ( !codx_path ) {
        project = $storex.projects.allProjects
          .find(p => p.project_name === project_name || 
                      p.project_id === project_id)
      }
      if (project?.codx_path === state.activeProject?.codx_path ) {
        return
      }

      if (project?.codx_path) {
      state.projectLoading = true
      try {

        API.setActiveProject(project)
          
        const existsProject = state.allProjects.find(p => p.project_id === API.activeProject.project_id)
        if (!existsProject) {
          await $storex.projects.setAllProjects([ ...state.allProjects, API.activeProject ])
        }
        state.activeProject = state.allProjectsById[API.activeProject.project_id]
        await $storex.projects.loadChats()
        if (state.activeChat?.project_id !== API.activeProject.project_id) {
          state.activeChat = null
        }
        state.ai = state.activeProject.$state.ai

        $storex.projects.addRecentProject(state.activeProject) 
        state.workspaces = API.workspaces
        $storex.ui.saveState()
      } finally {
        state.projectLoading = false
      }
      }
    },
    async loadProjectKnowledge({ state }) {
      const data = await API.knowledge.status()
      state.knowledge = data
    },
    async loadProfiles({ state }) {
      await $storex.profiles.loadProjectProfiles(state.activeProject)
    },
    async loadBranches({ state }, project) {
      const projectState = project?.$state || state
      const api = project?.$api || $storex.api
      
      projectState.project_branches = await api.repo.branches()
    },
    async loadPR({ state }, { fromBranch, toBranch }) {
      state.activePR = await $storex.api.repo.changes({ fromBranch, toBranch })
    },
    async createPR({ state }, { fromBranch, toBranch }) {
      state.activePR = await $storex.api.repo.changes({ fromBranch, toBranch })
    },
    async loadChats({ state }) {
      const chats = await API.chats.list()
      state.chats = chats.reduce((acc, chat) => ({ ...acc, [chat.id]: chat }), {})
      $storex.projects.setActiveChat(state.chats[state.activeChat?.id])
    },
    async saveChat (_, chat) {
      await API.chats.save(chat)
    },
    async saveChatInfo (_, chat) {
      await API.chats.saveChatInfo({ ...chat, messages: [] })
      await $storex.projects.loadChats()
    },
    async findProjectChat({ state }, { id, owner_project_id }) {
      const project = state.allProjectsById[owner_project_id]
      const chat = project.$state.chats.find(c => c.id === id)
      if (chat) {
        return chat
      }
      const loadedChat = await project.$api.chats.loadChat({ id, owner_project_id }) 
      project.$state.chats = project.$state.chats = [...project.$state.chats, loadedChat]
      return loadedChat 
    },
    async loadChat({ state }, chat) {
      if (!state.chats[chat.id]) {
        chat = await API.chats.loadChat(chat)
        state.chats[chat.id] = chat
      }
      if (state.activeChat?.id === chat.id) {
        state.activeChat = state.chats[chat.id]
      }
      return chat
    },
    async reloadChat({ state }, chat) {
      if (state.chats[chat.id]) {
        delete state.chats[chat.id]
      }
      return $storex.projects.loadChat(chat)
    },
    async deleteChat({ state }, chat) {
      if (!chat.temp) {
        await API.chats.delete(chat)
      }
      if (state.chats[chat.id]) {
        delete state.chats[chat.id]
      }
    },
    async setActiveChat({ state }, { id, project_id } = {}) {
      if (id) {
        await $storex.projects.reloadChat({ id, project_id })
      }
      if ($storex.ui.isMobile) {
        state.activeChat = state.chats[id]
      } else if (state.chats[id]) {
        $storex.ui.openChat(state.chats[id])
      }
    },
    async addLogIgnore({ state }, ignore) {
      let ignores = state.activeProject.log_ignore?.split(",") || []
      if (!ignores.includes(ignore)) {
        ignores.push(ignore.trim())
        state.activeProject.log_ignore = ignores.filter(i => i.trim().length).join(",")
        $storex.projects.saveSettings()
      }
    },
    async removeLogIgnore({ state }, ignore) {
      let ignores = state.activeProject.log_ignore?.split(",") || []
      if (ignores.includes(ignore)) {
        ignores = ignores.filter(i => i !== ignore)
        state.activeProject.log_ignore = ignores.filter(i => i.trim().length).join(",")
        $storex.projects.saveSettings()
      }
    },
    async saveSettings({ state }, settings) {
      state.projectLoading = true
      try {
        await API.settings.save(settings)
      } finally {
        state.projectLoading = false
      }
      state.activeProject = null
      $storex.projects.setActiveProject(API.activeProject)
    },
    async realoadProject({ state }) {
      state.projectLoading = true
      try {
        const [_, models] = await Promise.all([
          API.settings.read(),
          API.projects.ai.models.list()
        ])
        state.ai.models = models
      } finally {
        state.projectLoading = false
      }
      state.activeProject = null
      await $storex.projects.setActiveProject(API.activeProject)
      await $storex.projects.setAllProjects((state.allProjects||[])
        .map(p => p.codx_path === state.activeProject.codx_path ? state.activeProject : p))
      return state.activeProject
    },
    async createNewProject(_, projectPath) {
      const newProject = await API.projects.create(projectPath)
      if (!newProject) {
        return null
      }
      await $storex.projects.loadAllProjects()
      $storex.projects.setActiveProject(newProject)
    },
    async fetchAPILogs() {
      try {
        const data = await API.logs.read("codx-junior-api")
        return data
      } catch (error) {
        console.error(error)
        return []
      }
    },
    async refreshChangesSummary({ state }, { branch, rebuild }) {
      state.changesSummary = await $storex.api.run.changesSummary({ branch, rebuild })
    },
    async chatWihProject({ state }, chat) {
      const data = {
        chat,
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path
      }
      $storex.session.emit({ event: 'codx-junior-chat', data })
    },
    async chatSearch({ state }, { chat, query }) {
      const data = {
        chat: {
          id: chat.id
        },
        query,
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path
      }
      $storex.session.emit({ event: 'codx-junior-chat-search', data })
    },
    async codxWiki(_, data) {
      $storex.session.emit({ event: 'codx-junior-wiki', data })
    },
    async createSubTasks({ state }, { chat, instructions }) {
      const data = {
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path,
        chat,
        instructions
      }
      $storex.session.socket.emit({ event: 'codx-junior-subtasks', data })
    },
    async codeImprove({ state }, chat) {
      const data = {
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path,
        chat
      }
      $storex.session.socket.emit('codx-junior-improve', data)
    },
    async codeImprovePatch({ state }, { chat, code_generator }) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat,
        code_generator
      }
      $storex.session.socket.emit('codx-junior-improve-patch', data)
    },
    generateCode({ state }, { chat, codeBlockInfo }) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat,
        code_block_info: codeBlockInfo
      }
      $storex.session.socket.emit('codx-junior-generate-code', data)
    },
    async createSubtasks({ state }, { chat, instructions }) {
      const data = {
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path,
        chat,
        instructions
      }
      $storex.session.socket.emit('codx-junior-generate-tasks', data)
    },
    async onChatEvent({ state }, { event, data }) {
      const {
        chat: {
          id: chatId
        },
        message,
        event_type,
        type,
        codx_path
      } = data

      if (event_type === 'error') {
        $storex.ui.addNotification({ text: message, type: event_type })
      }
    
      if (chatId) {
        const { project_id } = $storex.projects.allProjects.find(p => p.codx_path === codx_path)
        if (type === 'changed' || !state.chats[chatId]) {
            await $storex.projects.reloadChat({ id: chatId, project_id })
        }
        const chat = state.chats[chatId]
        if (chat && message) {
          const currentMessage = chat.messages.find(m => m.doc_id === message.doc_id)
          if (currentMessage) {
            if (event_type === "done") {
              Object.assign(currentMessage, message)
            } else {
              currentMessage.is_thinking = message.is_thinking
              currentMessage.done = message.done
              currentMessage.meta_data = message.meta_data
              if (message.is_thinking) {
                currentMessage.think += message.think
              } else {
                currentMessage.content += message.content
              }
              currentMessage.updated_at = new Date().toISOString()
            }
          } else {
            chat.messages.push(message)
          }
        }
      }
    },
    async createNewChat({ state }, chat) {
      chat = {
        id: uuidv4(),
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        messages: [],
        ...chat
      }
      state.chats[chat.id] = chat
      if (!chat.temp) {
        await $storex.projects.saveChat(chat)
      }
      return chat
    },
    async createNewThread(_, { chat, mode, message }) {
      const { files, profiles, doc_id: subtaskMessageId } = message
      const findChild = $storex.projects.allChats.find(c => c.message_id === subtaskMessageId) 

      if (!findChild) {
        const boardTitle = chat.board
        const columnTitle = chat.column
        await $storex.projects.createNewBoardChat({ boardTitle, columnTitle,
          chat: {
            parent: chat,
            name: `${subtaskMessageId} - thread`,
            project_id: chat.project_id,
            parent_id: chat.parent_id,
            message_id: subtaskMessageId,
            file_list: files,
            profiles: profiles,
            mode,
            board: chat.board,
            column: chat.column,
            activateChat: true,
            child_index: this.childrenChats?.length,
            messages: [{ ...message, doc_id: null }]
          }
        })
      } else {
        this.$projects.setActiveChat(findChild)
      }
    },
    async createNewBoardChat({ state }, { boardTitle, columnTitle, chat }) {
      boardTitle = boardTitle || chat.board
      columnTitle = columnTitle || chat.column
      const newColumn = {
        title: columnTitle,
        chats: []
      }
      if (!state.kanban) {
        await $storex.projects.loadKanban()
      }
      if (!state.kanban.boards[boardTitle]) {
        state.kanban.boards = {
          ...state.kanban.boards,
          [boardTitle]: {
            columns: [newColumn]
          }
        }
      }
      let column = $storex.projects.allBoards
                        .find(({ title }) => title === boardTitle).columns.find(({ title }) => title === columnTitle)
      if (!column) {
        column = newColumn
        state.kanban.boards[boardTitle].columns.push(column)
      }

      chat = await $storex.projects.createNewChat({
        board: boardTitle,
        column: columnTitle,
        ...chat
      })
      $storex.projects.setActiveChat(chat)
      column.chats = [...column?.chats||[], chat.id]
      $storex.projects.saveKanban(state.kanban)
      return $storex.projects.allChats.find(c => c.id === chat.id)
    },
    async createNewChatFromUrl({ state}, chat) {
      chat = {
        id: uuidv4(),
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        ...chat
      }
      state.chats[chat.id] = await API.chats.fromUrl(chat)
      if (!chat.temp) {
        state.activeChat = state.chats[chat.id]
      }
      return state.chats[chat.id]
    },
    async loadKanban({ state }) {
      state.kanban = await $storex.api.chats.kanban.load()
    },
    async saveKanban({ state }, kanban) {
      await $storex.api.chats.kanban.save(kanban || state.kanban)
    },
    async saveProfile({ state }, profile) {
      const project = state.allProjectsById[profile.project_id] || state.activeProject
      const data = await $storex.profiles.saveProfile({ profile, project })
      await $storex.projects.loadProfiles()
      if (state.selectedProfile.name === data.name) {
        state.selectedProfile = $storex.projects.profiles.find(p => p.name === data.name)
      }      
    },
    deleteProfile({ state }, profile) {
      const project = state.allProjectsById[profile.project_id] || state.activeProject
      if (profile.name === state.selectedProfile?.name) {
        state.selectedProfile = null
      }
      $storex.profiles.deleteProfile({ profile, project })
      $storex.profiles.loadProjectProfiles(state.activeProject)
    },
    createNewProfile({ state }, profile) {
      state.selectedProfile = profile
    },
    async addBoard({ _ }, { title, parent_id, description, columns }) {
      if (!$storex.projects.kanban) {
        await $storex.projects.loadKanban()
      }
      if (!$storex.projects.kanban.boards[title]) {
        $storex.projects.kanban.boards[title] = {
          id: uuidv4(),
          title,
          parent_id,
          description,
          columns,
          last_update: new Date().toISOString()
        }        
        $storex.projects.saveKanban()
      }
      $storex.projects.setActiveBoard(title)
      return $storex.projects.allBoards.find(b => b.title === title)
    },
    async editBoard({ state }, { title, newTitle, description }) {
      const existingBoard = state.kanban.boards[title]
      existingBoard.description = description
      if (title !== newTitle) {
        if (!state.kanban.boards[newTitle]) {
          state.kanban.boards[newTitle] = existingBoard
          delete  state.kanban.boards[title]    
        }
      }
      $storex.projects.saveKanban()
    },
    async deleteBoard({ state }, { id, title }) {
      delete state.kanban.boards[title]
      if (state.activeBoard == title) {
        state.activeBoard = null
      }
      // Delete board chats
      await $storex.api.chats.kanban.delete(title)
      $storex.projects.saveKanban()
    },
    async applyPatch(_,patch) {
      return API.run.patch(patch)
    },
    openWorkspaceApp({ state }, { workspace, app }) {
      const ix = state.openedWorkspaces.findIndex(ows => ows.workspace.id === workspace.id && app.port === ows.app.port)
      if (ix !== -1) {
        state.openedWorkspaces = state.openedWorkspaces.filter((_, iix) => iix != ix)
      } else {
        state.openedWorkspaces = [...state.openedWorkspaces, { workspace, app }]
      }
    },
    async exportChat({ state }, { chat, exportFormat, clipboard }) {
      const project = state.activeProject;
      const api = project.$api || await API.project(project);

      try {
        return await api.chats.exportChat({ id: chat.id, exportFormat, clipboard });
      } catch (error) {
        console.error("Error exporting chat:", error);
      }
    },
    async loadProject({ state }, { project_id, project_name, codx_path }) {
      return await initProject(state.allProjects.find(p => {
        return p.project_id === project_id ||
              p.project_name === project_name ||
              p.codx_path === codx_path
      }))
    },
    async setActiveBoard({ state }, boardName) {
      if (!state.kanban) {
        await $storex.projects.loadKanban()
      }
      state.activeBoard = boardName
      state.activeChat = null
    },
    getChatProject({ state }, chat) {
      return state.allProjectsById[chat.project_id] || state.activeProject
    },
    async setAllProjects({ state }, allProjects) {
      state.allProjects = allProjects?.sort((a, b) => {
              const aUpdated = a._metrics?.last_update || ""
              const bUpdated = b._metrics?.last_update || ""
              return aUpdated > bUpdated ? -1 : 1
            })
      state.allProjectsById = state.allProjects?.reduce((acc, p) => ({ ...acc, [p.project_id]: p }), {}) || {}
          
      return Promise.all(allProjects.map(async project => {
          let { $api } = project
          if (!$api) {
            project.$api = await API.project(project)
            project.$state = createState()
            initProject(project)
          }
      }))
    },
  }
)
