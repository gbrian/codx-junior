<script setup>
import moment from 'moment'
import MobileMenuVue from './MobileMenu.vue'
import ProjectDetailt from './ProjectDetailt.vue'
import AppIcon from './apps/AppIcon.vue';
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center shadow justify-between"
      :class="[
        $storex.session.connected ? '' : 'grayscale text-error',
      ]">
      <div class="flex gap-2 items-center w-1/3" @click="showMobileMenu = !showMobileMenu">
        <div class="flex flex-col">
          <MobileMenuVue class="" v-if="showMobileMenu" @click.stop="" @close="showMobileMenu = false" />
          <span class="animate-pulse text-xs text-center" v-if="!$storex.session.connected">...offline</span>
        </div>
        <ProjectDetailt 
          :project="$project" 
          :options="{ showFolders: false, showIcon: !$ui.isMobile, showSelector: false }"
          @select="$projects.setActiveProject($event)"  
        /> 

      </div>
      

      <div class="flex gap-2 justify-end w-1/3 items-center">
        
        <a class="btn btn-sm btn-outline text-codx-primary" @click="newQuickChat()">
          <i class="fa-regular fa-comment"></i>
        </a>
        
        <a class="btn btn-sm btn-outline text-primary" @click="$ui.showNewProject(true)">
          <i class="fa-solid fa-plus"></i>
        </a>

        <div class="flex gap-1 items-center justify-end">
          <div :class="['dropdown dropdown-bottom dropdown-start click dropdown-left']">
            <a tabindex="0" class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom"
                :data-tip="$users.user.username"
              @click="$ui.readScreenResolutions()">
              <div class="avatar">
                <div class="w-6 md:w-8 ring rounded-full">
                  <img :src="$storex.api.user.avatar" />
                </div>
              </div>
            </a>
            <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box z-[150] w-72 p-2 shadow-xl">
              <li>
                <a class="flex gap-1" @click.stop="setActiveTab('account')">
                  <i class="fa-regular fa-circle-user"></i>
                  Account settings
                </a>
              </li>
              <li v-if="$project && $storex.api.permissions.isProjectAdmin">
                <a class="flex gap-1"  @click.stop="setProjectTab('settings')">
                  <i class="fa-solid fa-sliders"></i>
                  Project settings
                </a>
              </li>
              <li v-if="$project">
                <a @click.stop="setProjectTab('knowledge_settings')">
                  <i class="fa-solid fa-book"></i>
                  Knowledge settings
                </a>
              </li>
              <li v-if="$storex.api.permissions.isAdmin">
                <a class="flex gap-1"  @click.stop="setActiveTab('global-settings')">
                  <i class="fa-solid fa-gear"></i>
                  Global settings
                </a>
              </li>
              <li v-if="$storex.api.permissions.isAdmin">
                <a class="flex gap-1"  @click="$ui.toggleLogs()">
                  <i class="fa-solid fa-chart-line"></i> Logs
                </a>
              </li>
              <li class="border"></li>
              <li>
                <a class="flex gap-1"> 
                  <i class="fa-solid fa-microphone-lines"></i>
                  <select class="select select-sm" @change="$ui.setVoiceLanguage($event.target.value)">
                    <option v-for="key, lang in $ui.voiceLanguages"
                      :key="lang"
                      :selected="$ui.voiceLanguage === lang" :value="lang">{{ key }}</option>
                  </select>
                </a>
              </li>
              <li class="hidden">
                <a>
                  <i class="fa-solid fa-table-columns"></i>
                  <select class="select select-sm overflow-auto" @change="$ui.setAppDivided($event.target.value)">
                    <option v-for="divider in ['none', 'horizontal', 'vertical']" :key="divider" :value="divider">
                      {{ divider }}
                    </option>
                  </select>
                </a>
              </li>
              <li class="hidden">
                <a>
                  <span class="click" @click="$storex.api.screen.getScreenResolution()"><i class="fa-solid fa-display"></i></span>
                  <select class="select select-sm overflow-auto"
                    @change="$ui.setScreenResolution($event.target.value)">
                    <option disabled selected>Select Resolution</option>
                    <option v-for="resolution in $ui.resolutions" :key="resolution" :value="resolution"
                      :selected="$ui.resolution === resolution">
                      {{ resolution }}
                    </option>
                  </select>
                  <div class="dropdown dropdown-end group">
                    <div tabindex="2" role="button" class="btn btn-xs m-1">
                      <i class="fa-solid fa-up-right-and-down-left-from-center" v-if="$ui.noVNCSettings.resize === 'scale'"></i>
                      <i class="fa-solid fa-down-left-and-up-right-to-center" v-else></i>
                    </div>
                    <ul tabindex="2" class="hidden group-hover:flex dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li @click="$ui.setNoVNCSettings({ resize: 'scale' })">
                        <a><i class="fa-solid fa-up-right-and-down-left-from-center"></i> Local</a>
                      </li>
                      <li @click="$ui.setNoVNCSettings({ resize: 'remote' })">
                        <a><i class="fa-solid fa-down-left-and-up-right-to-center"></i> Remote</a>
                      </li>
                    </ul>
                  </div>
                </a>
              </li>
              <li class="border"></li>
              <li>
                <a class="flex gap-1" @click.stop="$users.logout()">
                  <i class="fa-solid fa-right-from-bracket"></i>
                  Log out
                </a>
              </li>
            </ul>
          </div>
        </div>
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

    <div class="tools hidden md:flex gap-2 items-center w-full">

      <div class="flex gap-2 items-center pb-2">
            
        <div class="tooltip tooltip-bottom" :data-tip="app.name" 
          :class="['hover:bg-base-100 click relative pb-2', 
            $ui.openApps[app.name] ? 'border-b-4 border-codx-secondary': '']"
          v-for="app in projectApps" :key="app.name + app.path"
          >
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500"
          @click.stop="$ui.showApp(app)"
          >
            <div class="indicator flex gap-2 items-center">
              <span class="indicator-item text-xs text-error" title="close" 
                @click.stop="$ui.closeApp(app)" v-if="$ui.openApps[app.name]">
                <i class="fa-regular fa-circle-xmark"></i>
              </span>
            
              <AppIcon :app="app" />
            </div>
          </a>
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
      
      <div class="grow"></div>
      
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

        <div :class="['hover:bg-base-100 click relative pb-2', 
          $ui.showLogs ? 'border-b-4 border-codx-secondary': '']">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom"  data-tip="Show logs"
          @click.stop="$ui.toggleLogs()">
            <div class="flex gap-2 items-center">
              <i class="fa-solid fa-file-lines"></i>
            </div>
          </a>
        </div>

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
      newProject: false
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
    }
  }
}
</script>