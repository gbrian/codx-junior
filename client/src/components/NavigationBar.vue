<script setup>
import moment from 'moment';
import ChatBar from './user/ChatBar.vue';
import CodxJuniorLogo from '@/components/CodxJuniorLogo.vue'
import WorkspacesSelector from './workspaces/WorkspacesSelector.vue';
</script>
<template>
  <div class="flex flex-col items-center shadow h-full"
    :class="$ui.showApp && 'click'">
    <div class="flex w-full flex-col mt-4 flex">
      <div class="">
        <CodxJuniorLogo @click="setProjectTab('wiki')" />

        <div class="absolute bottom-0 flex justify-center w-full"
          v-if="$session.apiCalls" @dblclick="$storex.session.decApiCalls()">
          <span class="badge badge-xs bg-secondary text-white animate-pulse">thinking</span>
        </div>
      </div>

      <div class="divider"></div>

      
      <div :class="['hover:bg-base-100 click relative', 
        !$project ? 'text-slate-400' :
          ($ui.activeTab === 'tasks' ? 'bg-base-100 text-primary': '')
        ,]">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Kanban"
          @click="setProjectTab('tasks')">
           <div class="flex flex-col gap-4">
            <i class="fa-brands fa-trello"></i>
          </div>
				</a>
			</div>

      <div :class="['hover:bg-base-100 click relative',
          !$project ? 'text-slate-400' :
              ($ui.activeTab === 'profiles' ? 'bg-base-100 text-primary': ''),]"
          v-if="$users.isProjectAdmin"
        >
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Profiles"
          @click="setProjectTab('profiles')">
           <div class="flex flex-col gap-4">
            <i class="fa-solid fa-user-group"></i>
          </div>
				</a>
			</div>

      <div :class="['hover:bg-base-100 click relative',
          !$project ? 'text-slate-400' :
              ($ui.activeTab === 'file-finder' ? 'bg-base-100 text-primary': ''),]">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="File finder"
          @click="setProjectTab('file-finder')">
           <div class="flex flex-col gap-4">
            <i class="fa-solid fa-folder"></i>
          </div>
				</a>
			</div>

      <div :class="['hover:bg-base-100 click relative', $ui.activeTab === 'home' ? 'bg-base-100 text-primary': '',]">
        <a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip"
          :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Add project"
          @click="setActiveTab('home')">
            <div class="flex flex-col gap-4">
              <i class="fa-solid fa-plus"></i>
          </div>
        </a>
      </div>

    </div>

    <div class="divider"></div>
    
    <ChatBar v-if="false" />

    <div class="grow"></div>
    <div class="divider"></div>

    <div class="dropdown dropdown-left" v-if="$projects.workspaces.length">
      <div tabindex="0" role="button" class="btn m-1">
        <i class="fa-solid fa-grip"></i>
      </div>
      <WorkspacesSelector tabindex="0"
        class="dropdown-content bg-base-300 rounded-box z-1 w-52 p-2 shadow-sm"
        :workspaces="$projects.workspaces"
        @select="onOpenWorkspace"
        v-if="$projects.workspaces"
      >
      </WorkspacesSelector>
    </div>
      
    <button class="hidden" v-if="$ui.showApp" @click="$ui.setFloatinCodxJunior(!$ui.floatingCodxJunior)">
      <i class="fa-solid fa-right-from-bracket" :class="$ui.floatingCodxJunior && 'rotate-180'"></i>
    </button>

    <div class="flex w-full flex-col mt-4 flex">
      <div :class="['hover:bg-base-100 click relative', $ui.appActives.includes('browser') ? 'text-primary': '',]"
        v-if="canShowBrowser"
      >
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show display"
          @click.stop="$ui.setShowBrowser(!$ui.appActives.includes('browser'))">
          <div class="flex flex-col gap-4">
            <i class="fa-brands fa-firefox"></i>
          </div>
				</a>
			</div>
      
      <div :class="['hover:bg-base-100 click relative', $ui.appActives.includes('coder') ? 'text-primary': '',]"
        v-if="canShowCoder"
      >
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show coder"
        @click.stop="$ui.setShowCoder(!$ui.appActives.includes('coder'))">
          <div class="flex flex-col gap-4">
            <i class="fa-solid fa-code"></i>
          </div>
				</a>
			</div>

      <div :class="['hover:bg-base-100 click relative group', $ui.showLogs ? 'text-primary': '',]">
        <a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" 
          :class="right ? 'tooltip-left' : 'tooltip-right'" 
          :data-tip="showLogsTooltip"
					 @click.stop="$ui.toggleLogs()">
           <div class="flex flex-col gap-4">
            <i class="fa-solid fa-chart-line"></i>
            <span class="text-xs text-warning hover:underline hover:opacity-100 absolute top-2 right-2 tooltip" data-tip="close" 
              v-if="$session.events.length">
              <i class="fa-solid fa-bell"></i>
            </span>
          </div>
				</a>
			</div>
    </div>

    <div class="divider"></div>

    <div>
      <div :class="['dropdown dropdown-end click',
        right ? 'dropdown-left' : 'dropdown-right']">
				<a tabindex="0" class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip"
          :class="right ? 'tooltip-left' : 'tooltip-right'" :data-tip="$users.user.username"
          @click="$ui.readScreenResolutions()">
          <div class="avatar">
            <div class="w-8 ring rounded-full">
              <img :src="$storex.api.user.avatar" />
            </div>
          </div>
				</a>
        <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box z-[50] w-72 p-2 shadow-xl">
          <li><a @click.stop="setActiveTab('account')">Account settings</a></li>
          <li v-if="$project && $storex.api.permissions.isProjectAdmin"><a @click.stop="setProjectTab('settings')">Project settings</a></li>
          <li v-if="$project"><a @click.stop="setProjectTab('knowledge_settings')">Knowledge settings</a></li>
          <li v-if="$storex.api.permissions.isAdmin"><a @click.stop="setActiveTab('global-settings')">Global settings</a></li>
          <li class="border"></li>
          <li>
            <a> 
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
                  :selected="$ui.resolution === resolution"
                >
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
          <li class="hidden">
            <a @click="$ui.toggleLogs()">
              <i class="fa-solid fa-chart-line"></i> Logs
            </a>
          </li>
          <li class="border"></li>
          <li><a @click.stop="$users.logout()">Log out</a></li>
        </ul>
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
      chat: null
    };
  },
  created () {
    this.$storex.api.screen.getScreenResolution()
  },
  computed: {
    canShowBrowser() {
      return this.$users.isAdmin || this.$user?.apps.includes("viewer")
    },
    canShowCoder() {
      return this.$users.isAdmin ||this.$user?.apps.includes("coder")
    },
    canShowAutogenStudio() {
      return this.$users.isAdmin ||this.$user?.apps.includes("autogenstudio")
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
    setActiveTab (tab) {
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
};
</script>