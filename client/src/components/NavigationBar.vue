<script setup>
import moment from 'moment'
import WorkspacesSelector from './workspaces/WorkspacesSelector.vue'
import SearchBar from './bar/SearchBar.vue'
import MobileMenuVue from './MobileMenu.vue'
import ProjectDetailt from './ProjectDetailt.vue'
import ProjectIcon from './ProjectIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center shadow justify-between"
      :class="[
        $storex.session.connected ? '' : 'grayscale text-error',
        $ui.showApp && 'click'
      ]">
      <div class="flex gap-2 items-center w-1/3" @click="showMobileMenu = true">
        <div class="flex flex-col" v-if="$ui.isMobile">
          <ProjectIcon class="cursor-pointer md:cursor-auto" :project="{ avatar: '/only_icon.png'}" />
          <MobileMenuVue class="md:hidden" v-if="showMobileMenu" @close="showMobileMenu = false" />
          <span class="animate-pulse text-xs text-center" v-if="!$storex.session.connected">...offline</span>
        </div>
        <ProjectDetailt 
          :project="$project" 
          :options="{ showFolders: !$ui.isMobile, showIcon: !$ui.isMobile, showSelector: !$ui.isMobile }"
          @select="$projects.setActiveProject($event)"  
        /> 

      </div>
      

      <div class="flex gap-2 justify-end w-1/3 items-center">

        <div class="w-40">
          <SearchBar />
        </div>

        <a class="btn btn-sm btn-outline text-codx-primary">
          <span class="hidden md:block">
            <i class="fa-solid fa-plus"></i>
          </span>
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
            <i class="fa-brands fa-trello"></i> Tasks
          </div>
        </a>
      </div>

      <div :class="['hover:bg-base-100 click relative', !$project ? 'text-slate-400' : ($ui.activeTab === 'profiles' ? 'border-b-4 border-codx-secondary': '')]"
          v-if="$users.isProjectAdmin">
        <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom" 
          data-tip="Profiles"
          @click="setProjectTab('profiles')">
          <div class="flex gap-2 items-center">
            <i class="fa-solid fa-user-group"></i> Profiles
          </div>
        </a>
      </div>

      <div :class="['hover:bg-base-100 click relative', !$project ? 'text-slate-400' : ($ui.activeTab === 'file-finder' ? 'border-b-4 border-codx-secondary': '')]">
        <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom" 
          data-tip="File finder"
          @click="setProjectTab('file-finder')">
          <div class="flex gap-2 items-center">
            <i class="fa-solid fa-folder"></i> Files
          </div>
        </a>
      </div>

      <div class="grow"></div>
      <div class="flex gap-2 items-center pb-2">
      
        <div class="dropdown dropdown-bottom" v-if="$projects.workspaces.length">
          <div tabindex="0" class="flex gap-2 items-center text-center pb-2 click hover:bg-base-100 px-2 py-1 rounded-md">
            <i class="fa-solid fa-grip"></i> Workspaces
          </div>
          <WorkspacesSelector tabindex="0"
            class="dropdown-content bg-base-100 rounded-box z-1 w-52 p-2 z-50 shadow-sm font-bold"
            :workspaces="$projects.workspaces"
            @select="onOpenWorkspace"
            v-if="$projects.workspaces">
          </WorkspacesSelector>
        </div>
      
        <div :class="['hover:bg-base-100 click relative pb-2 ', 
          $ui.appActives.includes('browser') ? 'border-b-4 border-codx-secondary': '']"
          v-if="canShowBrowser">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom"  data-tip="Show display"
            @click.stop="$ui.setShowBrowser(!$ui.appActives.includes('browser'))">
            <div class="flex gap-2 items-center">
              <i class="fa-brands fa-firefox"></i> 
            </div>
          </a>
        </div>
        
        <div :class="['hover:bg-base-100 click relative pb-2', 
          $ui.appActives.includes('coder') ? 'border-b-4 border-codx-secondary': '']">
          <a class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom"  data-tip="Show coder"
          @click.stop="$ui.setShowCoder(!$ui.appActives.includes('coder'))">
            <div class="flex gap-2 items-center">
              <i class="fa-solid fa-code"></i>
            </div>
          </a>
        </div>
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
      showMobileMenu: false
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
    }
  }
}
</script>