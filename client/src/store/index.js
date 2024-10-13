import { createStore, Store } from 'vuex'
import {
  useAccessor,
} from 'typed-vuex'
import { API } from '../api/api'

import * as session from './session'
import * as project from './project'
import * as ui from './ui'

const modules = { session, project, ui }
const storePattern = {
  modules,
}

const store = createStore(storePattern)

export const $storex = useAccessor(store, storePattern)
$storex.init = async () => {
  Object.keys(modules).forEach(async m => {
    await $storex[m].init()
  })
}
$storex.store = new Store()
window.$storex = $storex
$storex.api = API
export default store