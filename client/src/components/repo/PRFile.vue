<script setup>
import "@git-diff-view/vue/styles/diff-view.css"
import { DiffView, DiffModeEnum } from "@git-diff-view/vue"
import CodeComment from "./CodeComment.vue"
import Chat from "../chat/Chat.vue"
import CodeViewer from "../CodeViewer.vue"
import ChatEntry from "../ChatEntry.vue"
import ProfileViewer from '../profiles/ProfileViewer.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
</script>
<template>
  <div class="grow flex flex-col gap-2 border-2 border-slate-600 rounded-md py-1" :key="file.fileFullName">
    <div class="px-1 flex gap-2 items-center border-slate-600 w-full">
      <div class="flex flex-col gap-1 grow"
        :class="file.selected && 'text-warning'"
      >
        <div class="click flex gap-2 items-center truncate" :title="file.fileFullName" 
          @click="$ui.openFile(file.fileFullName)">
          <button @click.stop="file.collapse = !file.collapse">
            <i class="fa-solid fa-chevron-up" v-if="file.collapse"></i>
            <i class="fa-solid fa-chevron-down" v-else></i>
          </button>
          <span 
            @click.stop="file.selected = !file.selected"
            v-if="!file.profiles.length"  
          >
            <i class="w-5 h-5 fa-regular fa-file-lines"></i>
          </span>
          <div class="avatar-group -space-x-2" v-else>
            
            <div class="avatar" :title="profile.name" v-for="profile in file.profiles" :key="profile.name"
              @click.stop="toggleProfile(profile)"
            >
              <div class="w-5">
                <img :src="profile.avatar" />
              </div>
            </div>
          </div>
          <span :class="[file.isDeleted && 'text-error', file.isNewFile && 'text-success']">
            {{ file.title }}
          </span>
          {{ changes?.length }}
        </div>
      </div>
      <div class="grow"></div>
      <div class="text-error text-xs" v-if="!file.parsed">
        --no diff available--
      </div>

      <div class="dropdown dropdown-left" @click.stop="">
        <div tabindex="0" class="click border rounded-lg text-sm px-2 py-1"
          :class="`border-[${file.column?.color || 'gainsboro'}] text-[${file.column?.color || 'gainsboro'}]`">
          {{  file.column?.title || '...'  }}
        </div>
        <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-20 p-2 shadow-sm">
          <li v-for="column in columns" 
            :key="column.title"
            class="mb-2 text-sm border rounded-lg"
            :class="`border-[${column?.color || 'gainsboro'}] text-[${column?.color || 'gainsboro'}]`"
            @click="$emit('chat-column', { file, column: column.title})"
            >
            <a>{{ column.title }}</a>
          </li>
        </ul>
      </div>


      <button class="btn btn-sm btn-sm btn-outline tooltip" data-tip="Last comment" 
        :class="showMessage && 'btn-warning'"
        @click="showOption = 'message'" 
        v-if="file.chat"
      >
        <i class="fa-solid fa-message"></i>
      </button>
      
      <div class="indicator" v-if="file.chat"
        @click="showOption = 'chat'"
      >
        <span class="indicator-item indicator-end badge badge-secondary"
          v-if="showChat"
        >
          <span class="click" @click.stop="$projects.setActiveChat(file.chat)"
            v-if="file.chat && showChat">
            <i class="fa-solid fa-arrow-up-right-from-square"></i>
          </span>
         <span v-if="file.messageCount">{{ file.messageCount }}</span> 
        </span>
        <button class="btn btn-sm btn-outline" :class="showChat && 'btn-warning'"><i class="fa-regular fa-comment-dots"></i></button>
      </div>
      <button class="btn btn-sm btn-outline tooltip border-dashed text-slate-500" data-tip="Start revision" 
        @click="onShowChat(file)" v-else>
        <i class="fa-solid fa-comments"></i>
      </button>
      
      <button class="btn btn-sm btn-sm btn-outline tooltip" data-tip="File changes"
        :class="showDiff && 'btn-warning'"
        @click="showOption = 'diff'" 
        disabled="!file.parsed || file.isNewFile">
        <i class="fa-solid fa-code-merge"></i>
      </button>

      <button class="btn btn-sm btn-sm btn-outline tooltip" data-tip="File content"
        :class="showFile && 'btn-warning'"
        @click="showOption = 'file'">
        <i class="fa-solid fa-file-lines"></i>
      </button>

    </div>
    <VerticalSplitter class="grow flex h-full" 
      :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
      v-if="!file.collapse">
      <template v-slot:left>
        <ChatEntry :message="lastMessage" :menu-less="true" v-if="showMessage" />
        <div class="grow overflow-auto" v-if="file.parsed && showDiff">
          <div class="flex items-center gap-2 px-2 py-1 text-xs">
            <div class="flex gap-2 items-center">
              Split / Unified
              <input type="checkbox" v-model="diffSplit" class="toggle toggle-sm" />
            </div>
            <div class="flex gap-2 items-center">
              Text wrap
              <input type="checkbox" v-model="diffWrap" class="toggle toggle-sm" />
            </div>
          </div>
          <DiffView
            :data="file"
            :diff-view-theme="'dark'" 
            :diff-view-add-widget="true"
            :diff-view-wrap="diffWrap"
            :diff-view-highlight="true"
            :diffViewFontSize="10"
            :diffViewMode="diffSplit ? DiffModeEnum.Split : DiffModeEnum.Unified"          
          >
            <template #widget="{ onClose, lineNumber, side }">
              <div class="flex w-full pr-4 flex-col m-2">
                <CodeComment @close="onClose" @save="[onClose(), onAddComment({ lineNumber, side, message: $event })]" />
              </div>
            </template>
            <template #extend="{ data }">
              <div class="flex border bg-slate-400 px-[10px] py-[8px]">
                <h2 class="text-[20px]">>> {{ data }}</h2>
              </div>
            </template>
          </DiffView>
        </div>
        <div class="p-2" v-if="theChat && showChat">
          <Chat class="overflow-auto min-h-96" 
            :chat="theChat" 
            :enableDelete="true"
            :readOnly="false"
          />
        </div>
        <CodeViewer class="overflow-auto mb-20 p-2" 
          :code="fileContent"
          :language="file.extension"
          :file="file.fileFullName" 
          :diffOption="false"
          v-if="showFile && fileContent" />
      </template>
      <template v-slot:right v-if="selectedProfile">
        <div class="max-h-[1024px] overflow-auto">
          <ProfileViewer :profile="selectedProfile"  />
        </div>
      </template>
    </VerticalSplitter>
  </div>
