<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
import { CodeDiff } from 'v-code-diff'
</script>

<template>
  <div class="chat-entry flex gap-1 items-start relative reltive">
    <div class="grow overflow-auto">
      <div class="w-full flex flex-col gap-1 hover:rounded-md group">
        <div class="text-xs font-bold flex flex-col click">
          <div class="flex justify-start gap-4 items-center p-2" @dblclick.stop="toggleCollapse">
            <div v-for="profile in messageProfiles" :key="profile.name">
              <div class="avatar tooltip tooltip-bottom tooltip-right" :data-tip="profile.name">
                <div class="ring-primary ring-offset-base-100 w-6 h-6 rounded-full ring ring-offset-2">
                  <img :src="profile.avatar" :alt="profile.name" />
                </div>
              </div>
            </div>

            <div class="flex gap-2 grow">
              [{{ formatDate(message.updated_at) }}] <span v-if="timeTaken">({{ timeTaken }} s.)</span>
            </div>
            <div class="opacity-0 group-hover:opacity-100 flex gap-2 items-center justify-end">
              <div class="px-2 flex flex-col">
                <div class="gap-2 flex justify-end items-center">
                  <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="Copy message" @click="copyMessageToClipboard">
                    <i class="fa-solid fa-copy"></i>
                  </button>      
                  <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="View source" @click="toggleSrcView">
                    <i class="fa-solid fa-code"></i>
                  </button>
                  <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="View diff" @click="toggleShowDiff" v-if="message.diffMessage">
                    <i class="fa-regular fa-file-lines"></i>
                    <i class="fa-regular fa-file-lines text-primary -ml-1"></i>
                  </button>
                  <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="Edit message" @click="$emit('edit')" v-if="canEditMessage">
                    <i class="fa-solid fa-pencil"></i>
                  </button>
                  <button class="hidden btn btn-xs hover:btn-outline bg-secondary tooltip" data-tip="Enhance message" 
                    @click="$emit('enhance')">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                  </button>
                  <div class="dropdown dropdown-hover dropdown-end">
                    <button tabindex="0" class="btn hover:btn-error btn-xs" @click="onRemove">
                      <i class="fa-solid fa-bars"></i>
                    </button>
                    <ul tabindex="0" class="dropdown-content menu rounded-box shadow w-28 p-2 bg-base-300">
                      <li class="text-warning">
                        <a @click.stop="$emit('hide')" class="text-left tooltip tooltip-bottom click"
                            :data-tip="message.hide ? 'Click to add message to conversation' : 
                                              'Click to hide message from the conversation'">
                          {{ message.hide ? 'Show' : 'Hide' }}
                        </a>                  
                      </li>
                      <li class="text-error">
                        <a class="hover:underline" @click="confirmRemove">Delete</a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="message.think">
          <div class="chat chat-start click"
            @click="message.full_think = !message.full_think"
          >
            <div class="chat-bubble">
              <div class="badge badge-info badge-outline">think</div>
              {{ thinkText }}
              <div class="chat-footer opacity-50" v-if="message.is_thinking">
                <span class="loading loading-dots"></span>
              </div>
              <span class="underline" v-if="message.full_think">close</span>
            </div>
            
          </div>                
        </div>
        <div @copy.stop="onMessageCopy" :class="['max-w-full group border-slate-300/20', message.collapse ? 'max-h-40 overflow-hidden': 'h-fit', message.hide ? 'text-slate-200/20': '']">
          <pre v-if="srcView">{{ message.content }}</pre>
          <Markdown 
            :text="messageContent"
            @generate-code="onGenerateCode" 
            v-if="!showDiff && !srcView && !code_patches" />
          <CodeDiff
            :new-string="message.diffMessage.content"
            :old-string="messageContent"
            theme="dark"
            v-if="showDiff"
          />
          <div v-if="code_patches">
            <div class="mt-2 p-2 rounded-md flex flex-col gap-1 overflow-hidden" v-for="patch in code_patches" :key="patch.file_path">
              <div class="text-xs font-bold text-primary" :title="patch.file_path">
                {{ patch.file_path.replace($project.project_path, '') }}
              </div>
              <div class="">{{ patch.description }}</div>
              <Markdown :text="'```diff\n' + patch.patch + '\n```'"></Markdown>
              <div class="flex justify-end">
                <button class="btn btn-sm btn-warning" :disabled="patch.working" @click="applyPatch(patch)">
                  <span class="loading loading-spinner" v-if="patch.working"></span>
                  Apply changes
                </button>
              </div>
              <div v-if="patch.res">
                <div class="text-xs text-error" v-if="patch.res.error">{{ patch.res.error }}</div>
                <div class="text-xs text-success" v-else>Patch applied</div>
              </div>
            </div>
          </div>
          <div class="chat-footer opacity-50" v-if="message.content && !message.done">
            <span class="loading loading-dots"></span>
          </div>
          <div v-if="images">
            <div class="carousel gap-2" v-if="images?.length">
              <div class="carousel-item click mt-2" v-for="image in images" :key="image.src" @click="$emit('image', image)" :alt="image.alt" :title="image.alt">
                <div class="flex flex-col">
                  <div class="bg-contain bg-no-repeat bg-center border rounded-md w-12 h-12 md:h-20 md:w-20" :style="`background-image: url(${image.src})`"></div>
                  <p class="badge badge-xs" v-if="image.alt">{{ image.alt.slice(0, 10) }}</p>
                </div>
              </div>
            </div>
          </div>
          <div class="font-bold text-xs flex flex-col gap-2 mt-2" v-if="message.files?.length">
            Linked files:
            <div v-for="file in message.files" :key="file" :title="file" class="flex gap-2 items-center click">
              <div class="flex gap-2 click hover:underline" @click="openFile(file)">
                <div class="click tooltip tooltip-right" data-tip="Attach file" @click.stop="$emit('add-file-to-chat', file)">
                  <i class="fa-solid fa-file-arrow-up"></i>
                </div>
                <div class="overflow-hidden">
                  {{ file.split('/').reverse()[0] }}
                </div>
              </div>
              <div class="click hover:text-error" @click.stop="$emit('remove-file', file)">
                <i class="fa-regular fa-circle-xmark"></i>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['chat', 'message'],
  data() {
    return {
      srcView: false,
      isRemove: false,
      improvementData: null,
      showDiff: false
    }
  },
  computed: {
    isMyMessage() {
      return this.message.user === this.$user.username
    },
    isChannelMessage() {
      return this.chat.mode === 'channel'
    },
    canEditMessage() {
      return !this.isChannelMessage ||
        this.isMyMessage ||
        this.message.role === 'assistant'
    },
    thinkText () {
      const { full_think, is_thinking, think } = this.message 
      return (full_think || is_thinking) 
        ? think : `${think.slice(0, 50)}...`
    },
    messageProfiles() {
      let profiles = this.$projects.profiles.filter(p => this.message.profiles?.includes(p.name))
      const user = this.$project.users.find(({ username }) => username === this.message.user)
      return [user, ...profiles].filter(u => !!u)
    },
    html() {
      if (!this.showDoc) {
        try {
          return this.md.render(this.message.content)
        } catch (ex) {
          console.error("Message can't be rendered", this.message)
        }
      }
      return this.showDocPreview
    },
    showDocPreview() {
      return this.md.render("```json\n" + JSON.stringify(this.message, null, 2) + "\n```")
    },
    images() {
      return this.message?.images?.map(i => {
        try {
          return JSON.parse(i)
        } catch {
          return { src: i }
        }
      })
    },
    messageContent() {
      const { content } = this.message
      return content
    },
    selection () {
      return document.getSelection().toString()
    },
    code_changes () {
      return this.improvementData?.code_changes
    },
    code_patches () {
      return this.improvementData?.code_patches
    },
    timeTaken () {
      if (!this.message.meta_data?.time_taken) {
        return null
      }
      const seconds = Math.floor(this.message.meta_data.time_taken)
      const baseMoment = moment({h:0, m:0, s:0, ms:0})
      return `${this.message.meta_data.model} ${baseMoment.add(seconds, 'seconds').format("mm:ss")}`
    },
    chatProject() {
      if (this.chat.project_id) {
        return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id)
      }
      return this.$project
    }
  },
  methods: {
    formatDate(date) {
      return moment(date).format('DD/MMM HH:mm:ss')
    },
    extractImprovementData() {
      this.improvementData = null
      if (this.message.content?.includes("```json")) {
        try {
          const jsBlock = this.message.content.split("```json")[1].split("```")[0]
          this.improvementData = JSON.parse(jsBlock)
        } catch (ex) {
          console.error("Failed to parse improvement data", ex)
        }
      }
    },
    copyTextToClipboard(text) {
      this.$ui.copyTextToClipboard(text)
    },
    onMessageCopy(ev) {
      const text = window.getSelection().toString()
      if (text) {
        this.copyTextToClipboard(text)
        ev.preventDefault()
      }
    },
    toggleCollapse() {
      this.message.collapse = !this.message.collapse
    },
    toggleSrcView() {
      if (this.srcView = !this.srcView) {
        this.showDiff = false
        this.message.collapse = false
      }
    },
    toggleShowDiff() {
      if (this.showDiff = !this.showDiff) {
        this.srcView = false
        this.message.collapse = false
      }
    },
    onRemove() {
      if (this.isRemove) {
        this.$emit('remove')
      } else {
        this.isRemove = true
      }
    },
    confirmRemove() {
      this.isRemove = true
      this.$emit('remove')
    },
    cancelRemove() {
      this.isRemove = false
    },
    copyMessageToClipboard() {
      this.copyTextToClipboard(this.message.content)
    },
    async applyPatch(patch) {
      patch.working = true 
      try {
        const code_changes = this.code_changes.filter(cc => cc.file_path === patch.file_path)
        await this.$projects.codeImprovePatch({ chat: this.chat, code_generator: { code_changes, code_patches: [ patch ] } })
        patch.res = {
          info: "Patch sent, please check events for updates"
        }
      } catch {
        patch.res = { info: "", error: "Error aplaying patch" }
      }
      delete patch.working
    },
    onGenerateCode(codeBlockInfo) {
      this.$emit('generate-code', codeBlockInfo)
    },
    openFile(file) {
      this.$ui.openFile(file)
    }
  },
  mounted() {
    this.message.collapse = this.message.hide
    this.extractImprovementData()
  }
}
</script>