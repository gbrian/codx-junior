import './assets/main.css'

import { createApp, defineAsyncComponent, onBeforeMount, onBeforeUnmount, watch } from 'vue'
import store, { $storex } from "./store"
import service from "./service"

import App from './App.vue'
import Modal from './components/Modal.vue'
import Toast from './components/Toast.vue'
import router from './router'

import 'vuefinder/dist/style.css'
import VueFinder from 'vuefinder/dist/vuefinder'

// Markdown is only needed once a message containing markdown is rendered. It
// used to be imported eagerly here, which dragged the whole editor graph
// (monaco-editor, @git-diff-view, vue-code-highlighter, highlight.js) into the
// entry chunk and blocked the first paint.
const Markdown = defineAsyncComponent(() => import('@/components/Markdown.vue'))

// Monaco workers are registered on the first editor mount by
// src/components/monaco/monacoWorkers.js (see src/components/monaco/Editor.vue).
//
// highlight.js is imported by its consumers through src/utils/highlight.js, so
// only the languages actually supported are bundled. Vite keeps it
// pre-bundled via `optimizeDeps.include` (see vite.config.ts) — that is what
// the previous entry-level import used to force.

function generateUID(length) {
  return window.btoa(String.fromCharCode(...window.crypto.getRandomValues(new Uint8Array(length * 2)))).replace(/[+/=]/g, "").substring(0, length)
}

// The mixin is applied app-wide, so anything in its lifecycle hooks runs once
// per component instance — every panel, list row and toolbar button. The
// lifecycle logs below were a measurable share of the mount cost in the
// production profile, so they are now dev-only (stripped by esbuild `define`).
const globalMixin = {
  onBeforeMount() {
    if (import.meta.env.DEV) {
      console.log("Before mount. Events: ", this.events, this.$root)
    }
  },
  onBeforeUnmount() {
    if (import.meta.env.DEV) {
      console.log("Before Unmount. Events: ", this.events)
    }
  },
  computed: {
    $storex () {
      return $storex
    },
    $ui () {
      return $storex.ui
    },
    $views () {
      return $storex.views
    },
    $projects () {
      return $storex.projects
    },
    $app () {
      const tabId = this.$props?.params?.params?.app?.tabId
      if (!tabId) return null
      return $storex.ui.openApps[tabId]
    },
    $projectId() {
      return this.$app?.params?.project_id ||
             this.$props?.params?.params?.app?.params?.project_id
    },
    $project () {
      return $storex.projects.allProjectsById[this.$projectId] ||
             $storex.projects.activeProject
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
    $chats () {
      return $storex.chats
    },
    $teams () {
      return $storex.teams
    },
    $media () {
      return $storex.media
    },
    $globalSettings() {
      return $storex.api.globalSettings
    },
    $service () {
      return service
    },
    // FIXED: restored $toast computed so this.$toast works in all components
    $toast () {
      return $storex.toast.toastApi
    }
  },
  watch: {
  },
  methods: {
    $bubble(event: string, data: EventInit) {
    },
    generateUID
  }
}

$storex.users.login()

const app = createApp(App)
              .mixin(globalMixin)
              .use(store)
              .use(router)
              .use(VueFinder)
              .component('modal', Modal)
              .component('Markdown', Markdown)
              .component('Toast', Toast)
              .mount('#app')

$storex.app = app
$storex.$router = router

// eruda for mobile debugging
window.setTimeout(() =>
  (function() {
    function isMobile() {
      return /Mobi|Android/i.test(navigator.userAgent)
    }
    if (isMobile()) {
      var script1 = document.createElement('script')
      script1.src = "https://cdn.jsdelivr.net/npm/eruda"
      document.body.appendChild(script1)
    }
  })(), 10)