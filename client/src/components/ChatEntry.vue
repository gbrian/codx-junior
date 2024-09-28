<script setup>
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
      <div>
        <div class="flex gap-2 items-center">
          <div class="btn btn-xs flex gap-2 items-center font-bold text-xs bg-base-300 group-hover:bg-base-100 rounded-md">
            <button class="btn btn-xs" @click="$emit('hide')">
              <span class="text-warning" v-if="message.hide">
                <i class="fa-solid fa-eye-slash"></i>
              </span>
              <span v-else>
                <i class="fa-solid fa-eye"></i>
              </span>
            </button>
            <div v-if="message.role ==='user'">You ({{ message.role }})</div>
            <div v-else>gpt-engineer ({{ message.role }})</div>
          </div>
          <div class="hidden group-hover:flex gap-2">
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
        <Markdown class="" :text="message.content" v-else></Markdown>
        <div v-if="images">
          <div class="grid grid-cols-6">
            <div class="carousel-item click mt-2"
              v-for="image in images" :key="image.src"
              @click="$emit('image', image)"
            >
              <div class="flex flex-col">
                <div class="bg-auto bg-no-repeat bg-center border rounded-md h-28 w-28" :style="`background-image: url(${image.src})`"></div>
                <p class="badge badge-xs" v-if="image.alt">{{ image.alt }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="grid gap-2 grid-cols-3 mt-2">
          <div v-for="file in message.files" :key="file" :data-tip="file" class="badge badge-info badge-sm tooltip">
            {{ file.split("/").reverse()[0] }}
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
  props: ['message'],
  data () {
    return {
      codeBlocks: [],
      showDoc: false,
      srcView: false
    }
  },
  mounted () {
    this.message.collapse = this.message.hide
    // this.updateCodeBlocks()
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
  watch: {
    message () {
      this.codeBlocks = []
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
      const classes = ["h-20", "overflow-hidden"]
      if (code._collapsed) {
        parentNode.classList.add(...classes)
      } else {
        parentNode.classList.remove(...classes)
      }
    },
    updateCodeBlocks () {
      setInterval(() => {
        const codeBlocks = [...this.$el.querySelectorAll('code[class^="language"]')]
                            .filter(cb => !this.codeBlocks.find(ccb => ccb === cb))
        if (codeBlocks.length) {
          this.codeBlocks = [...this.codeBlocks, ...codeBlocks]
          console.log("Code blocks", codeBlocks)
        }
      }, 500)      
    }
  }
}
</script>