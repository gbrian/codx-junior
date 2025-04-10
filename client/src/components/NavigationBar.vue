<script setup>
import ProjectIconVue from './ProjectIcon.vue'
import UserList from './UserList.vue'
import moment from 'moment';
</script>
<template>
  <div class="flex flex-col items-center shadow h-full"
    :class="$ui.showApp && 'click'">

    <div class="relative">
    <ProjectIconVue
      :right="right"
      :online="$storex.session.connected"
    />
      <div class="absolute bottom-0 flex justify-center w-full"
        v-if="$session.apiCalls" @dblclick="$storex.session.decApiCalls()">
        <span class="badge badge-xs bg-secondary text-white animate-pulse">thinking</span>
      </div>
    </div>

    <UserList v-if="false" />


    <div class="flex w-full flex-col mt-4 flex">
      <div :class="['hover:bg-base-100 click relative', $ui.tabIx === 'wiki' ? 'bg-base-100 text-primary': '',]">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Wiki"
          @click="$ui.setActiveTab('wiki')">
          <i class="fa-solid fa-book-medical"></i>
				</a>
			</div>
      
      <div :class="['hover:bg-base-100 click relative', $ui.tabIx === 'tasks' ? 'bg-base-100 text-primary': '',]">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Kanban"
          @click="$ui.setActiveTab('tasks')">
           <div class="flex flex-col gap-4">
            <i class="fa-brands fa-trello"></i>
          </div>
				</a>
			</div>

      <div :class="['hover:bg-base-100 click relative', $ui.tabIx === 'prview' ? 'bg-base-100 text-primary': '',]">
        <a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" 
          :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Changes details"
          @click="$ui.setActiveTab('prview')">
            <div class="flex flex-col gap-4">
                <i class="fa-solid fa-code-compare"></i>
            </div>
        </a>
      </div>

      <div :class="['hidden hover:bg-base-100 click relative', $ui.tabIx === 'knowledge_settings' ? 'bg-base-100 text-primary': '',]">
        <a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Knowledge"
          @click="$ui.setActiveTab('knowledge_settings')">
          <div class="flex flex-col gap-4">
            <i class="fa-solid fa-book"></i>
          </div>
        </a>
      </div>

      <div :class="['hover:bg-base-100 click relative', $ui.tabIx === 'profiles' ? 'bg-base-100 text-primary': '',]">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Team"
          @click="$ui.setActiveTab('profiles')">
           <div class="flex flex-col gap-4">
            <i class="fa-solid fa-user-group"></i>
          </div>
				</a>
			</div>

      <div :class="['hover:bg-base-100 click relative', $ui.tabIx === 'help' ? 'bg-base-100 text-primary': '',]">
        <a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip"
          :class="right ? 'tooltip-left' : 'tooltip-right'"
          data-tip="Add project"
          @click="$ui.setActiveTab('help')">
            <div class="flex flex-col gap-4">
              <i class="fa-solid fa-plus"></i>
          </div>
        </a>
      </div>

    </div>



    <div class="grow"></div>
    <div class="divider"></div>
      
    <button class="hidden md:block" v-if="$ui.showApp" @click="$ui.setFloatinCodxJunior(!$ui.floatingCodxJunior)">
      <i class="fa-solid fa-right-from-bracket" :class="$ui.floatingCodxJunior && 'rotate-180'"></i>
    </button>

    <div class="flex w-full flex-col mt-4 flex">
      <div :class="['hover:bg-base-100 click relative', $ui.appActives[0] === 'coder' ? 'text-primary': '',]">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" data-tip="Show coder"
        @click.stop="$ui.setShowCoder(true)">
          <div class="flex flex-col gap-4">
            <i class="fa-solid fa-code"></i>
            <span class="text-xs text-error hover:underline opacity-50 hover:opacity-100 absolute top-2 right-2 tooltip" data-tip="close" 
              @click.stop="$ui.setShowCoder(false)" v-if="$ui.showCoder">
              <i class="fa-solid fa-power-off"></i>
            </span>
          </div>
				</a>
			</div>
      <div :class="['hover:bg-base-100 click', $ui.appActives[0] === 'browser' ? 'text-primary': '']">
				<a class="h-16 px-6 flex justify-center items-center w-full focus:text-orange-500 tooltip" :class="right ? 'tooltip-left' : 'tooltip-right'" 
          data-tip="Show preview"
					 @click.stop="$ui.setShowBrowser(true)">
           <div class="flex flex-col gap-4">
            <i class="fa-solid fa-display"></i>
            <span class="text-xs text-error hover:underline opacity-50 hover:opacity-100 absolute top-2 right-2 tooltip" data-tip="close" 
              @click.stop="$ui.setShowBrowser(false)" v-if="$ui.showBrowser">
              <i class="fa-solid fa-power-off"></i>
            </span>
          </div>
				</a>
			</div>
      <div :class="['hover:bg-base-100 click relative', $ui.showLogs ? 'text-primary': '',]">
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
          <li v-if="$storex.api.permissions.isProjectAdmin"><a @click.stop="setActiveTab('settings')">Project settings</a></li>
          <li v-if="$storex.api.permissions.isAdmin"><a @click.stop="setActiveTab('global-settings')">Global settings</a></li>
          <li><a @click.stop="setActiveTab('knowledge_settings')">Knowledge settings</a></li>
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
          <li>
            <a>
              <i class="fa-solid fa-table-columns"></i>
              <select class="select select-sm overflow-auto" @change="$ui.setAppDivided($event.target.value)">
                <option v-for="divider in ['none', 'horizontal', 'vertical']" :key="divider" :value="divider">
                  {{ divider }}
                </option>
              </select>
            </a>
          </li>
          <li>
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
    isSettings () {
      return ['settings', 'profiles', 'global-settings'].includes(this.$ui.tabIx)
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
    }
  }
};
</script>