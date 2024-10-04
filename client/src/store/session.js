import { v4 as uuidv4 } from 'uuid';
import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import { $storex } from '.'
import io from 'socket.io-client';

export const namespaced = true

export const state = () => ({
  socket: null
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