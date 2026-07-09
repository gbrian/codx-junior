<script setup>
import CodeViewer from "../CodeViewer.vue"
import ChatEntry from "../ChatEntry.vue"
import ProfileViewer from '../profiles/ProfileViewer.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
</script>

<template>
  <div class="grow flex flex-col gap-2 border-2 border-slate-600 rounded-md py-1" :key="file.fileFullName">
    <!-- Header Controls -->
    <div class="px-1 flex gap-2 items-center border-slate-600 w-full">
      <div class="flex flex-col gap-1 grow"
        :class="file.selected && 'text-warning'"
      >
        <div class="click flex gap-2 items-center truncate" 
          :title="file.fileFullName" 
          @click="$ui.openFile(file.fileFullName)">
          <button @click.stop="toggleCollapse">
            <i class="fa-solid fa-chevron-up" v-if="file.collapse"></i>
            <i class="fa-solid fa-chevron-down" v-else></i>
          </button>
          
          <!-- Profiles or file icon -->
          <span v-if="!file.profiles.length" @click.stop="file.selected = !file.selected">
            <i class="w-5 h-5 fa-regular fa-file-lines"></i>
          </span>
          <div class="avatar-group -space-x-2" v-else>
            <div class="avatar" :title="profile.name" 
              v-for="profile in file.profiles" :key="profile.name"
              @click.stop="toggleProfile(profile)">
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

      <!-- Error state -->
      <div class="text-error text-xs" v-if="!file.parsed">
        --no diff available--
      </div>

      <!-- Column selector dropdown -->
      <div class="dropdown dropdown-left" @click.stop="">
        <div tabindex="0" 
          class="click border rounded-lg text-sm px-2 py-1 max-w-32 overflow-hidden text-nowrap text-ellipsis"
          :title="file.column?.title"
          :class="`border-[${file.column?.color || 'gainsboro'}] text-[${file.column?.color || 'gainsboro'}]`">
          <i class="fa-solid fa-table-columns"></i> {{  file.column?.title || '...'  }}
        </div>
        <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-20 p-2 shadow-sm">
          <li v-for="column in columns" 
            :key="column.title"
            class="mb-2 text-sm border rounded-lg overflow-hidden text-nowrap text-ellipsis"
            :class="`border-[${column?.color || 'gainsboro'}] text-[${column?.color || 'gainsboro'}]`"
            @click="$emit('chat-column', { file, column: column.title})"
            >
            <a class="overflow-hidden text-nowrap text-ellipsis">
              <i class="fa-solid fa-table-columns"></i> {{ column.title }}
            </a>
          </li>
        </ul>
      </div>

      <!-- Chat button -->
      <div class="indicator" v-if="file.chat" @click="navigateToChat">
        <button class="btn btn-sm btn-outline" :class="showChat && 'btn-warning'">
          <i class="fa-regular fa-comment-dots"></i>
        </button>
      </div>
      <button class="btn btn-sm btn-outline tooltip border-dashed text-slate-500" 
        data-tip="Start revision" 
        @click="onShowChat" v-else>
        <i class="fa-solid fa-comments"></i>
      </button>
    </div>

    <!-- Content area with splitter -->
    <VerticalSplitter class="grow flex h-full min-h-96" 
      :panels="{ left: { defaultSize: 60 }, right: { defaultSize: 40 }}"
      v-if="file.collapse === true">
      
      <template v-slot:left>
        <div class="@container/prfile grow overflow-auto">
          <div class="flex flex-col @xl/prfile:flex-row h-full">
            <!-- CodeViewer delegates all file operations -->
            <CodeViewer class="grow overflow-auto mb-20 p-2 border-none" 
              :code="fileContent"
              :language="file.extension"
              :file="file.fileFullName"
              :finished="true"
              :diffOption="false"
              :showCodeOpened="true"
              :message="message"
              :fromBranch="fromBranch"
              :toBranch="toBranch"
              :project="chatProject"
              @save-file="onSaveFile"
              @message-change="onMessageChange"
              @sub-task="onCreateSubTask"
              v-if="fileContent" />

            <!-- Review message display -->
            <ChatEntry :chat="file.chat" :message="review" v-if="showChat && review" />
          </div>
        </div>
      </template>

      <!-- Profile panel -->
      <template v-slot:right v-if="selectedProfile">
        <div class="max-h-[1024px] overflow-auto">
          <ProfileViewer :profile="selectedProfile" />
        </div>
      </template>
    </VerticalSplitter>
  </div>
</template>

<script>
export default {
  props: ['prChat', 'file', 'columns', 'fromBranch', 'toBranch'],
  emits: ['chat-column', 'new-chat'],
  data() {
    return {
      fileContent: null,
      selectedProfile: null,
      showChat: false
    }
  },
  created() {
    if (this.file.chat) {
      this.$chats.loadChat(this.file.chat)
    }
  },
  computed: {
    changes() {
      return this.file.diff?.split("\n")
        .filter(l => ["+", "-"].includes(l[0]))
    },
    theChat() {
      return this.$projects.allChats.find(c => c.id === this.file.chat?.id)
    },
    review() {
      return this.file.chat?.messages
        .filter(m => !m.hide && m.task_item === 'review')
        .reverse()[0]
    },
    message() {
      return { doc_id: this.file.chat?.id }
    },
    chatProject() {
      return this.$storex.projects.allProjectsById[this.prChat?.project_id]
        || this.$projects.allProjectsById[this.prChat?.owner_project_id]
        || this.$project
    }
  },
  watch: {
    file() {
      this.loadFileContent()
    }
  },
  methods: {
    async loadFileContent() {
      try {
        this.fileContent = null
        const { content } = await this.$storex.api.files.read(this.file.fileFullName)
        this.fileContent = content
      } catch (error) {
        console.error('Failed to load file content:', error)
      }
    },

    toggleCollapse() {
      this.file.collapse = !this.file.collapse
      if (!this.fileContent) {
        this.loadFileContent()
      }
    },

    toggleProfile(profile) {
      this.selectedProfile = this.selectedProfile === profile ? null : profile
    },

    async onShowChat() {
      if (!this.file.chat) {
        await this.$emit('new-chat', { file: this.file })
      }
      this.showChat = !this.showChat
    },

    async navigateToChat() {
      await this.$chats.setActiveChat(this.file.chat)
    },

    async onSaveFile({ file, content }) {
      await this.$storex.api.files.write(file, content)
    },

    async onMessageChange({ orgContent, newContent }) {
      if (this.fileContent === orgContent) {
        this.fileContent = newContent
      }
    },

    onCreateSubTask({ file, content }) {
      this.$emit('new-chat', { file: this.file, content })
    }
  },
  expose: ['file']
}
</script>