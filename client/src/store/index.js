import { createStore, Store } from 'vuex'
import {
  useAccessor,
} from 'typed-vuex'

import * as session from './session'

const modules = { session }
const storePattern = {
  modules,
}

const store = createStore(storePattern)

export const $storex = useAccessor(store, storePattern)
$storex.init = async () => {
  await $storex.session.init()
}
$storex.store = new Store()
window.$storex = $storex
export default store