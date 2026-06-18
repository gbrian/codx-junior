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
import MarkdownIt from 'markdown-it'
import { full as emoji } from 'markdown-it-emoji'
import highlight from 'markdown-it-highlightjs'

function createMd(documentId) {
  const md = new MarkdownIt({ html: true, linkify: true, typographer: true })
  md.use(emoji)
  md.use(highlight)

  const defaultHeadingRenderer = md.renderer.rules.heading_open || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }

  // Prefix heading anchors with documentId to keep them unique across documents
  md.renderer.rules.heading_open = function(tokens, idx, options, env, self) {
    const token = tokens[idx]
    const inlineToken = tokens[idx + 1]
    if (inlineToken && inlineToken.children) {
      const text = inlineToken.children
        .filter(t => t.type === 'text' || t.type === 'code_inline')
        .map(t => t.content)
        .join('')
      const slug = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .trim()
        .replace(/\s+/g, '-')
      const anchor = documentId ? `${documentId}-${slug}` : slug
      token.attrSet('id', anchor)
      token.attrSet('class', 'heading-anchor scroll-mt-4')
    }
    return defaultHeadingRenderer(tokens, idx, options, env, self)
  }

  // Add anchor to fenced code blocks that have a file path as info string
  const defaultFenceRenderer = md.renderer.rules.fence || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }

  md.renderer.rules.fence = function(tokens, idx, options, env, self) {
    const token = tokens[idx]
    const info = token.info ? token.info.trim() : ''
    // Match "language file/path" — file path must contain at least one slash
    const infoMatch = info.match(/^(\w+)\s+([\w\-_.\/]+)$/)
    const filePath = infoMatch ? infoMatch[2] : null

    const rendered = defaultFenceRenderer(tokens, idx, options, env, self)

    if (!filePath) return rendered

    // Derive slug from file path, prefix with documentId
    const slug = filePath
      .toLowerCase()
      .replace(/[^\w\s\-./]/g, '')
      .trim()
      .replace(/[\s/]+/g, '-')
    const anchor = documentId ? `${documentId}-${slug}` : slug

    // Wrap rendered block with an anchor element
    return `<div id="${anchor}" class="code-block-anchor scroll-mt-4">${rendered}</div>`
  }

  return md
}

const FILE_PATH_REGEX = /(?<=^|[\s(,>])((?:\.{1,2}\/|\/)?(?:[\w\-_.]+\/)+[\w\-_.]+\.(?:js|ts|vue|py|java|cpp|c|h|cs|go|rb|rs|php|html|css|scss|json|yaml|yml|md|txt|sh|bash|env|toml|xml|sql|graphql|proto|ipynb|jsx|tsx|mjs|cjs|svelte|kotlin|swift|dart))(?=[\s),<]|$)/g

function addFileUploadIcons(html) {
  return html.replace(
    FILE_PATH_REGEX,
    (match) =>
      `<span
        class="file-path-upload-btn underline ml-1 cursor-pointer inline-flex items-center align-middle"
        data-file-path="${match}"
        title="Add '${match}' to chat files"
      ><i class="fa-solid fa-file-arrow-up"></i>&nbsp;${match}</span>`
  )
}

export default {
  props: {
    text: { type: String, default: '' },
    files: { type: Array, default: null },
    documentId: { type: String, default: '' }
  },
  emits: ['add-file'],
  computed: {
    html() {
      try {
        const md = createMd(this.documentId)
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
      let text = ''
      if (this.text) {
        text = this.text
          .replace('```thymeleaf', '```html')
          .replace('```md', '')
      }
      return text
    }
  },
  methods: {
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