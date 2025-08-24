import './assets/main.css'

import { createApp, onBeforeMount, onBeforeUnmount } from 'vue'
import store, { $storex } from "./store";
import service from "./service"

import App from './App.vue'
import Modal from './components/Modal.vue'
import router from './router'
import Markdown from '@/components/Markdown.vue'
import FloatingVue from 'floating-vue'

import 'vuefinder/dist/style.css'
import VueFinder from 'vuefinder/dist/vuefinder'

// BUG: error loading module. Keep it here
import highlightjs from 'highlight.js'

const globalMixin = {
  onBeforeMount() {
    console.log("Before mount. Events: ", this.events, this.$root)
  },
  onBeforeUnmount() {
    console.log("Before Unmount. Events: ", this.events)
  },
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
      return $storex.api.user
    },
    $users () {
      return $storex.users
    },
    $globalSettings() {
      return $storex.api.globalSettings
    },
    $service () {
      return service
    }
  },
  methods: {
    $bubble(event: string, data: EventInit) {
    }
  }
}

$storex.users.login()

const app = createApp(App)
              .mixin(globalMixin)
              .use(store)
              .use(router)
              .use(FloatingVue)
              .use(VueFinder)
              .component('modal', Modal)
              .component('Markdown', Markdown)
              .mount('#app')

$storex.app = app
$storex.$router = router
