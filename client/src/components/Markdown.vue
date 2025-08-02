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
      class="code-block"
      :key="new Date()"
      :code="code"
      @generate-code="$emit('generate-code', $event)"
    />
  </div>
</template>

<script>
import hljs from 'highlight.js'
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: function (str, lang, file) {
    if (lang && hljs.getLanguage(lang)) {
      const render = body =>`<pre>
        <code class="hljs language-${lang}" data-file="${file}">${body}</code>
      </pre>`
      try {
        return render(hljs.highlight(str, { language: lang, ignoreIllegals: true }).value)
      } catch (__) {}
    }
    return render(md.utils.escapeHtml(str))
  }
})


md.use(emoji)
// md.use(highlight, { hljs })

export default {
  props: ['text'],
  data() {
    return {
      codeBlocks: [],
      showDoc: false,
      youtubeLinks: [],
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
      let text = this.text || ""
      const lines = text.trim().split("\n")
      const firstLine = lines[0]
      const isMdFence = !![
          "```",
          "```md",
          "```markdown",
        ].find(pattern => firstLine.trim() === pattern)

      if (isMdFence) {
        // Unnecessary
        lines.splice(0, 1)
        const ix = lines.findLastIndex(l => l === '```')
        if (ix !== -1) {
          lines.splice(ix, 1)
        }
        text = lines.join("\n")
      }
      text = text
        .replace("```thymeleaf", "```html")
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
        .filter(cb => cb.innerText.trim().length > 40 && !this.codeBlocks.includes(cb))
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