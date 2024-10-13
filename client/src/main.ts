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
    $project () {
      return $storex.project
    },
    $session () {
      return $storex.session
    },
    lastSettings () {
      return $storex.project.lastSettings
    }
  }
}

const app = createApp(App)
              .mixin(globalMixin)
              .provide('$storex', $storex)
              .use(router)
              .component('modal', Modal)
              .mount('#app')


store.app = app;
$storex.app = app;
$storex.init()
