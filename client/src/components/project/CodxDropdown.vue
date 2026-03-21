<script setup>
import moment from 'moment'
import Chat from '../chat/Chat.vue'
</script>
<template>
  <div class="dropdown dropdown-end dropdown-left"
    :class="[ focused && 'dropdown-open']"
    @click="handleFocusOut"
  >
    <div tabindex="0" role="button" class="click">
      <div class="w-6 md:w-8 ring rounded-full"
        :class="[ focused && 'ring ring-offset-2 ring-info']"
      >
        <img :src="$storex.api.user.avatar" />
      </div>
    </div>
    <ul
      tabindex="-1"
      class="dropdown-content menu border bg-base-100 rounded-box z-1 w-[600px] p-2 shadow-sm mr-2"
      :class="[ focused && 'border-info']"
      >
      <div>
        <div class="grow flex flex-col gap-1 h-[600px] pb-2" 
          @click.stop=""
          @focusin.stop="handleFocusIn"
          v-if="chat">
          <div class="flex gap-2 items-center px-1">
            <span class="font-bold">{{ chat.name }}</span>
            <span class="grow"></span>
            <span class="text-xs">[{{ moment(chat.updated_at || chat.created_at).fromNow() }}]</span>
            <span class="click" @click="openChat">
              <i class="fa-solid fa-arrow-up-right-from-square"></i>
            </span>
          </div>
          <Chat class="h-full" :chat="chat" />
        </div>
      </div>
      <ul class="flex gap-2 items-center w-full px-2 overflow-hidden shrink-0">
        <li class="mr-4">
          <a
            class="flex gap-1 tooltip tooltip-right click"
            data-tip="New chat"
            @click.stop="newQuickChat">
            <i class="fa-regular fa-comment"></i>
          </a>
        </li>
        <li>
          <a
            class="flex gap-1 tooltip tooltip-right click"
            data-tip="Account settings"
            @click.stop="setActiveTab('account')">
            <i class="fa-regular fa-circle-user"></i>
          </a>
        </li>
        <li v-if="$project && $storex.api.permissions.isProjectAdmin">
          <a
            class="flex gap-1 tooltip tooltip-right click"
            data-tip="Project settings"
            @click.stop="setProjectTab('settings')">
            <i class="fa-solid fa-sliders"></i>
          </a>
        </li>
        <li v-if="$project && $storex.api.permissions.isProjectAdmin">
          <a
            class="flex gap-1 tooltip tooltip-right click"
            data-tip="Knowledge settings"
            @click.stop="setProjectTab('knowledge_settings')">
            <i class="fa-solid fa-book"></i>
          </a>
        </li>
        <li v-if="$storex.api.permissions.isAdmin">
          <a
            class="flex gap-1 tooltip tooltip-right click"
            data-tip="Global settings"
            @click.stop="setActiveTab('global-settings')">
            <i class="fa-solid fa-gear"></i>
          </a>
        </li>
        <li v-if="$storex.api.permissions.isAdmin">
          <a
            class="flex gap-1 tooltip tooltip-right click"
            data-tip="Logs"
            @click="$ui.toggleLogs()">
            <i class="fa-solid fa-chart-line"></i>
          </a>
        </li>
        <li class="ml-4">
          <a class="flex items-center gap-2 tooltip select select-sm" data-tip="Voice language">
            <i class="fa-solid fa-microphone-lines"></i>
            <select
              class="select select-sm select-ghost"
              @change="$ui.setVoiceLanguage($event.target.value)">
              <option
                v-for="key, lang in $ui.voiceLanguages"
                :key="lang"
                :selected="$ui.voiceLanguage === lang"
                :value="lang">
                {{ key }}
              </option>
            </select>
          </a>
        </li>
        <li class="grow"></li>
        <li>
          <a
            class="flex gap-1 tooltip text-error"
            data-tip="Log out"
            @click.stop="$users.logout()">
            <i class="fa-solid fa-right-from-bracket"></i>
          </a>
        </li>
      </ul>
    </ul>
  </div>
</template>
<script>
export default {
  data() {
    return {
      lastQuickChat: null,
      showMenu: false,
      focused: false
    }
  },
  created() {
    this.lastQuickChat = this.getLastQuickChat() || this.newQuickChat()
  },
  computed: {
    chat() {
      return this.$projects.allChats.find(c => c.id === this.lastQuickChat)
    },
    menu() {
      return this.$refs?.menu
    }
  },
  methods: {
    getLastQuickChat() {
      return this.$projects.allChats
        .filter(c => c.board === 'Quick chats')
        .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)[0]?.id
    },
    setActiveTab(tab) {
      this.$ui.setActiveTab(tab)
    },
    setProjectTab(tab) {
      if (this.$project) {
        this.setActiveTab(tab)
      } else {
        this.$session.onError("No project selected")
      }
    },
    async newQuickChat() {
      const chat = {
        name: "Quick chat",
        board: "Quick chats",
        column: moment().format("YYYYMMDD"),
        mode: 'chat'
      }
      await this.$projects.createNewBoardChat({ chat })
      this.lastQuickChat = this.getLastQuickChat()
    },
    openChat() {
      this.$projects.setActiveChat(this.chat)
      this.$ui.showTab('tasks')
    },
    toggleMenu() {
      this.showMenu = !this.menu
      if (this.showMenu) {
        setTimeout(() => this.menu.focus(), 500)
      }
    },
    handleFocusIn() {
      this.focused = true
    },
    handleFocusOut() {
      this.focused = false
    }
  }
}
</script>
```