</template>
<script>
export default {
  props: ['file', 'option', 'columns'],
  data() {
    return {
      showOption: this.option || 'diff',
      fileContent: null,
      diffSplit: false,
      diffWrap: true,
      selectedProfile: null
    }
  },
  created() {
    if (this.showOption === 'diff' && this.file.isNewFile) {
      this.loadFileContent()
    }
  },
  computed: {
    showMessage() {
      return this.showOption === 'message' && 
        this.file.chat &&
        this.lastMessage
    },
    showChat() {
      return this.showOption === 'chat'
    },
    showFile() {
      return this.showOption === 'file'
    },
    showDiff() {
      return this.showOption === 'diff'
    },
    lastMessage() {
      return this.theChat?.messages.reverse().find(m => !m.hide)
    },
    changes() {
      return this.file.diff?.split("\n")
              .filter(l => ["+", "-"].includes(l[0]) )
    },
    theChat() {
      return this.$projects.allChats.find(c => c.id === this.file.chat?.id)
    }
  },
  watch: {
    option(newVal) {
      this.showOption = newVal
    },
    file() {
      this.showFile && this.loadFileContent()
    },
    showOption(newVal) {
      newVal === 'file' && this.loadFileContent()
      newVal === 'chat' && this.onShowChat()
    }
  },
  methods: {
    onShowChat() {
      if (!this.file.chat) {
        this.$emit('new-chat', this.file)
      }
      this.showOption = 'chat'
    },
    async loadFileContent() {
      this.fileContent = await this.$storex.api.files.read(this.file.fileFullName)
      this.showOption = 'file'
    },
    toggleProfile(profile) {
      if (this.selectedProfile === profile) {
        profile = null
      }
      this.selectedProfile = profile
    },
    onAddComment({ lineNumber, side, message, metadata }) {
      this.$emit('new-chat', { file: this.file, message, metadata })
    }
  },
  expose: ['file']
}
</script>