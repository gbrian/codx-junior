import { createStore, Store } from 'vuex'
import {
  useAccessor,
} from 'typed-vuex'
import { API } from '../api/api'

import * as session from './session'
import * as projects from './project'
import * as ui from './ui'
import * as users from './users'
import * as profiles from './profiles'

const modules = { session, projects, ui, users, profiles }
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
  await API.init()
  await Promise.all(Object.keys(modules).map(async m => {
    if (storex[m].init) {
      await storex[m].init(storex)
    }
  }))
  $storex.ui.setUIready()
}
storex.store = store
storex.api = API

window.$storex = storex

export default store
export const $storex = storex
