<script setup>
import "@git-diff-view/vue/styles/diff-view.css";
import { DiffView } from "@git-diff-view/vue";
import CodeComment from "./CodeComment.vue";
import Chat from "../chat/Chat.vue";
import CodeViewer from "../CodeViewer.vue";
</script>
<template>
  <div class="grow flex flex-col gap-2 h-full" :key="file.fileFullName">
    <div class="flex gap-2 text-xl py-2 items-center">
      <div class="flex flex-col gap-1 grow"
        :class="file.selected && 'text-warning'"
      >
        <div class="click flex gap-2 items-center truncate" :title="file.fileFullName" 
          @click="$ui.openFile(file.fileFullName)">
          <span 
            @click.stop="file.selected = !file.selected"
            v-if="!file.profiles.length"  
          >
            <i class="w-5 h-5 fa-regular fa-file-lines"></i>
          </span>
          <div class="avatar-group -space-x-2" v-else>
            
            <div class="avatar" :title="profile.name" v-for="profile in file.profiles" :key="profile.name">
              <div class="w-5">
                <img :src="profile.avatar" />
              </div>
            </div>
          </div>
          <span :class="[file.isDeleted && 'text-error', file.isNewFile && 'text-success']">
            {{ file.title }}
          </span>
          <div class="text-xs w-fit" :class="`text-[${file.column.color}]`"  v-if="file.column">
            ( {{  file.column.title  }} )
          </div> 
        </div>
      </div>
      <div class="grow"></div>
      <div class="text-error text-xs" v-if="!file.parsed">
        --no diff available--
      </div>

      <button class="btn btn-sm btn-sm btn-outline" 
        :class="showFile && 'btn-warning'"
        @click="showOption = 'file'">
        <i class="fa-solid fa-file-lines"></i>
      </button>

      <div class="indicator" v-if="file.chat"
        @click="showOption = 'chat'"
      >
      <span class="indicator-item indicator-end badge badge-secondary">
          {{ file.messageCount }}
        </span>
        <button class="btn btn-sm btn-outline" :class="showChat && 'btn-warning'"><i class="fa-regular fa-comment-dots"></i></button>
      </div>
      <button class="btn btn-sm btn-outline tooltip" data-tip="Review changes" 
        :class="file.chat && 'border bg-sky-600'"
        @click="showOption = 'chat'" v-else>
        <i class="fa-solid fa-comments"></i>
      </button>
      
      <button class="btn btn-sm btn-sm btn-outline" 
        :class="showDiff && 'btn-warning'"
        @click="showOption = 'diff'" 
        v-if="file.parsed">
        <i class="fa-solid fa-code-merge"></i>
      </button>

    </div>
    <div class="grow overflow-auto">
      <DiffView
        :data="file"
        :diff-view-theme="'dark'" 
        :diff-view-add-widget="false"
        :diff-view-wrap="true"
        v-if="file.parsed && showDiff"
      >
        <template #widget="{ onClose, lineNumber, side }">
          <div class="absolute z-[100] top-0 left-0 right-0 bottom-0 bg-base-300">
            <div class="flex flex-col items-center justify-center w-full h-full">
              <CodeComment 
                @close="onClose"
                @save="onAddComment($event, file, lineNumber, side, onClose)"
              />
            </div>
          </div>
        </template>
        <template #extend="{ data }">
          <div class="flex border bg-slate-400 px-[10px] py-[8px]">
            <h2 class="text-[20px]">>> {{ data }}</h2>
          </div>
        </template>
      </DiffView>
    </div>
    <Chat class="h-full overflow-auto mb-20" 
      :chat="file.chat" 
      v-if="file.chat && showChat" />
    <CodeViewer class="h-full overflow-auto mb-20" 
      :code="fileContent"
      :language="file.extension"
      :file="file.fileFullName" 
      :diffOption="false"
      v-if="showFile && fileContent" />
  </div>
</template>
<script>
export default {
  props: ['file'],
  data() {
    return {
      showOption: 'diff',
      fileContent: null
    }
  },
  mounted() {
  },
  computed: {
    showChat() {
      return this.showOption === 'chat'
    },
    showFile() {
      return this.showOption === 'file'
    },
    showDiff() {
      return this.showOption === 'diff'
    },
  },
  watch: {
    file() {
      this.showFile && this.loadFileContent()
    },
    showOption(newVal) {
      newVal === 'file' && this.loadFileContent()
      newVal === 'chat' && this.onShowChat()
    }
  },
  methods: {
    onFileComment(file, message) {
      this.$emit('comment', { file, message })
    },
    onShowChat() {
      if (!this.file.chat) {
        this.onFileComment(this.file, "Review file changes, fix errors and suggest improvements. Return just a list of changes. Add examples for complex changes.")
      }
    },
    async loadFileContent() {
      this.fileContent = await this.$storex.api.files.read(this.file.fileFullName)
    }
  }
}
</script>