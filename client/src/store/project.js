import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { API } from '../api/api'

export const namespaced = true

export const state = () => ({
  allProjects: null,
  chats: null,
  activeChat: null,
  activeProject: null,
  logs: null,
  formatedLogs: [],
  selectedLog: null,
  autoRefresh: false,
  changesSummary: null,
  kanban: {}
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
  }
})

export const getters = getterTree(state, {
  allChats: state => Object.values(state.chats || {}),
  allTags: state => new Set(Object.values(state.chats||{})?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || []),
  projectDependencies: state => {
    const { project_dependencies } = state.activeProject
    return project_dependencies?.split(",")
        .map(project_name => state.allProjects
        .find(p => p.project_name === project_name))
        .filter(f => !!f)
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
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init () {
      await $storex.projects.loadAllProjects()
    },
    async loadAllProjects() {
      await API.project.list()
      $storex.projects.setAllProjects(API.allProjects)
      if (API.lastSettings) {
        try {
          await $storex.projects.setActiveProject(API.lastSettings)
        } catch {}
      }
      if (!$storex.projects.activeProject && $storex.projects.allProjects?.length) {
        $storex.projects.setActiveProject($storex.projects.allProjects[0])
      }
    },
    async setActiveProject ({ state }, project) {
      if (project?.codx_path === state.activeProject?.codx_path) {
        return
      }
      state.activeProject = project
      state.chats = {}
      state.activeChat = null
      await API.init(project?.codx_path)
      project && await $storex.projects.loadKanban()
      state.activeProject = API.lastSettings
      
    },
    async loadChats({ state }) {
      const chats = await API.chats.list()
      state.chats = chats.reduce((acc, chat) => ({ ...acc, [chat.id]: chat }), {})
      $storex.projects.setActiveChat(state.chats[state.activeChat?.id])
    },
    async saveChat (_, chat) {
      await API.chats.save(chat)
      await $storex.projects.loadChats()
    },
    async saveChatInfo (_, chat) {
      await API.chats.saveChatInfo({ ...chat, messages: [] })
      await $storex.projects.loadChats()
    },
    async loadChat({ state }, chat) {
      const loadedChat = await API.chats.loadChat(chat)
      state.chats[loadedChat.id] = loadedChat
      return loadedChat
    },
    async deleteChat(_, chat) {
      await API.chats.delete(chat)
      await $storex.projects.loadChats()
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
      await API.settings.write(settings)
      await $storex.projects.loadAllProjects()
      state.activeProject = API.lastSettings
    },
    async realoadProject({ state }) {
      await API.settings.read()
      state.activeProject = API.lastSettings
      state.allProjects = (state.allProjects||[])
        .map(p => p.codx_path === state.activeProject.codx_path ? state.activeProject : p)
      return state.activeProject
    },
    async createNewProject(_, projectPath) {
      const { data: newProject } = await API.project.create(projectPath)
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
        const { data } = await API.logs.read("codx-junior-api")
        return data
      } catch (error) {
        console.error(error)
        return []
      }
    },
    async refreshChangesSummary({ state }, rebuild) {
      state.changesSummary = await $storex.api.run.changesSummary(rebuild)
    },
    async chatWihProject({ state }, chat) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat
      }
      $storex.session.socket.emit('codx-junior-chat', data)
    },
    async createSubTasks({ state }, chat) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat
      }
      $storex.session.socket.emit('codx-junior-subtasks', data)
    },
    async onChatEvent({ state }, { event, data }) {
      const {
        chat: {
          id: chatId
        },
        message
      } = data
      if (chatId) {
        const chat = state.chats[chatId] || await $storex.projects.loadChat({ id: chatId })
        if (chat && message) {
          const currentMessage = chat.messages.find(m => m.doc_id === message.doc_id)
          if (currentMessage) {
            currentMessage.content += message.content
          } else {
            chat.messages.push(message)
          }
        }
      }
    },
    createNewChat({ state}, chat) {
      state.chats[chat.id] = chat
      state.activeChat = chat
    },
    async loadKanban({ state }) {
      const [kanban] = await Promise.all([
                              $storex.api.chats.kanban.load(),
                              $storex.projects.loadChats()
                            ])
      state.kanban = kanban
    },
    async saveKanban({ state }) {
      await $storex.api.chats.kanban.save(state.kanban)
    }
  }
)