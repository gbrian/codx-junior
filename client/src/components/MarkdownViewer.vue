<script setup>
import { full as emoji } from 'markdown-it-emoji'
import MarkdownIt from 'markdown-it'
import highlight from 'markdown-it-highlightjs'
</script>

<template>
  <div class="text-wrap overflow-y-auto prose max-w-full" v-html="html" @click="handleClick">
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

// Matches file paths like src/foo/bar.vue, ./foo/bar.ts, /abs/path.js
const FILE_PATH_REGEX = /(?<=^|[\s(,>])((?:\.{1,2}\/|\/)?(?:[\w\-_.]+\/)+[\w\-_.]+\.(?:js|ts|vue|py|java|cpp|c|h|cs|go|rb|rs|php|html|css|scss|json|yaml|yml|md|txt|sh|bash|env|toml|xml|sql|graphql|proto|ipynb|jsx|tsx|mjs|cjs|svelte|kotlin|swift|dart))(?=[\s),<]|$)/g

// Append upload icon span after each detected file path in rendered HTML
function addFileUploadIcons(html) {
  return html.replace(
    FILE_PATH_REGEX,
    (match) =>
      `${match}<span
        class="file-path-upload-btn ml-1 cursor-pointer text-accent hover:text-primary inline-flex items-center align-middle"
        data-file-path="${match}"
        title="Add '${match}' to chat files"
      ><i class="fa-solid fa-upload text-xs"></i></span>`
  )
}

export default {
  props: ['text', 'files'],
  emits: ['add-file'],
  data() {
    return {}
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
        const rendered = md.render(textWithLinks)
        return addFileUploadIcons(rendered)
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
  },
  methods: {
    // Delegate click events to handle file upload icon clicks
    handleClick(event) {
      const btn = event.target.closest('.file-path-upload-btn')
      if (!btn) return
      event.preventDefault()
      event.stopPropagation()
      const filePath = btn.getAttribute('data-file-path')
      if (filePath) {
        this.$emit('add-file', filePath)
      }
    }
  }
}
</script>