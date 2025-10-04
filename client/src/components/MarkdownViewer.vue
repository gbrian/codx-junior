<script setup>
import { full as emoji } from 'markdown-it-emoji'
import MarkdownIt from 'markdown-it'
import highlight from 'markdown-it-highlightjs'
</script>

<template>
  <div class="text-wrap overflow-y-auto prose max-w-full" v-html="html">
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
    }
  },
  mounted() {
  },
  computed: {
    html() {
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
  }
}
</script>