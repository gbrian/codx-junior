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
  logs: null,
  formatedLogs: [],
  selectedLog: null,
  autoRefresh: false,
  changesSummary: null,
  selectedProfile: null,
  kanban: {},
  project_branches: {},
  projectLoading: false,
  knowledge: null,
  permissions: null
})

export const mutations = mutationTree(state, {
  setAllProjects(state, allProjects) {
    state.allProjects = allProjects
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
  }
})

export const getters = getterTree(state, {
  profiles: state => $storex.profiles.profiles[state.activeProject.project_id],
  allChats: state => Object.values(state.chats || {}),
  allTags: state => new Set(Object.values(state.chats||{})?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || []),
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
                        name: `file://${file.split('/').reverse()[0]}`,
                        filePath: file.split('/').reverse().slice(0, 3).reverse().join('/')
                      }))
        .map(({ file, name, filePath }) => ({ name, 
                        file, 
                        tooltip: `Use file ${filePath}` })),
    ].map(m => ({ ...m, searchIndex: m.name.toLowerCase() }))
  },
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init () {
      $storex.projects.loadAllProjects()
    },
    async loadAllProjects() {
      if ($storex.api.user) {
        await API.projects.list()
        $storex.projects.setAllProjects(API.allProjects)
        if (API.activeProject) {
          try {
            await $storex.projects.setActiveProject(API.activeProject)
          } catch {}
        }
        if (!$storex.projects.activeProject && $storex.projects.allProjects?.length) {
          $storex.projects.setActiveProject($storex.projects.allProjects[0])
        }
      } else { 
        state.allProjects = []
        state.activeProject = null
        state.activeChat = null
      }
    },
    async setActiveProject ({ state }, project) {
      if (project?.codx_path === state.activeProject?.codx_path) {
        return
      }
      state.projectLoading = true
      try {
        await API.setActiveProject(project)
      } finally {
        state.projectLoading = false
      }
      $storex.projects.loadProjectKnowledge()
      state.activeProject = API.activeProject
      state.chats = {}
      state.kanban = {}
      state.activeChat = null
      state.permissions = API.permissions.projectSettings(project)
      await $storex.projects.loadProfiles()
    },
    async loadProjectKnowledge({ state }) {
      state.knowledge = null
      const data = await API.knowledge.status()
      state.knowledge = data
    },
    async loadProfiles({ state }) {
      await $storex.profiles.loadProjectProfiles(state.activeProject)
    },
    async loadBranches({ state }) {
      state.project_branches = await $storex.api.projects.branches()
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
        state.activeChat = loadedChat
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
    async setActiveChat({ state }, chat) {
      if (chat) {
        await $storex.projects.loadChat(chat)
      }
      state.activeChat = chat ? state.chats[chat.id] : null
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
        await API.settings.read()
      } finally {
        state.projectLoading = false
      }
      state.activeProject = API.activeProject
      state.allProjects = (state.allProjects||[])
        .map(p => p.codx_path === state.activeProject.codx_path ? state.activeProject : p)
      return state.activeProject
    },
    async createNewProject(_, projectPath) {
      const newProject = await API.projects.create(projectPath)
      if (!newProject) {
        return null
      }
      await $storex.projects.loadAllProjects()
      const project = $storex.projects.allProjects.find(p => p.project_path === newProject.project_path)
      $storex.projects.setActiveProject(project)
      $storex.ui.coderOpenPath(project)
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
        codx_path: state.activeProject.codx_path,
        chat
      }
      $storex.session.socket.emit('codx-junior-chat', data)
    },
    async createSubTasks({ state }, { chat, instructions }) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat,
        instructions
      }
      $storex.session.socket.emit('codx-junior-subtasks', data)
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
            currentMessage.content += message.content
            currentMessage.updated_at = new Date().toISOString()
          } else {
            chat.messages.push(message)
          }
        }
      }
    },
    createNewChat({ state}, chat) {
      chat = {
        id: uuidv4(),
        mode: 'chat',
        profiles: [],
        chat_index: 0,
        ...chat
      }
      state.chats[chat.id] = chat
      if (!chat.temp) {
        state.activeChat = chat
      }
      return chat
    },
    async loadKanban({ state }) {
      state.kanban = await  $storex.api.chats.kanban.load()
    },
    async saveKanban({ state }) {
      await $storex.api.chats.kanban.save(state.kanban)
    },
    async saveProfile({ state }, profile) {
      const data = await $storex.profiles.saveProfile({ profile, project: state.activeProject })
      if (state.selectedProfile.name === data.name) {
        state.selectedProfile = data
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
    }
  }
)