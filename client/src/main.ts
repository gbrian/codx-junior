import './assets/main.css'

import { createApp } from 'vue'
import store, { $storex } from "./store";

import App from './App.vue'
import Modal from './components/Modal.vue'
import router from './router'
import Markdown from '@/components/Markdown.vue'
import FloatingVue from 'floating-vue'

// BUG: error loading module. Keep it here
import highlightjs from 'highlight.js'

const globalMixin = {
  computed: {
    $storex () {
      return $storex
    },
    $ui () {
      return $storex.ui
    },
    $projects () {
      return $storex.projects
    },
    $project () {
      return $storex.projects.activeProject
    },
    $session () {
      return $storex.session
    },
    $user () {
      return $storex.users.user
    },
    $users () {
      return $storex.users
    }
  }
}

$storex.init($storex)

const app = createApp(App)
              .mixin(globalMixin)
              .use(store)
              .use(router)
              .use(FloatingVue)
              .component('modal', Modal)
              .component('Markdown', Markdown)
              .mount('#app')

$storex.app = app
$storex.$router = router
