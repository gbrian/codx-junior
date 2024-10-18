<script setup>
import { API } from '../api/api'
import Markdown from './Markdown.vue'
</script>
<template>
  <div :class="['relative w-full relative p-2 hover:rounded-md',
      message.role === 'user' ? 'chat-start': 'chat-end',
    ]" >
    <div :class="['px-2 max-w-full group w-full -mx-2 prose-xs',
      message.improvement ? 'border-green-300/20 bg-green-900' : 'border-slate-300/20',
      message.role === 'user' ? '': '',
      message.collapse ? 'max-h-40 overflow-hidden': 'h-fit',
      message.hide ? 'text-slate-200/20': ''
    ]"
    >
      <div @copy.stop="onMessageCopy">
        <div class="flex gap-2 items-center">
          <div :class="['btn btn-sm btn-outline flex gap-2 items-center font-bold text-xs rounded-md',
            message.role ==='user' ? 'bg-base-300' :'bg-secondary/80 text-secondary-content' ]">
            <div class="click" @click="$emit('hide')">
              <span class="text-warning" v-if="message.hide">
                <i class="fa-solid fa-eye-slash"></i>
              </span>
              <span v-else>
                <i class="fa-solid fa-eye"></i>
              </span>
            </div>
            <div v-if="message.role ==='user'">You</div>
            <div v-else>codx-junior</div>
          </div>
          <div class="opacity-20 group-hover:opacity-100 md:opacity-100 gap-2">
            <button class="btn btn-xs" @click="message.collapse = !message.collapse">
              <span v-if="message.collapse">
                <i class="fa-solid fa-chevron-up"></i>
              </span>
              <span v-else>
                <i class="fa-solid fa-chevron-down"></i>
              </span>
            </button>
            <button class="hidden btn btn-xs bg-base-100" @click="copyMessageToClipboard">
              <i class="fa-solid fa-copy"></i>
            </button>      
            <button class="btn btn-xs " @click="srcView = !srcView">
                <i class="fa-solid fa-code"></i>
            </button>
            <button class="btn btn-xs bg-success" @click="$emit('edit')">
              <i class="fa-solid fa-pencil"></i>
            </button>
            <button class="btn bg-purple-600 text-white btn-xs" @click="$emit('enhance')">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
            </button>
            <button class="ml-4 btn btn-error btn-xs" @click="$emit('remove')">
              <i class="fa-solid fa-trash"></i>
            </button>
            
          </div>
        </div>
        <pre v-if="srcView">{{ message.content }}</pre>
        <Markdown :text="message.content" v-else />
        <div v-if="images">
          <div class="carousel gap-2">
            <div class="carousel-item click mt-2"
              v-for="image in images" :key="image.src"
              @click="$emit('image', image)"
              :alt="image.alt"
              :title="image.alt"
            >
              <div class="flex flex-col">
                <div class="bg-auto bg-no-repeat bg-center border rounded-md w-12 h-12 md:h-20 md:w-20" :style="`background-image: url(${image.src})`"></div>
                <p class="badge badge-xs" v-if="image.alt">{{ image.alt.slice(0, 10) }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="grid gap-2 grid-cols-3 mt-2">
          <div v-for="file in message.files" :key="file" :title="file"
            class="badge badge-primary text-xs flex gap-2 items-center click"
            @click="API.coder.openFile(file)"
          >
            <button class="btn btn-xs btn-circle" @click="$emit('add-file-to-chat', file)">
              <i class="fa-solid fa-file-circle-plus"></i>
            </button>
            <div class="overflow-hidden">
              {{ file.split("/").reverse()[0] }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import { full as emoji } from 'markdown-it-emoji'
import highlight  from 'markdown-it-highlightjs'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: true
})
md.use(emoji)
md.use(highlight)

export default {
  props: ['chat', 'message'],
  data () {
    return {
      showDoc: false,
      srcView: false
    }
  },
  mounted () {
    this.message.collapse = this.message.hide
  },
  computed: {
    html () {
      if (!this.showDoc) {
        try {
          return md.render(this.message.content)
        } catch (ex) {
          console.error("Message can't be rendered", this.message)
        }
      }
      return this.showDocPreview
    },
    showDocPreview () {
      return md.render("```json\n" + JSON.stringify(this.message, null, 2) + "\n```")
    },
    images () {
      return this.message?.images?.map(i => {
        try {
          return JSON.parse(i)
        } catch {
          return {
            src: i
          }
        }
      })
    }
  },
  methods: {
    onRunEdit (preNone) {
      const codeNode = preNone.querySelector('code')
      const codeText = codeNode.innerText
      const codeLang = [...codeNode.classList.values()].find(c => c.startsWith("language-"))||"language-code"
      const codeSnipped = "```" + codeLang.split("language-")[1] + "\n" + codeText + "\n```"
      this.$emit('run-edit', codeSnipped)
    },
    copyCodeToClipboard(codeBlock){
      const text = codeBlock.childNodes[0].nodeValue
      this.copyTextToClipboard(text)
    },
    copyMessageToClipboard(){
      const text = this.message.content
      this.copyTextToClipboard(text)
    },
    copyTextToClipboard (text) {
      const textArea = document.createElement("textarea")
      textArea.value = text

      document.body.appendChild(textArea)

      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      console.log("Code copied", text)
    },
    toggleExpand(code) {
      const { parentNode } = code
      code._collapsed = !code._collapsed
      const classes = ["h-10", "overflow-hidden"]
      if (code._collapsed) {
        parentNode.classList.add(...classes)
      } else {
        parentNode.classList.remove(...classes)
      }
    },
    getSelectionText() {
        if (window.getSelection) {
            return window.getSelection().toString();
        }  
        if (document.selection && document.selection.type != "Control") {
            return document.selection.createRange().text;
        }
        return null;
    },
    onMessageCopy(ev) {
      const text = this.getSelectionText()
      if (text) {
        this.copyTextToClipboard(text)
        ev.preventDefault()
        window.navigator.clipboard.read().then(console.log)
      }
    }
  }
}
</script>