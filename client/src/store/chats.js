import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { API } from '../api/api'
import { v4 as uuidv4 } from 'uuid'


export const namespaced = true

export const state = () => ({
  chats: null,
})

// TODO: Move chat logic from projects store