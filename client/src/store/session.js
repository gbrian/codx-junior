import { v4 as uuidv4 } from 'uuid';
import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import io from 'socket.io-client';

export const namespaced = true

const EVENT_EXPIRE_SECONDS = 120
setInterval(() => $storex.session.tick(), 1000)

import { API } from '../api/api'
// Add a request interceptor
API.interceptors = { 
  request: [
    (config) => {
      $storex.session.incApiCalls()
      return config;
    }, 
    (error) => {
      $storex.session.decApiCalls()
      return Promise.reject(error);
    }
  ],
  response: [
    (response) => {
      $storex.session.decApiCalls()
      return response
    },
    (error) => {
      $storex.session.decApiCalls()
      $storex.session.setLastError(error)
      console.error("API ERROR:", error);
      $storex.session.onError(error.toString())
    }
  ]
}

export const state = () => ({
  socket: null,
  apiCalls: 0,
  lastError: null,
  id: uuidv4(),
  ts: new Date().getTime(),
  notifications: [],
  connected: false,
  user: {
    userName: new Date().getTime()
  },
  users: null,
  events: []
})

export const getters = getterTree(state, {
  lastEvent: state => state.events[state.events.length - 1]?.data,
  wikiEvents: ({ events }) => events.filter(e => e.data?.type === 'wiki')
})

export const mutations = mutationTree(state, {
  setSocket (state, socket) {
    state.socket = socket
  },
  incApiCalls(state) {
    state.apiCalls = state.apiCalls + 1
  },
  decApiCalls(state) {
    state.apiCalls = state.apiCalls - 1
  },
  setLastError(state, error) {
    state.setLastError = error
  },
  set$childCodxJuior(state, $childCodxJuior) {
    state.$childCodxJuior = $childCodxJuior
  },
  addNotification(_, notification) {
    $storex.ui.addNotification(notification)
  },
  setConnected(state, connected) {
    state.connected = connected
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init () {
      $storex.session.connect()
    },
    tick ({ state }) {
      const expireNotif = new Date( Date.now() - 1000 * EVENT_EXPIRE_SECONDS ).getTime();
      if (state.events.find(e => e.ts < expireNotif)) {
        state.events = state.events.filter(e => e.ts >= expireNotif)
      }
    },
    connect () {
      const socket = io({
        path: '/api/socket.io',
        reconnectionDelayMax: 1000
       })
       socket.on("connect_error", (err) => {
        console.log(`connect_error due to ${err.message}`);
      });
      socket.on("connect", () => {
        console.log("Socket connected", socket.id)
        API.sid = socket.id
        $storex.session.setConnected(true)
        $storex.session.login()
      });
      socket.on("disconnect", () => $storex.session.setConnected(false))
      socket.io.on("reconnect", () => {
        $storex.session.setConnected(true)
        $storex.session.login()
      })
      $storex.session.setSocket(socket);
      socket.onAny((event, data) => $storex.session.onEvent({ event, data }))
    },
    login({ state }) {
      $storex.session.socket.emit("codx-junior-login", { "user": API.user }, users => {
        state.users = users
      })
    },
    onEvent({ state }, { event, data }) {
      console.log("On server message", event, data)
      state.events.push({ event, data, ts: new Date().getTime() })
      const {
        codx_path,
        type,
        chat
      } = data
      if (codx_path) {
        data.project = $storex.projects.allProjects?.find(p => p.codx_path === codx_path)
      }
      if (chat) {
        $storex.projects.onChatEvent({ event, data })
      }
      if (type === 'notification') {
        $storex.ui.addNotification(data)
      }
      if (event === 'codx-junior-online-users') {
        $storex.users.setOnlineUsers(data)
      }
    },
    onInfo(_, notification) {
      if (typeof(notification) === 'string') {
        notification = { text: notification }
      }
      $storex.session.addNotification({ ...notification, type: 'info' })
    },
    onWarning(_, notification) {
      if (typeof(notification) === 'string') {
        notification = { text: notification }
      }
      $storex.session.addNotification({ ...notification, type: 'warning' })
    },
    onError(_, notification) {
      if (typeof(notification) === 'string') {
        notification = { text: notification }
      }
      $storex.session.addNotification({ ...notification, type: 'error' })
    },
    emit({ state }, { event, data }) {
      data = {
        ...data || {},
        codx_path: $storex.projects.activeProject.codx_path
      }
      state.socket.emit(event, data)
    }
  },
)