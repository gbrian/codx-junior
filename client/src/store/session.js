import { v4 as uuidv4 } from 'uuid';
import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import io from 'socket.io-client';

export const namespaced = true


import { API } from '../api/api'
// Add a request interceptor
API.axiosRequest.interceptors.request.use(function (config) {
    $storex.session.incApiCalls()
    return config;
  }, function (error) {
    $storex.session.decApiCalls()
    return Promise.reject(error);
  });

API.axiosRequest.interceptors.response.use(
  (response) => {
    $storex.session.decApiCalls()
    return response
  },
  (error) => {
    $storex.session.decApiCalls()
    $storex.session.setLastError(error)
    console.error("API ERROR:", error);
  });


export const state = () => ({
  socket: null,
  apiCalls: 0,
  lastError: null,
  id: uuidv4(),
  ts: new Date().getTime(),
  notifications: [],
  connected: false
})

export const getters = getterTree(state, {
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
  addNotification(state, notification) {
    notification.id = new Date().getTime()
    state.notifications = [...state.notifications, notification]
    setTimeout(() => $storex.session.removeNotification(notification), 15000)
  },
  removeNotification(state, notification) {
    state.notifications = state.notifications.filter(n => n.id !== notification.id)
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
    connect () {
      const socket = io({
        reconnectionDelayMax: 1000
       })
       socket.on("connect_error", (err) => {
        console.log(`connect_error due to ${err.message}`);
      });
      socket.on("connect", () => {
        console.log("Socket connected", socket.id)
        API.sid = socket.id
        $storex.session.setConnected(true)
      });
      socket.on("disconnect", () => $storex.session.setConnected(false))
      socket.io.on("reconnect", () => {
        $storex.session.setConnected(true)
      })
      $storex.session.setSocket(socket);
      socket.onAny((event, data) => $storex.session.onEvent({ event, data }))
    },
    onEvent(_, { event, data }) {
      console.log("On server message", event, data)
      $storex.session.onInfo(data)
    },
    onChanEvent(_, { id: chatId, text }) {
      $storex.session.onInfo({ text })  
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
    }
  },
)