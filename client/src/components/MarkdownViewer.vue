<script setup>
import { full as emoji } from 'markdown-it-emoji'
import MarkdownIt from 'markdown-it'
import highlight from 'markdown-it-highlightjs'
import InteractiveTable from './InteractiveTable.vue'
</script>

<template>
  <div class="text-wrap overflow-y-auto prose max-w-full">
    <!-- Render markdown content with mixed elements -->
    <div class="space-y-4">
      <div 
        v-for="(element, idx) in renderedElements" 
        :key="`element-${idx}`"
        @click="handleClick"
      >
        <!-- Markdown/HTML content -->
        <div 
          v-if="element.type === 'markdown'"
          v-html="element.content"
        ></div>

        <!-- Table with toggle header -->
        <div 
          v-else-if="element.type === 'table'"
          class="space-y-2"
        >
          <div class="flex items-center justify-end">
            <label class="toggle toggle-sm text-base-content cursor-pointer">
              <input 
                type="checkbox"
                :checked="element.viewMode === 'interactive'"
                @change="toggleTableMode(idx, element.viewMode === 'markdown' ? 'interactive' : 'markdown')"
              />
              <svg 
                aria-label="Interactive" 
                xmlns="http://www.w3.org/2000/svg" 
                viewBox="0 0 24 24"
                class="w-4 h-4"
              >
                <g
                  stroke-linejoin="round"
                  stroke-linecap="round"
                  stroke-width="2"
                  fill="none"
                  stroke="currentColor"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M9 11h6m-6 4h6" />
                </g>
              </svg>
              <svg
                aria-label="Standard"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                class="w-4 h-4"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M7 7h10M7 11h10M7 15h4" />
              </svg>
            </label>
          </div>

          <!-- Interactive table component -->
          <InteractiveTable 
            v-if="element.viewMode === 'interactive'"
            :initial-data="element.data"
            :table-index="idx"
            @update-table="handleTableUpdate"
          />

          <!-- Standard markdown table -->
          <div 
            v-else
            v-html="element.markdownHtml"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import MarkdownIt from 'markdown-it'
import { full as emoji } from 'markdown-it-emoji'
import highlight from 'markdown-it-highlightjs'
import InteractiveTable from './InteractiveTable.vue'

