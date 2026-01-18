<script setup>
import moment from 'moment'
import MobileMenuVue from './MobileMenu.vue'
import AppIcon from './apps/AppIcon.vue';
import ProjectIconVue from './ProjectIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center"
      :class="[
        $storex.session.connected ? '' : 'grayscale text-error',
      ]">

      <div class="tools hidden md:flex gap-2 items-center">

        <div class="flex gap-1 items-center pb-2">
              
          <div class="tooltip tooltip-top" :data-tip="app.name" 
            :class="['hover:bg-base-100 click relative pt-1 shadow rounded-lg border-t-4 ', 
              `group`,
              $ui.openApps[app.name] ? 'border-codx-secondary': 'opacity-80 hover:opacity-100 border-slate-700']"
              v-for="app in projectApps" :key="app.name + app.path"
              @click.stop="activeAppPanel(app)"
            >
            <a class="px-2 flex justify-center items-center w-full focus:text-orange-500">
              <div class="flex gap-2 items-center">
                <span class="click" @click.stop="toggleAppPanel(app)" v-if="$ui.openApps[app.name]">
                  <i class="fa-solid fa-caret-right" v-if="$ui.openApps[app.name].left"></i>
                  <i class="fa-solid fa-caret-left" v-else></i>
                </span>
                <AppIcon :app="app" />
                <div class="max-w-10 text-nowrap text-ellipsis overflow-hidden">{{ app.name }}</div> 
                <div class="text-error" title="close" v-if="$ui.openApps[app.name]" 
                  @click.stop="$ui.closeApp(app)">
                  <i class="fa-regular fa-circle-xmark"></i>
                </div>
              </div>
            </a>
            <video :src="videoThumb" class="hidden group:block" />
          </div>

          <div class="dropdown">
            <div tabindex="0" role="button" class="btn btn-sm btn-ghost m-1">
              <i class="fa-solid fa-ellipsis"></i>
            </div>
            <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow-sm">
              <li @click.stop="$ui.toggleFloatinCodxJunior()"
                v-if="$ui.activeApp">
                <a>
                  <i class="fa-solid fa-thumbtack rotate-45" v-if="$ui.floatingCodxJunior"></i>
                  <i class="fa-solid fa-thumbtack" v-else></i>
                  {{ $ui.floatingCodxJunior ? 'Pin' : 'Float'  }} codx-junior
                </a>
              </li>
              <div class="divider"></div>
              <li>
                <a>
                  workspace
                </a>
              </li>
            </ul>
          </div>

        </div>

      </div>

      <div class="divider"></div>

      <div class="flex gap-2 items-center justify-center -mt-4 hidden">
        <div :class="['hover:bg-base-100 click relative', 
          $ui.activeTab === 'home' ? 'border-b-4 border-codx-secondary': '']">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom" 
            data-tip="Home"
            @click="setActiveTab('home')">
            <div class="flex gap-2 items-center">
              <i class="fa-solid fa-home"></i> Home
            </div>
          </a>
        </div>

        <div :class="['hover:bg-base-100 click relative', !$project ? 'text-slate-400' : ($ui.activeTab === 'tasks' ? 'border-b-4 border-codx-secondary': '')]">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom" 
            data-tip="Kanban"
            @click="setProjectTab('tasks')">
            <div class="flex gap-2 items-center">
              <i class="fa-brands fa-trello"></i> Kanban
            </div>
          </a>
        </div>

        <div :class="['hover:bg-base-100 click relative', !$project ? 'text-slate-400' : ($ui.activeTab === 'profiles' ? 'border-b-4 border-codx-secondary': '')]"
            v-if="$users.isProjectAdmin">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom" 
            data-tip="Profiles"
            @click="setProjectTab('profiles')">
            <div class="flex gap-2 items-center">
              <i class="fa-solid fa-user-group"></i> Team
            </div>
          </a>
        </div>


        <div :class="['hover:bg-base-100 click relative', !$project ? 'text-slate-400' : ($ui.activeTab === 'wiki' ? 'border-b-4 border-codx-secondary': '')]">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom" 
            data-tip="Wiki"
            @click="setProjectTab('wiki')">
            <div class="flex gap-2 items-center">
              <i class="fa-solid fa-book"></i> Wiki
            </div>
          </a>
        </div>

        <div :class="['hover:bg-base-100 click relative', !$project ? 'text-slate-400' : ($ui.activeTab === 'file-finder' ? 'border-b-4 border-codx-secondary': '')]"
          v-if="$ui.isMobile"
        >
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom" 
            data-tip="File finder"
            @click="setProjectTab('file-finder')">
            <div class="flex gap-2 items-center">
              <i class="fa-solid fa-folder"></i> Files
            </div>
          </a>
        </div>
      </div>
      
      <div class="grow"></div>

      <div class="flex gap-2 justify-end items-center">
        <a class="btn btn-sm btn-outline text-codx-primary" @click="newQuickChat()">
          <i class="fa-regular fa-comment"></i>
        </a>
        
        <a class="btn btn-sm btn-outline text-primary" @click="$ui.showNewProject(true)">
          <i class="fa-solid fa-plus"></i>
        </a>
    </div>

      <modal v-if="restartModal">
        <div class="flex flex-col gap-2 font-mono">
          <div class="font-bold text-xl">Restart... really!!??</div>
          <div class="">
            <i class="fa-solid fa-heart-crack text-red-600"></i> Ouch, sorry to hear that... codx-junior will lose one live!  (don't worry, have many). 
            After restarting give some time to codx-junior and reload, good luck!
          </div>
          <div class="flex justify-between">
            <button class="btn btn-error" @click="$storex.api.restart">
              <i class="fa-solid fa-skull"></i> Kill codx-junior
            </button>
            <button class="btn" @click="restartModal = false">
              Ops, no, no...
            </button>
          </div>
        </div>
      </modal>
    </div>

  </div>
</template>

<script>
export default {
  props: ['right'],
  data() {
    return {
      isCollapsed: false,
      tabActive: 'text-info bg-base-100',
      tabInactive: 'text-warning bg-base-300 opacity-50 hover:opacity-100',
      restartModal: false,
      chat: null,
      showMobileMenu: false,
      newProject: false,
      videoThumb: null
    }
  },
  created () {
    this.$storex.api.screen.getScreenResolution()
  },
  computed: {
    canShowBrowser() {
      return this.$users.canShowBrowser
    },
    isSettings () {
      return ['settings', 'profiles', 'global-settings'].includes(this.$ui.activeTab)
    },
    isSharedScreen () {
      return this.$route.name === 'codx-junior-shared'
    },
    showLogsTooltip() {
      const lastEvent = this.$session.events[this.$session.events.length-1]
      if (lastEvent) {
        const message = lastEvent.data.message?.content || ""
        return `[${moment(lastEvent.ts).format('HH:mm:ss')}] ${lastEvent.event} ${lastEvent.data.text || ''}\n${message}`
      }
      return "Show logs/events"
    },
    projectApps() {
      return this.$storex.api.workspaces?.filter(w => w.project_ids.includes("*") || 
                            w.project_ids.includes(this.$project?.project_id))
                        .reduce((a, w) => a.concat(w.apps.map(a => ({ ...a, workspaceId: w.id }))), [])
                        .sort(a => this.$ui.openApps[a.name] && this.$ui.openApps[a.name].left ? -1: 1)

    }
  },
  methods: {
    setActiveTab(tab) {
      this.$ui.setActiveTab(tab)
    },
    setActiveProject(project) {
      this.$projects.setActiveProject(project)
    },
    async newQuickChat() {
      await this.$projects.createNewChat({ temp: true })
    },
    setProjectTab(tab) {
      if (this.$project) { 
        this.setActiveTab(tab)
      } else {
        this.$session.onError("No project selected")
      }
    },
    onOpenWorkspace({ workspace, app }) {
      this.$projects.openWorkspaceApp({ workspace, app })
    },
    async newQuickChat() {
      const chat = {
        name: "Quick chat",
        board: "Quick chats",
        column: moment().format("YYYYMMDD"),
        mode: 'chat'
      }
      this.$projects.createNewBoardChat({ chat })
      this.$ui.showTab('tasks')
    },
    toggleAppPanel({ name }) {
      const app = this.$ui.openApps[name]
      this.$ui.showApp({
        ...app,
        left: !app.left,
        ts: new Date().getTime()
      })
    },
    activeAppPanel(app) {
      app = app || this.$ui.openApps[app.name]
      this.$ui.showApp({
        ...app,
        ts: new Date().getTime()
      })
    }
  }
}
</script>