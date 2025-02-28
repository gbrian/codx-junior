<script setup>
import Code from './Code.vue'
import YoutubeViewer from './YoutubeViewer.vue'
import { full as emoji } from 'markdown-it-emoji'
import MarkdownIt from 'markdown-it'
import highlight from 'markdown-it-highlightjs'
</script>

<template>
  <div class="w-full h-full flex gap-2">
    <div class="text-md text-wrap max-w-full w-full overflow-y-auto prose leading-tight">
      <div v-html="html"></div>
      <YoutubeViewer
        v-for="(url, index) in youtubeLinks"
        :key="index"
        :youtubeUrl="url"
      />
    </div>
    <Code
      v-for="code in codeBlocks"
      :key="code.id"
      :code="code"
      @generate-code="$emit('generate-code', $event)"
    />
  </div>
</template>

<script>
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})
md.use(emoji)
md.use(highlight)

export default {
  props: ['text'],
  data() {
    return {
      codeBlocks: [],
      showDoc: false,
      youtubeLinks: []
    }
  },
  mounted() {
    this.initializeComponent()
  },
  computed: {
    html() {
      if (!this.showDoc) {
        try {
          const textWithLinks = this.sanitizedText.replace(
            /`((?:\/[^\s:]+)+)(?::(\d+))?`/g,
            (match, filePath, lineNumber) => {
              const slashCount = (filePath.match(/\//g) || []).length
              if (slashCount < 2) return match
              const lineInfo = lineNumber ? `:${lineNumber}` : ''
              return `<a class="file-link btn btn-link" href="${filePath}${lineInfo}">${filePath}${lineInfo}</a>`
            }
          )
          return md.render(textWithLinks)
        } catch (ex) {
          console.error("Message can't be rendered", this.text)
        }
      }
      return this.showDocPreview
    },
    showDocPreview() {
      return md.render("```json\n" + JSON.stringify(this.text, null, 2) + "\n```")
    },
    sanitizedText() {
      let text = ""
      if (this.text) {
        text = this.text
          .replace("```thymeleaf", "```html")
          .replace("```md", "")
      }
      return text
    }
  },
  watch: {
    text() {
      this.codeBlocks = []
      this.youtubeLinks = []
      requestAnimationFrame(() => {
        this.initializeComponent()
      })
    }
  },
  methods: {
    initializeComponent() {
      // Initialize component by capturing links and extracting necessary data
      this.updateCodeBlocks()
      this.captureLinks()
      this.extractYoutubeLinks()
      this.captureFileLinks()
    },
    captureLinks() {
      const linkBlocks = [...this.$el.querySelectorAll('a')]
      linkBlocks.forEach(a => a.onclick = ev => {
        ev.preventDefault()
        this.$emit('link', { a, url: a.attributes["href"].value, text: a.innerText })
      })
    },
    updateCodeBlocks() {
      const codeBlocks = [...this.$el.querySelectorAll('code[class*="language-"]')]
        .filter(cb => cb.innerText.trim().length && !this.codeBlocks.includes(cb))
      if (codeBlocks.length) {
        this.codeBlocks = [...this.codeBlocks, ...codeBlocks]
        console.log("Code blocks", codeBlocks)
      }
    },
    extractYoutubeLinks() {
      const youtubeRegex = /https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/g
      this.youtubeLinks = this.text?.match(youtubeRegex) || []
    },
    captureFileLinks() {
      const fileLinks = [...this.$el.querySelectorAll('.file-link')]
      fileLinks.forEach(link => {
        link.onclick = ev => {
          ev.preventDefault()
          this.openFile(link.getAttribute('href'))
        }
      })
    },
    openFile(href) {
      this.$ui.copyTextToClipboard(href)
      this.$storex.api.coder.openFile(href)
    }
  }
}
</script>