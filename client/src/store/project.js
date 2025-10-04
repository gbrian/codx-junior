import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { API } from '../api/api'
import { v4 as uuidv4 } from 'uuid'

export const namespaced = true

export const state = () => ({
  allProjects: null,
  chats: {},
  activeChat: null,
  activeProject: null,
  recentProjects: [], // New state property to keep track of recent projects
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
  openedWorkspaces: []
})

export const mutations = mutationTree(state, {
  setAllProjects(state, allProjects) {
    state.allProjects = allProjects?.sort((a, b) => {
        const aUpdated = a._metrics?.last_update || ""
        const bUpdated = b._metrics?.last_update || ""
        return aUpdated > bUpdated ? -1 : 1
      })
    state.activeChat = null
  },
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
  setActiveBoard(state, boardName) {
    state.activeBoard = boardName
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
  }
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
  profiles: state => $storex.profiles.profiles[state.activeProject.project_id]
                      .map(p => ({
                        ...p,
                        project: state.allProjects.find(({ project_id }) => project_id === p.project_id)
                      })),
  allChats: state => Object.values(state.chats || {}).map(chat =>createProjectChat(state.activeProject, chat)),
  allBoards: state => Object.keys(state.kanban.boards).map(title => ({ title, ...state.kanban.boards[title] })),
  allTags: state => new Set(Object.values(state.chats||{})?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || []),
  allPRs: () => $storex.projects.allChats().filter(c => c.pr_view?.from_branch),
  projectDependencies: state => {
    const { project_dependencies } = state.activeProject
    return project_dependencies?.split(",")
        .map(project_name => state.allProjects
        .find(p => p.project_name === project_name))
        .filter(f => !!f) || []
  },
  childProjects: state => state.allProjects.filter(p => 
      p.project_path !== state.activeProject.project_path && p.project_path.startsWith(state.activeProject.project_path))
  ,
  parentProject: state => state.allProjects.find(p =>
    p.project_path !== state.activeProject.project_path && state.activeProject.project_path.startsWith(p.project_path)),
  projectHierarchy: (state) => {
    const hierarchy = state.allProjects.map(project => ({ ...project }))
    return hierarchy.map(project => {
      project.parent_project = hierarchy
                        .filter(pp => project.project_path != pp.project_path) 
                        .find(pp => project.project_path.startsWith(pp.project_path))
      project.sub_projects = hierarchy
                        .filter(pp => project.project_path != pp.project_path)
                        .filter(pp => pp.project_path.startsWith(project.project_path))
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
  mentionList: () => {
    return [
      ...$storex.api.userNetwork.map(user => ({ 
        name: user.username,
        user,
        tooltip: `User @${user.username}` 
      })),
      ...$storex.projects.profiles.map(profile => ({ 
          name: profile.name,
          profile,
          tooltip: profile.description 
        })),
      ...[
        $storex.projects.activeProject,
        $storex.projects.parentProject,
        ...$storex.projects.childProjects,
        ...$storex.projects.projectDependencies,
      ]
        .filter(project => project)
        .map(project => ({ name: project.project_name, project, tooltip: `Search in project ${project.project_name}` })),
      ...[
        ...$storex.projects.knowledge?.files || [],
        ...$storex.projects.knowledge?.pending_files || []
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
      searchIndex: m.searchIndex || m.name.toLowerCase(),
      mention: encodeURIComponent(m.name)
    }))
  },
  lastAssistantChats: () =>
        $storex.projects.allChats
          .filter(c => c.board === 'codx-junior')
          .sort((a, b) => a.updated_at > b.updated_at ? -11 : 1).slice(0, 6),
  userList: () => [$storex.users.user, ...$storex.projects.profiles.map(p => ({ ...p, isProfile: true }))],
  workspaces: state => Object.values(state.allProjects.map(p => p.workspaces)
                          .reduce((a, b) => a.concat(b), [])
                          .reduce((acc, ws) => ({ ...acc, [ws.id]: ws }) , {}))
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
      $storex.projects.setAllProjects([])
      state.activeProject = null
      state.activeChat = null

      $storex.projects.loadAllProjects()
    },
    async loadAllProjects(_, withMetrics) {
      if ($storex.api.user) {
        try {
          await API.projects.list(withMetrics)
          $storex.projects.setAllProjects(API.allProjects)
          if (API.activeProject) {
            try {
              await $storex.projects.setActiveProject(API.activeProject)
            } catch {}
          }
          if (!$storex.projects.activeProject && $storex.projects.allProjects?.length) {
            $storex.projects.setActiveProject($storex.projects.allProjects[0])
          }
          return $storex.projects.allProjects
        } catch {
          $storex.session.onError("Error loading projects")
        }
      } 
      $storex.projects.setAllProjects([])
      state.activeProject = null
      state.activeChat = null
    },
    async setActiveProject ({ state, commit }, project) {
      const { project_name, codx_path } = project
      if ( project_name && !codx_path ) {
        project = $storex.projects.allProjects.find(p => p.project_name === project_name)
      }
      if (project?.codx_path === state.activeProject?.codx_path ) {
        return
      }

      if (project?.codx_path) {
        state.projectLoading = true
        try {
          const [_, models ] = await Promise.all([
            API.setActiveProject(project),
            API.projects.ai.models.list()
          ])
          state.ai.models = models

          state.activeProject = API.activeProject
          state.activeChat = null

          commit('addRecentProject', state.activeProject) // Update recent projects

          $storex.projects.loadProjectKnowledge()            
          await Promise.all([
            $storex.projects.loadProfiles(),
            $storex.projects.loadChats()
          ])
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
    async loadBranches({ state }) {
      state.project_branches = await $storex.api.repo.branches()
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
    async loadChat({ state }, chat) {
      const loadedChat = await API.chats.loadChat(chat)
      state.chats[loadedChat.id] = loadedChat
      if (state.activeChat?.id === loadedChat.id) {
        state.activeChat = state.chats[loadedChat.id]
      }
      return loadedChat
    },
    async deleteChat({ state }, chat) {
      if (!chat.temp) {
        await API.chats.delete(chat)
        await $storex.projects.loadChats()
      } else {
        delete state.chats[chat.id]
      }
    },
    async setActiveChat({ state }, { id } = {}) {
      if (id) {
        await $storex.projects.loadChat({ id })
      }
      state.activeChat = state.chats[id]
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
      state.activeProject = API.activeProject
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
      state.activeProject = API.activeProject
      $storex.projects.setAllProjects((state.allProjects||[])
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
    getProjectDependencies({ state }, project) {
      const { project_dependencies } = project
      return `${project_dependencies}`.split(",").map(dep => 
        state.allProjects.find(({ project_name }) => project_name === dep.trim()))
                          .filter(p => !!p)
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
        chat
      }
      $storex.session.emit({ event: 'codx-junior-chat', data })
    },
    async codxWiki(_, data) {
      $storex.session.emit({ event: 'codx-junior-wiki', data })
    },
    async createSubTasks({ state }, { chat, instructions }) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat,
        instructions
      }
      $storex.session.socket.emit({ event: 'codx-junior-subtasks', data })
    },
    async codeImprove({ state }, chat) {
      const data = {
        codx_path: state.activeProject.codx_path,
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
    createSubtasks({ state }, { chat, instructions }) {
      const data = {
        codx_path: state.activeProject.codx_path,
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
    
      if (chatId && (!state.chats[chatId] || type === 'changed')) {
        if (codx_path === state.activeProject.codx_path) {
            await $storex.projects.loadChat({ id: chatId })
        }
      }

      if (chatId) {
        const chat = state.chats[chatId] || await $storex.projects.loadChat({ id: chatId })
        if (chat && message) {
          const currentMessage = chat.messages.find(m => m.doc_id === message.doc_id)
          if (currentMessage) {
            currentMessage.is_thinking = message.is_thinking
            currentMessage.done = message.done
            if (message.is_thinking) {
              currentMessage.think += message.think
            } else {
              currentMessage.content += message.content
            }
            currentMessage.updated_at = new Date().toISOString()
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
    async createNewBoardChat({ state }, { boardTitle, columnTitle, chat }) {
      chat = await $storex.projects.createNewChat({
        board: boardTitle,
        column: columnTitle,
        ...chat
      })
      this.$projects.setActiveChat(chat)
      const column = $storex.projects.allBoards.find(({ title }) => title === boardTitle)
                        .columns.find(({ title }) => title === columnTitle)
      column.chats = [...column.chats||[], chat.id]
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
    async saveKanban({ state }) {
      await $storex.api.chats.kanban.save(state.kanban)
    },
    async saveProfile({ state }, profile) {
      const data = await $storex.profiles.saveProfile({ profile, project: state.activeProject })
      await $storex.projects.loadProfiles()
      if (state.selectedProfile.name === data.name) {
        state.selectedProfile = $storex.projects.profiles.find(p => p.name === data.name)
      }      
    },
    deleteProfile({ state }, profile) {
      if (profile.name === state.selectedProfile?.name) {
        state.selectedProfile = null
      }
      $storex.api.profiles.delete(profile.name)
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
    }
  }
)
