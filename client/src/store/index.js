import { createStore, Store } from 'vuex'
import {
  useAccessor,
} from 'typed-vuex'
import { API } from '../api/api'

import * as session from './session'
import * as projects from './project'
import * as ui from './ui'

const modules = { session, projects, ui }
const storePattern = {
  state () {
    return {
    }
  },
  modules,
}

let store = null
let storex = null
store = createStore(storePattern)
storex = useAccessor(store, storePattern)
storex.init = async () => {
  Object.keys(modules).forEach(async m => {
    await storex[m].init(storex)
  })
}
storex.store = store
storex.api = API
storex.init(storex)

window.$storex = storex

export default store
export const $storex = storex
