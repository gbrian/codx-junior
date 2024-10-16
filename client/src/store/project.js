import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import { API } from '../api/api'

export const namespaced = true

export const state = () => ({
  activeProject: null,
  allProjects: [],
  chats: null
})

export const mutations = mutationTree(state, {
  setAllProjects(state, allProjects) {
    state.allProjects = allProjects
  }
})

export const getters = getterTree(state, {
  allTags: state => new Set(state.chats?.map(c => c.tags).reduce((a, b) => a.concat(b), []) || [])
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
        await API.init()
        $storex.project.setAllProjects(API.allProjects)
        $storex.project.setActiveProject(API.lastSettings)
    },
    async setActiveProject ({ state }, project) {
      await API.init(project?.codx_path)
      state.activeProject = API.lastSettings
      await $storex.project.loadChats()
    },
    async loadChats({ state }) {
      state.chats = await API.chats.list()
    },
    async saveChat (_, chat) {
      await API.chats.save(chat)
      await $storex.project.loadChats()
    },
    async saveChatInfo (_, chat) {
      await API.chats.saveChatInfo(chat)
      await $storex.project.loadChats()
    },
    async loadChat({ state }, name) {
      const chat = await API.chats.loadChat(name)
      state.chats = [...state.chats.filter(c => c.name !== name), chat]
      return chat 
    },
    async newChat() {
      return await API.chats.newChat()
    },
    async deleteChat(_, name) {
      await API.chats.delete(name)
      await $storex.project.loadChats()
    }
  }
)