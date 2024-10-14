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
  lastError: null
})

const session = {
  id: uuidv4(),
  ts: new Date().getTime()
}

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
  }
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init () {
    },
    login ({ commit }, { username, password }) {
      const socket = io('/');
      $storex.session.setSocket(socket);
    }
  },
)