function createMd(documentId) {
  const md = new MarkdownIt({ html: true, linkify: true, typographer: true })
  md.use(emoji)
  md.use(highlight)

  const defaultHeadingRenderer = md.renderer.rules.heading_open || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }

  // Add IDs to heading elements - CRITICAL for DocumentSummary scroll-to functionality
  md.renderer.rules.heading_open = function(tokens, idx, options, env, self) {
    const token = tokens[idx]
    const inlineToken = tokens[idx + 1]
    if (inlineToken && inlineToken.children) {
      const text = inlineToken.children
        .filter(t => t.type === 'text' || t.type === 'code_inline')
        .map(t => t.content)
        .join('')
      
      // Generate slug matching DocumentSummary format
      const slug = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .trim()
        .replace(/\s+/g, '-')
      
      // Create anchor ID with documentId scope
      const anchor = documentId ? `${documentId}-${slug}` : slug
      
      token.attrSet('id', anchor)
      token.attrSet('class', 'heading-anchor scroll-mt-4')
    }
    return defaultHeadingRenderer(tokens, idx, options, env, self)
  }

  md.core.ruler.push('table_marker', (state) => {
    let rowIdx = 0
    for (let i = 0; i < state.tokens.length; i++) {
      const token = state.tokens[i]
      if (token.type === 'table_open') {
        token.attrSet('data-interactive-table', 'true')
        rowIdx = 0
      }
      if (token.type === 'tr_open') {
        token.attrSet('data-row', rowIdx.toString())
        rowIdx++
      }
      if (token.type === 'th_open' || token.type === 'td_open') {
        const colIdx = token.map ? state.tokens.slice(0, i).filter(t => t.type === token.type && t.map && t.map[0] === token.map[0]).length : 0
        token.attrSet('data-col', colIdx.toString())
      }
    }
  })

  const defaultFenceRenderer = md.renderer.rules.fence || function(tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }

  // Add IDs to code block anchors - CRITICAL for DocumentSummary scroll-to functionality
  md.renderer.rules.fence = function(tokens, idx, options, env, self) {
    const token = tokens[idx]
    const info = token.info ? token.info.trim() : ''
    const infoMatch = info.match(/^(\w+)\s+([\w\-_.\/]+)$/)
    const filePath = infoMatch ? infoMatch[2] : null
    const rendered = defaultFenceRenderer(tokens, idx, options, env, self)

    if (!filePath) return rendered

    // Generate slug matching DocumentSummary format
    const slug = filePath
      .toLowerCase()
      .replace(/[^\w\s\-./]/g, '')
      .trim()
      .replace(/[\s/]+/g, '-')
    
    // Create anchor ID with documentId scope
    const anchor = documentId ? `${documentId}-${slug}` : slug
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
        class=""
        data-file-path="${match}"
        title="Add '${match}' to chat files"
      >${match}</span>`
  )
}

function parseTableFromHtml(tableHtml) {
  if (typeof document === 'undefined') return null
  const parser = new DOMParser()
  const doc = parser.parseFromString(tableHtml, 'text/html')
  const table = doc.querySelector('table')
  if (!table) return null

  const data = []
  const rows = table.querySelectorAll('tr')
  
  rows.forEach(tr => {
    const cells = tr.querySelectorAll('td, th')
    const row = Array.from(cells).map(cell => cell.textContent.trim())
    if (row.length > 0) data.push(row)
  })

  return data.length > 0 ? data : null
}

export default {
  props: {
    text: { type: String, default: '' },
    files: { type: Array, default: null },
    documentId: { type: String, default: '' }
  },
  emits: ['add-file', 'table-updated', 'copy-chapter', 'create-task'],
  components: {
    InteractiveTable
  },
  data() {
    return {
      renderedElements: []
    }
  },
  computed: {
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
  watch: {
    text() {
      this.renderContent()
    },
    documentId() {
      this.renderContent()
    }
  },
  mounted() {
    this.renderContent()
  },
  methods: {
    renderContent() {
      try {
        const md = createMd(this.documentId)
        const textWithLinks = this.sanitizedText.replace(
          /`((?:\/[^\s:]+)+)(?::(\d+))?`/g,
          (match, filePath, lineNumber) => {
            const slashCount = (filePath.match(/\//g) || []).length
            if (slashCount < 2) return match
            const lineInfo = lineNumber ? `:${lineNumber}` : ''
            return `<span>${filePath}${lineInfo}</span>`
          }
        )
        const rendered = md.render(textWithLinks)
        this.parseElements(rendered)
      } catch (ex) {
        console.error("Message can't be rendered", this.text)
        this.renderedElements = []
      }
    },
    parseElements(html) {
      const elements = []
      const tableRegex = /<table[^>]*>[\s\S]*?<\/table>/g
      let lastIndex = 0
      let match

      // Extract all tables with their positions
      const tables = []
      while ((match = tableRegex.exec(html)) !== null) {
        tables.push({
          start: match.index,
          end: match.index + match[0].length,
          html: match[0],
          data: parseTableFromHtml(match[0])
        })
      }

      // Split content by tables
      tables.forEach((table, idx) => {
        // Add markdown content before table
        if (table.start > lastIndex) {
          const mdHtml = html.substring(lastIndex, table.start).trim()
          if (mdHtml) {
            elements.push({
              type: 'markdown',
              content: addFileUploadIcons(mdHtml)
            })
          }
        }

        // Add table element with view mode toggle
        if (table.data && table.data.length > 0) {
          elements.push({
            type: 'table',
            data: table.data,
            markdownHtml: table.html,
            viewMode: 'markdown'
          })
        }

        lastIndex = table.end
      })

      // Add remaining markdown content
      if (lastIndex < html.length) {
        const mdHtml = html.substring(lastIndex).trim()
        if (mdHtml) {
          elements.push({
            type: 'markdown',
            content: addFileUploadIcons(mdHtml)
          })
        }
      }

      this.renderedElements = elements.length > 0 ? elements : [{ 
        type: 'markdown', 
        content: addFileUploadIcons(html) 
      }]
    },
    toggleTableMode(idx, mode) {
      if (this.renderedElements[idx] && this.renderedElements[idx].type === 'table') {
        this.renderedElements[idx].viewMode = mode
      }
    },
    handleTableUpdate(payload) {
      this.$emit('table-updated', payload)
    },
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