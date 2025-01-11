import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'

export const namespaced = true

export const state = () => ({
  allProjects: null,
  chats: null,
  activeChat: null,
  activeProject: null
})

export const mutations = mutationTree(state, {
  setAllProjects(state, allProjects) {
    state.allProjects = allProjects
    state.activeChat = null
  }
})

export const getters = getterTree(state, {
  allTags: state => new Set(state.chats?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || []),
  projectDependencies: state => {
    const { project_dependencies } = state.activeProject
    return project_dependencies?.split(",")
        .map(project_name => state.allProjects
        .find(p => p.project_name === project_name))
        .filter(f => !!f)
  },
  childProjects: state => {
    const { _sub_projects } = state.activeProject
    return _sub_projects?.map(project_name => state.allProjects
        .find(p => p.project_name === project_name))
        .filter(f => !!f)
  },
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
      $storex.projects.setActiveProject(API.lastSettings)
    },
    async setActiveProject ({ state }, project) {
      if (project?.codx_path === state.activeProject?.codx_path) {
        return
      }
      await API.init(project?.codx_path)
      state.activeProject = API.lastSettings
      state.activeChat = null
      project && await $storex.projects.loadChats()
    },
    async loadChats({ state }) {
      state.chats = await API.chats.list()
    },
    async saveChat (_, chat) {
      await API.chats.save(chat)
      await $storex.projects.loadChats()
    },
    async saveChatInfo (_, chat) {
      await API.chats.saveChatInfo(chat)
      await $storex.projects.loadChats()
    },
    async loadChat({ state }, { board, name }) {
      const chat = await API.chats.loadChat({ board, name })
      state.chats = [...state.chats.filter(c => c.name !== name), chat]
      return chat 
    },
    async newChat({ state }, chat) {
      state.activeChat = chat
      return chat
    },
    async deleteChat(_, {  board, name }) {
      await API.chats.delete(board, name)
      await $storex.projects.loadChats()
    },
    async setActiveChat({ state }, chat) {
      if (chat) {
        const loadedChat = await API.chats.loadChat(chat)
        state.chats = [...state.chats.filter(c => c.id !== loadedChat.id), loadedChat]
      }
      state.activeChat = state.chats.find(c => c.id === chat?.id)
      $storex.ui.setKanban(state.activeChat?.board)
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
      state.activeProject = API.lastSettings
      state.allProjects = (state.allProjects||[])
        .map(p => p.codx_path === state.activeProject.codx_path ? state.activeProject : p)
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
    }
  }
)