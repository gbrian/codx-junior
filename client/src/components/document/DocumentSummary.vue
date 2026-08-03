<script setup>
</script>

<template>
  <div class="relative" v-if="headings.length >= minHeadings">
    <button
      @click="open = !open"
      class="flex items-center gap-2 text-xs font-semibold text-base-content/60 hover:text-base-content mb-1 transition-colors"
    >
      <span class="text-base">📋</span>
      <span>{{ open ? 'Hide' : 'Show' }} Contents</span>
      <span class="text-base-content-ERROR-40">({{ headings.length }})</span>
      <svg
        class="w-3 h-3 transition-transform"
        :class="open && 'rotate-180'"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>
    </button>

    <transition name="toc-slide">
      <div
        v-if="open"
        class="bg-base-200 border border-base-300 rounded-lg px-4 py-3 mb-4"
      >
        <p class="text-xs font-bold text-base-content/50 uppercase tracking-widest mb-2">Table of Contents</p>
        <ul class="space-y-0.5">
          <li
            v-for="(h, i) in headings"
            :key="i"
            :style="{ paddingLeft: (h.level - 1) * 12 + 'px' }"
          >
            <a
              :href="`#${h.anchor}`"
              class="text-sm text-primary hover:underline hover:text-primary-focus block py-0.5 truncate"
              @click.prevent="scrollTo(h.anchor)"
            >
              <span class="text-base-content/30 mr-1 text-xs">{{ levelIcon(h.level, h.type) }}</span>
              {{ h.text }}
            </a>
          </li>
        </ul>
      </div>
    </transition>
  </div>
</template>

<script>
export default {
  name: 'DocumentSummary',
  props: {
    content: { type: String, default: '' },
    minHeadings: { type: Number, default: 3 },
    documentId: { type: String, default: '' },
    scrollContainer: { type: Object, default: null }
  },
  data() {
    return {
      open: true
    }
  },
  computed: {
    headings() {
      const lines = (this.content || '').split('\n')
      const result = []
      let insideCodeBlock = false
      let codeBlockDepth = 0

      for (const line of lines) {
        const openMatch = line.match(/^```(\w+)\s+(.+)$/)
        const closeMatch = line === '```'
        const bareOpenMatch = line.match(/^```(\w+)?\s*$/)

        // Track code fence nesting to know when we're inside a plain code block
        if (!insideCodeBlock && openMatch) {
          // Code block with a file path — this is a TOC entry
          const [, lang, filePath] = openMatch
          const fileName = filePath.split('/').pop()
          const slug = filePath
            .toLowerCase()
            .replace(/[^\w\s\-./]/g, '')
            .trim()
            .replace(/[\s/]+/g, '-')
          const anchor = this.documentId ? `${this.documentId}-${slug}` : slug
          result.push({ level: 2, text: filePath, anchor, type: 'code', lang, fileName })
          insideCodeBlock = true
          codeBlockDepth = 1
          continue
        }

        if (!insideCodeBlock && bareOpenMatch) {
          // Code block without file path, skip content but track depth
          insideCodeBlock = true
          codeBlockDepth = 1
          continue
        }

        if (insideCodeBlock) {
          if (openMatch || bareOpenMatch) codeBlockDepth++
          if (closeMatch) codeBlockDepth--
          if (codeBlockDepth <= 0) insideCodeBlock = false
          continue
        }

        // Regular markdown heading
        const m = line.match(/^(#{1,6})\s+(.+)$/)
        if (!m) continue
        const text = m[2].trim()
        const slug = text
          .toLowerCase()
          .replace(/[^\w\s-]/g, '')
          .trim()
          .replace(/\s+/g, '-')
        const anchor = this.documentId ? `${this.documentId}-${slug}` : slug
        result.push({ level: m[1].length, text, anchor, type: 'heading' })
      }

      return result
    }
  },
  methods: {
    levelIcon(level, type) {
      if (type === 'code') return '📄'
      return ['#', '##', '###', '####', '#####', '######'][level - 1] || '#'
    },
    findScrollableParent(el) {
      if (!el || el === document.body) return null
      const { overflowY } = window.getComputedStyle(el)
      const isScrollable = (overflowY === 'auto' || overflowY === 'scroll') && el.scrollHeight > el.clientHeight
      return isScrollable ? el : this.findScrollableParent(el.parentElement)
    },
    scrollTo(anchor) {
      const target = document.getElementById(anchor)
      if (!target) return

      const container = this.scrollContainer
        || this.findScrollableParent(target)
        || window

      if (container === window) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' })
        return
      }

      const containerRect = container.getBoundingClientRect()
      const targetRect = target.getBoundingClientRect()
      const offset = targetRect.top - containerRect.top + container.scrollTop - 8
      container.scrollTo({ top: offset, behavior: 'smooth' })
    }
  }
}
</script>