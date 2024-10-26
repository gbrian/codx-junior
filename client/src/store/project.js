import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'

export const namespaced = true

export const state = () => ({
  activeProject: null,
  allProjects: null,
  chats: null,
  activeChat: null
})

export const mutations = mutationTree(state, {
  setAllProjects(state, allProjects) {
    state.allProjects = allProjects
    state.activeChat = null
  }
})

export const getters = getterTree(state, {
  allTags: state => new Set(state.chats?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || [])
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init () {
      $storex.projects.loadAllProjects()
    },
    async loadAllProjects() {
      await API.init()
      $storex.projects.setAllProjects(API.allProjects)
      $storex.projects.setActiveProject(API.lastSettings)
    },
    async setActiveProject ({ state }, project) {
      if (project?.codx_path === state.activeProject?.codx_path) {
        return
      }
      await API.init(project?.codx_path)
      state.activeProject = project ? API.lastSettings : null
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
    },
    async deleteChat(_, name) {
      await API.chats.delete(name)
      await $storex.projects.loadChats()
    },
    async setActiveChat({ state }, { board, name } = {}) {
      if (name) {
        const chat = await API.chats.loadChat({ board, name })
        const existingChat = state.chats.find(c => c.name === name)
        if (existingChat) {
          existingChat.messages = chat.messages
        } else {
          state.chats = [...state.chats, chat]
        }
      }
      state.activeChat = state.chats.find(c => c.name === name)
    }
  }
)