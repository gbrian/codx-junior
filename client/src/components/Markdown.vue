<script setup>
import Code from './Code.vue'
import YoutubeViewer from './YoutubeViewer.vue'
import { full as emoji } from 'markdown-it-emoji'
import MarkdownIt from 'markdown-it'
import highlight from 'markdown-it-highlightjs'
</script>

<template>
  <div class="w-full h-full flex gap-2">
    <div
      v-bind="$attrs"
      class="text-md text-wrap max-w-full w-full overflow-y-auto prose leading-tight"
    >
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
      :key="code"
      :code="code"
      :files="files"
      :chat="chat"
      @generate-code="$emit('generate-code', $event)"
      @reload-file="$emit('reload-file', $event)"
      @open-file="$emit('open-file', $event)"
      @save-file="$emit('save-file', $event)"
      @add-file="$emit('add-file', $event)"
      @edit-message="$emit('edit-message', $event)"
      @text-changed="onBlockTextChanged"
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
    const render = body =>
      `<pre><code class="hljs language-${lang}" data-file="${file}">${body}</code></pre>`
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
  props: ['chat', 'text', 'mentionList', 'files'],
  emits: ['generate-code', 'reload-file', 'open-file', 'save-file', 'add-file', 'edit-message', 'text-changed'],
  data() {
    return {
      // localText is the mutable working copy of the markdown source
      localText: null,
      codeBlocks: [],
      showDoc: false,
      youtubeLinks: [],
    }
  },
  mounted() {
    this.localText = this.text
    this.initializeComponent()
  },
  computed: {
    html() {
      if (this.showDoc) return this.showDocPreview
      try {
        return md.render(this.sanitizedText)
      } catch (ex) {
        console.error("Message can't be rendered", this.localText)
      }
      return ''
    },
    showDocPreview() {
      return md.render("```json\n" + JSON.stringify(this.localText, null, 2) + "\n```")
    },
    sanitizedText() {
      let text = (this.localText || "").trim()
      const lines = text.split("\n")
      const firstLine = lines[0]
      const isMdFence = !!["```", "```md", "```markdown"].find(p => firstLine.trim() === p)

      if (isMdFence) {
        lines.splice(0, 1)
        const ix = lines.findLastIndex(l => l === '```')
        if (ix !== -1) lines.splice(ix, 1)
        text = lines.join("\n")
      }
      return text.replace("```thymeleaf", "```html")
    }
  },
  watch: {
    text(val) {
      this.localText = val
      this.codeBlocks = []
      this.youtubeLinks = []
      requestAnimationFrame(() => this.initializeComponent())
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
      }
    },
    extractYoutubeLinks() {
      const youtubeRegex = /https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/g
      this.youtubeLinks = this.localText?.match(youtubeRegex) || []
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
    },

    // A Code block reported its content changed; patch localText and bubble up
    onBlockTextChanged({ block, newContent }) {
      this.localText = this.replaceBlockInText(this.localText, block, newContent)
      this.$emit('text-changed', this.localText)
    },

    // Replace only the matching fenced block inside the full markdown source
    replaceBlockInText(fullText, block, newContent) {
      const lang = block.language || ''
      const fileHint = block.file ? ` ${block.file}` : ''
      const openFence = `\`\`\`${lang}${fileHint}`

      const lines = fullText.split('\n')
      let insideFence = false
      let fenceStart = -1
      const result = []

      for (let i = 0; i < lines.length; i++) {
        if (!insideFence && lines[i].startsWith(openFence)) {
          insideFence = true
          fenceStart = i
          result.push(lines[i])
          continue
        }
        if (insideFence && lines[i].startsWith('```') && lines[i].trim() === '```') {
          // Replace everything between the fences with newContent
          result.splice(fenceStart + 1)
          newContent.split('\n').forEach(l => result.push(l))
          result.push('```')
          insideFence = false
          fenceStart = -1
          continue
        }
        if (!insideFence) result.push(lines[i])
      }

      return result.join('\n')
    }
  }
}
</script>