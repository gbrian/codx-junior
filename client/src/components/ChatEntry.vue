<script setup>
import { API } from '../api/api'
import Markdown from './Markdown.vue'
import moment from 'moment'
import { full as emoji } from 'markdown-it-emoji'
import highlight from 'markdown-it-highlightjs'
import MarkdownIt from 'markdown-it'
</script>

<template>
  <div :class="['relative w-full hover:rounded-md', message.role === 'user' ? 'chat-start': 'chat-end']">
    <div class="text-xs font-bold">{{ formatDate(message.updated_at) }}</div>
    <div :class="['max-w-full group w-full prose-xs border-slate-300/20', message.collapse ? 'max-h-40 overflow-hidden': 'h-fit', message.hide ? 'text-slate-200/20': '']">
      <div @copy.stop="onMessageCopy">
        <div class="flex gap-2 items-center">
          <div :class="['btn btn-sm btn-outline flex gap-2 items-center font-bold text-xs rounded-md', message.role === 'user' ? 'bg-base-300' :'bg-secondary/80 text-secondary-content']">
            <div class="click" @click="$emit('hide')">
              <span class="text-warning" v-if="message.hide">
                <i class="fa-solid fa-eye-slash"></i>
              </span>
              <span v-else>
                <i class="fa-solid fa-eye"></i>
              </span>
            </div>
            <div>
              <div v-if="message.role === 'user'">You</div>
              <div v-else>codx-junior</div>
            </div>
          </div>
          <div class="opacity-20 group-hover:opacity-100 md:opacity-100 gap-2 flex w-full">
            <button class="btn btn-xs" @click="toggleCollapse">
              <span v-if="message.collapse">
                <i class="fa-solid fa-chevron-up"></i>
              </span>
              <span v-else>
                <i class="fa-solid fa-chevron-down"></i>
              </span>
            </button>
            <button class="btn btn-xs bg-base-100" @click="copyMessageToClipboard">
              <i class="fa-solid fa-copy"></i>
            </button>      
            <button class="btn btn-xs" @click="toggleSrcView">
              <i class="fa-solid fa-code"></i>
            </button>
            <button class="btn btn-xs bg-success" @click="$emit('edit')">
              <i class="fa-solid fa-pencil"></i>
            </button>
            <button class="hidden btn btn-xs bg-secondary" @click="$emit('enhance')">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
            </button>
            <div class="grow"></div>
            <div class="dropdown dropdown-hover dropdown-end">
              <button tabindex="0" class="btn btn-error btn-xs" @click="onRemove">
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
        </div>
        <pre v-if="srcView">{{ message.content }}</pre>
        <Markdown :text="messageContent" v-if="!srcView && !improvementData" />
        <div v-if="improvementData">
          <div class="mt-2 p-2 bg-base-100 rounded-md flex flex-col gap-1" v-for="patch in improvementData.code_patches" :key="patch.file_path">
            <div class="text-xs font-bold text-primary">
              {{ patch.file_path }}
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
                <div class="bg-auto bg-no-repeat bg-center border rounded-md w-12 h-12 md:h-20 md:w-20" :style="`background-image: url(${image.src})`"></div>
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
      improvementData: null
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
      const { task_item, content } = this.message
      return task_item ? `### \`${task_item}\`\n\n${content}` : content
    },
    selection () {
      return document.getSelection().toString()
    }
  },
  methods: {
    formatDate(date) {
      return moment(date).format('DD/MMM HH:mm')
    },
    extractImprovementData() {
      if (this.message.improvement) {
        try {
          const jsBlock = this.message.content.split("```json")[1].split("```")[0]
          this.improvementData = JSON.parse(jsBlock)
        } catch (ex) {
          console.error("Failed to parse improvement data", ex)
        }
      }
    },
    copyTextToClipboard(text) {
      const textArea = document.createElement('textarea')
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      console.log('Code copied', text)
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
      this.srcView = !this.srcView
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
        const code_changes = this.improvementData.code_changes.filter(cc => cc.file_path === patch.file_path)
        patch.res = await this.$storex.api.run.patch({ code_changes, code_patches: [ patch ] })
        if (patch.res.info?.toLowerCase().includes('error')) {
          patch.res.error = patch.res.info
        }
      } catch {
        patch.res = { info: "", error: "Error aplaying patch" }
      }
      delete patch.working
    }
  },
  mounted() {
    this.message.collapse = this.message.hide
    this.extractImprovementData()
  }
}
</script>