import './assets/main.css'

import { createApp } from 'vue'
import store, { $storex } from "./store";

import App from './App.vue'
import Modal from './components/Modal.vue'
import router from './router'

const globalMixin = {
  computed: {
    $storex () {
      return $storex
    },
    $ui () {
      return $storex.ui
    },
    $project () {
      return $storex.project
    },
    $session () {
      return $storex.session
    }
  }
}

const app = createApp(App)
              .mixin(globalMixin)
              .use(store)
              .use(router)
              .component('modal', Modal)
              .mount('#app')

$storex.app = app
$storex.$router = router
