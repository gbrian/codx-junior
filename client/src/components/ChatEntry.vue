<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
import { CodeDiff } from 'v-code-diff'
</script>

<template>
  <div class="relative flex flex-col gap-1 w-full hover:rounded-md p-2 group">
    <div class="text-xs font-bold flex justify-between">
      <div class="flex justify-start gap-2">
        [{{ formatDate(message.updated_at) }}] <span v-if="timeTaken">({{ timeTaken }} s.)</span>
        <div>
          <div class="text-primary" v-if="message.role === 'user'">You</div>
          <div class="text-secondary" v-else>codx-junior</div>
        </div>
      </div>
      <div class="flex gap-2 items-center justify-end relative grow">
        <div class="opacity-0 group-hover:opacity-100 flex flex-col absolute right-0 top-0">
          <div class="gap-2 flex justify-end items-center">
            <div class="tooltip tooltip-bottom click"
              :data-tip="message.hide ? 'Click to add message to conversation' : 
                                        'Click to hide message from the conversation'"
              :checked="!message.hide" @click.stop="$emit('hide')"
              >
              <i class="fa-solid fa-eye" v-if="message.hide"></i>
              <i class="text-warning fa-solid fa-eye-slash" v-else></i>
            </div>  
            <button class="btn btn-xs tooltip tooltip-bottom" data-tip="Expand/Collapse" @click="toggleCollapse">
              <span v-if="message.collapse">
                <i class="fa-solid fa-chevron-up"></i>
              </span>
              <span v-else>
                <i class="fa-solid fa-chevron-down"></i>
              </span>
            </button>
            <button class="btn btn-xs hover:btn-outline bg-base-100 tooltip tooltip-bottom" data-tip="Copy message" @click="copyMessageToClipboard">
              <i class="fa-solid fa-copy"></i>
            </button>      
            <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="View source" @click="toggleSrcView">
              <i class="fa-solid fa-code"></i>
            </button>
            <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="View diff" @click="toggleShowDiff" v-if="message.diffMessage">
              <i class="fa-regular fa-file-lines"></i>
              <i class="fa-regular fa-file-lines text-primary -ml-1"></i>
            </button>
            <button class="btn btn-xs hover:btn-outline tooltip tooltip-bottom" data-tip="Edit message" @click="$emit('edit')">
              <i class="fa-solid fa-pencil"></i>
            </button>
            <button class="hidden btn btn-xs hover:btn-outline bg-secondary tooltip" data-tip="Enhance message" 
              @click="$emit('enhance')">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
            </button>
            <div class="dropdown dropdown-hover dropdown-end">
              <button tabindex="0" class="btn hover:btn-error btn-xs" @click="onRemove">
                <i class="fa-solid fa-trash"></i>
                <span v-if="isRemove"> Confirm </span>
              </button>
              <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box shadow w-28 p-2">
                <li>
                  <a class="hover:underline" @click="confirmRemove">Yes</a>
                </li>
                <li>
                  <a class="hover:underline" @click.stop="cancelRemove">No</a>
                </li>
              </ul>
            </div>
          </div>
          <div class="flex justify-end">
            <div>{{ message.profiles?.join(',') }}</div>
          </div>
        </div>
      </div>
    </div>
    <div :class="['max-w-full group w-full border-slate-300/20', message.collapse ? 'max-h-40 overflow-hidden': 'h-fit', message.hide ? 'text-slate-200/20': '']">
      <div @copy.stop="onMessageCopy">
        <pre v-if="srcView">{{ message.content }}</pre>
        <Markdown 
          :text="messageContent"
          @generate-code="onGenerateCode" 
          v-if="!showDiff && !srcView && !code_patches" />
        <CodeDiff
          :old-string="message.diffMessage.content"
          :new-string="messageContent"
          theme="dark"
          v-if="showDiff"
        />
        <div v-if="code_patches">
          <div class="mt-2 p-2 bg-base-100 rounded-md flex flex-col gap-1 overflow-hidden" v-for="patch in code_patches" :key="patch.file_path">
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
        <div v-if="images">
          <div class="carousel gap-2">
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
            <div class="flex gap-2 click hover:underline" @click="$ui.openFile(file)">
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
      return `${this.message.meta_data.model} ${moment().add(Math.floor(this.message.meta_data.time_taken), 'seconds').format("mm:ss")}`
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
    }
  },
  mounted() {
    this.message.collapse = this.message.hide
    this.extractImprovementData()
  }
}
</script>