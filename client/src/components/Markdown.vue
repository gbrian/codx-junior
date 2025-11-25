<script setup>
import Code from './Code.vue'
import YoutubeViewer from './YoutubeViewer.vue'
import { full as emoji } from 'markdown-it-emoji'
import MarkdownIt from 'markdown-it'
import highlight from 'markdown-it-highlightjs'
</script>

<template>
  <div class="w-full h-full flex gap-2">
    <div v-bind="$attrs" class="text-md text-wrap max-w-full w-full overflow-y-auto prose leading-tight">
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
      :files="files"
      @generate-code="$emit('generate-code', $event)"
      @reload-file="$emit('reload-file', $event)"
      @open-file="$emit('open-file', $event)"
      @save-file="$emit('save-file', $event)"
      @add-file="$emit('add-file', $event)"
      @edit-message="$emit('edit-message', $event)"
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
    lang = lang || "txt"
    const render = body =>`<pre><code class="hljs language-${lang}" data-file="${file}">${body}</code></pre>`
    try {
      return render(hljs.highlight(str, { language: lang, ignoreIllegals: true }).value)
    } catch (ex) {
      console.error("Error rendering markdown", { ex, str, lang, file })
    }
    return render(md.utils.escapeHtml(str))
  }
})

md.use(emoji)

export default {
  inheritAttrs: false,
  props: ['text', 'mentionList', 'files'],
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
          let { sanitizedText } = this 
          const avatarHtml = (mention) => {
            const { user, profile } = mention  
            const name = mention.name
            const avatar = mention.avatar
            return `
              <div class="avatar flex gap-2">
                <img src="${user.avatar}" class="w-10" />
                ${user.username}
              </div>
            `
          }
          /*
          this.mentionList?.filter(m => m.avatar)
              .forEach(mention => {
                const mentionPattern = new RegExp(`@${mention.name}`, 'g')
                sanitizedText = sanitizedText.replace(mentionPattern, avatarHtml(mention))
              })
          */
          return md.render(sanitizedText)
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