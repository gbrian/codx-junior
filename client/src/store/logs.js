import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'

import { API } from '../api/api'

export const state = () => ({
  rawLogs: [],
  logNames: [],
  selectedLog: 'codx-junior-api',
  autoRefresh: false,
  showMetrics: false,
  showTimeFilter: false,
  filter: null
})

export const getters = getterTree(state, {
  filteredLogs: (state) => {
    const isLogVisible = log => {
      const patterns = state.filter?.split(',').map(p => p.trim().toLowerCase()) || []
      return !patterns.some(pattern => log.toLowerCase().includes(pattern))
    }
    return state.rawLogs.filter(isLogVisible)
  },
  matchCount: (state, getters) => {
    return state.filter ? 
           getters.filteredLogs.filter(log =>
             log.toLowerCase().includes(state.filter.toLowerCase())).length : 0
  }
})

export const mutations = mutationTree(state, {
  setRawLogs(state, logs) {
    state.rawLogs = logs
  },
  setLogNames(state, logNames) {
    state.logNames = logNames
  },
  setSelectedLog(state, log) {
    state.selectedLog = log
  },
  clearLogs(state) {
    state.rawLogs = []
  },
  setFilter(state, filter) {
    state.filter = filter
  },
  setAutoRefresh(state, autoRefresh) {
    state.autoRefresh = autoRefresh
  },
  toggleAutoRefresh(state) {
    state.autoRefresh = !state.autoRefresh
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async fetchLogNames() {
      try {
        const logNames = await API.logs.list()
        $storex.logs.setLogNames(logNames)
        if (logNames.length) {
          $storex.logs.setSelectedLog(logNames[0])
          await $storex.logs.fetchLogs()
        }
      } catch (error) {
        console.error('Error fetching log names:', error)
      }
    },
    async fetchLogs({ state }, tailSize) {
      const data = await API.logs.read(state.selectedLog, tailSize)
      if (state.autoRefresh) {
        const newLogs = data.filter(l => !state.rawLogs.includes(l))
        $storex.logs.setRawLogs([...state.rawLogs, ...newLogs])
        setTimeout(() => $storex.logs.fetchLogs(tailSize), 3000)
      } else {
        $storex.logs.setRawLogs(data)
      }
    },
  }
)
