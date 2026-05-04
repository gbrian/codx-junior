<script setup>
import moment from 'moment'
import ProjectDetailt from './ProjectDetailt.vue';
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center"
      :class="[
        $storex.session.connected ? '' : 'grayscale text-error',
      ]">

      <ProjectDetailt @click.stop=""
          :options="{ folders: true, showIcon: true }"
          @select="$projects.setActiveProject($event)"
        />
      
      <div class="grow"></div>
        
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
  props: [],
  data() {
    return {
      isCollapsed: false,
      tabActive: 'text-info bg-base-100',
      tabInactive: 'text-warning bg-base-300 opacity-50 hover:opacity-100',
      restartModal: false,
      chat: null,
      showMobileMenu: false,
      newProject: false,
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
  },
  methods: {
    setActiveTab(tab) {
      this.$ui.setActiveTab(tab)
    },
    setActiveProject(project) {
      this.$projects.setActiveProject(project)
    },
    async newQuickChat() {
      await this.$chats.createNewChat({ temp: true })
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