<script setup>
/**
 * Modern documentation renderer.
 *
 * - GitHub-flavoured callouts (`> [!TIP]`) become styled hints.
 * - ```mermaid fences render as interactive diagrams (read-only here) instead
 *   of raw code.
 * - Code fences use the shared highlight.js instance and get a copy button.
 * - `wiki:` links are emitted as `open-page` events so the docs shell can
 *   navigate without a full page reload.
 * - Headings get stable anchors that match the manifest's "on this page" rail.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import { full as emoji } from 'markdown-it-emoji'
import MermaidViewer from '../MermaidViewer.vue'
import { highlightCode } from '@/utils/highlight'

const props = defineProps({
  text: { type: String, default: '' },
  compact: { type: Boolean, default: false },
  hideTitle: { type: Boolean, default: false }
})
const emit = defineEmits(['open-page'])

const root = ref(null)
const segments = ref([])
const calloutIcons = {
  tip: 'fa-solid fa-lightbulb',
  note: 'fa-solid fa-circle-info',
  warning: 'fa-solid fa-triangle-exclamation',
  important: 'fa-solid fa-circle-exclamation',
  caution: 'fa-solid fa-hand'
}
const calloutLabels = {
  tip: 'Tip',
  note: 'Note',
  warning: 'Warning',
  important: 'Important',
  caution: 'Caution'
}

function slugifyHeading(value) {
  // Keep this in sync with `_heading_slug` in the Python site builder:
  // apostrophes become hyphens, other punctuation is dropped.
  return String(value || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/['’]/g, '-')
    .replace(/[`*_~[\]()]/g, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '') || 'section'
}

function decorateCallouts(tokens) {
  for (let index = 0; index < tokens.length; index++) {
    const token = tokens[index]
    if (token.type !== 'blockquote_open') continue
    let depth = 0
    let closeIndex = -1
    let inline = null
    for (let cursor = index; cursor < tokens.length; cursor++) {
      if (tokens[cursor].type === 'blockquote_open') depth++
      if (tokens[cursor].type === 'blockquote_close') {
        depth--
        if (depth === 0) {
          closeIndex = cursor
          break
        }
      }
      if (!inline && tokens[cursor].type === 'inline') inline = tokens[cursor]
    }
    if (!inline) continue
    const match = String(inline.content || '').match(/^\s*\[!(TIP|NOTE|WARNING|IMPORTANT|CAUTION)\]\s*/i)
    if (!match) continue
    const type = match[1].toLowerCase()
    token.meta = { ...(token.meta || {}), callout: type }
    if (closeIndex >= 0) {
      tokens[closeIndex].meta = { ...(tokens[closeIndex].meta || {}), callout: type }
    }
    inline.content = inline.content.replace(match[0], '')
    const first = (inline.children || []).find(child => child.type === 'text')
    if (first) first.content = first.content.replace(match[0], '').trimStart()
  }
}

function createMarkdown() {
  const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
    breaks: false,
    highlight: highlightCode
  })
  md.use(emoji)

  const defaultHeading = md.renderer.rules.heading_open || function (tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }
  md.renderer.rules.heading_open = function (tokens, idx, options, env, self) {
    const inline = tokens[idx + 1]
    if (inline && inline.children) {
      const text = inline.children
        .filter(child => child.type === 'text' || child.type === 'code_inline')
        .map(child => child.content)
        .join('')
      tokens[idx].attrSet('id', slugifyHeading(text))
      tokens[idx].attrSet('class', 'wiki-heading scroll-mt-24')
    }
    return defaultHeading(tokens, idx, options, env, self)
  }

  const defaultBlockquoteOpen = md.renderer.rules.blockquote_open || function (tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }
  md.renderer.rules.blockquote_open = function (tokens, idx, options, env, self) {
    const type = tokens[idx].meta && tokens[idx].meta.callout
    if (!type) return defaultBlockquoteOpen(tokens, idx, options, env, self)
    return (
      `<blockquote class="wiki-callout wiki-callout-${type}">` +
      `<div class="wiki-callout-label">` +
      `<i class="${calloutIcons[type] || calloutIcons.note}"></i>` +
      `<span>${calloutLabels[type] || 'Note'}</span>` +
      `</div>`
    )
  }

  md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
    const href = tokens[idx].attrGet('href') || ''
    if (href.startsWith('wiki:')) {
      tokens[idx].attrSet('data-wiki-path', href.slice(5))
      tokens[idx].attrSet('href', '#')
      tokens[idx].attrSet('class', 'wiki-inline-link')
    } else if (!/^[a-z]+:/i.test(href) && /\.md(#|$)/.test(href)) {
      tokens[idx].attrSet('data-wiki-path', href.replace(/^\.?\//, '').replace(/\.md(#.*)?$/, ''))
      tokens[idx].attrSet('href', '#')
      tokens[idx].attrSet('class', 'wiki-inline-link')
    } else if (/^https?:/i.test(href)) {
      tokens[idx].attrSet('target', '_blank')
      tokens[idx].attrSet('rel', 'noopener noreferrer')
    }
    return self.renderToken(tokens, idx, options)
  }

  return md
}

function normalizeContainers(text) {
  // VitePress-style containers are common in older wiki pages. Convert them to
  // the GitHub callout syntax the renderer understands.
  const aliases = {
    tip: 'TIP', warning: 'WARNING', danger: 'CAUTION', info: 'NOTE', note: 'NOTE'
  }
  const lines = String(text || '').split('\n')
  const result = []
  for (let index = 0; index < lines.length; index++) {
    const match = lines[index].match(/^:::\s*(tip|warning|danger|info|note)\s*$/i)
    if (!match) {
      result.push(lines[index])
      continue
    }
    const type = aliases[match[1].toLowerCase()] || 'NOTE'
    result.push(`> [!${type}]`)
    index++
    while (index < lines.length && !/^:::\s*$/.test(lines[index])) {
      result.push(`> ${lines[index]}`)
      index++
    }
  }
  return result.join('\n')
}

function buildSegments(text) {
  const source = normalizeContainers(
    String(text || '').replace(/^---[\s\S]*?---\s*/, '').trim()
  )
  if (!source) return []
  const md = createMarkdown()
  const tokens = md.parse(source, {})
  decorateCallouts(tokens)
  const result = []
  let buffer = []
  const flush = () => {
    if (!buffer.length) return
    result.push({ type: 'html', html: md.renderer.render(buffer, md.options, {}) })
    buffer = []
  }
  for (const token of tokens) {
    const info = (token.info || '').trim().split(/\s+/)[0].toLowerCase()
    if (token.type === 'fence' && info === 'mermaid') {
      flush()
      result.push({ type: 'mermaid', code: token.content })
    } else {
      buffer.push(token)
    }
  }
  flush()
  return result
}

function enhanceCodeBlocks() {
  const element = root.value
  if (!element) return
  element.querySelectorAll('pre').forEach(pre => {
    if (pre.dataset.enhanced) return
    pre.dataset.enhanced = '1'
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'wiki-copy-code'
    button.title = 'Copy code'
    button.innerHTML = '<i class="fa-regular fa-copy"></i>'
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(pre.innerText.replace(/^Copy$/, '').trim())
        button.innerHTML = '<i class="fa-solid fa-check"></i>'
        setTimeout(() => { button.innerHTML = '<i class="fa-regular fa-copy"></i>' }, 1400)
      } catch {
        button.innerHTML = '<i class="fa-solid fa-xmark"></i>'
      }
    })
    pre.appendChild(button)
  })
}

function onRootClick(event) {
  const link = event.target.closest('[data-wiki-path]')
  if (!link) return
  event.preventDefault()
  event.stopPropagation()
  emit('open-page', link.getAttribute('data-wiki-path'))
}

onMounted(() => {
  nextTick(enhanceCodeBlocks)
})

watch(
  () => props.text,
  () => {
    segments.value = buildSegments(props.text)
    nextTick(enhanceCodeBlocks)
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  segments.value = []
})

const hasContent = computed(() => Boolean(String(props.text || '').trim()))
</script>

<template>
  <div
    ref="root"
    class="wiki-markdown prose max-w-none"
    :class="{ 'wiki-markdown-compact': compact, 'wiki-hide-title': hideTitle }"
    @click="onRootClick"
  >
    <template v-if="hasContent">
      <template v-for="(segment, index) in segments" :key="index">
        <div v-if="segment.type === 'html'" class="wiki-markdown-segment" v-html="segment.html"></div>
        <MermaidViewer
          v-else
          :diagram="segment.code"
          :editable="false"
          title="Architecture diagram"
          class="my-4"
        />
      </template>
    </template>
    <div v-else class="opacity-50 italic">No content yet.</div>
  </div>
</template>

<style scoped>
.wiki-markdown {
  font-size: 0.95rem;
  line-height: 1.75;
}
.wiki-markdown :deep(h1) {
  font-size: 2rem;
  line-height: 1.2;
  margin: 1.5rem 0 0.75rem;
}
.wiki-markdown :deep(h2) {
  font-size: 1.4rem;
  margin: 2rem 0 0.75rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
}
.wiki-markdown :deep(h3) {
  font-size: 1.1rem;
  margin: 1.5rem 0 0.5rem;
}
.wiki-markdown :deep(p) {
  margin: 0.65rem 0;
}
.wiki-markdown :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.wiki-markdown :deep(pre) {
  position: relative;
  margin: 1rem 0;
  padding: 1rem;
  border-radius: 0.75rem;
  overflow-x: auto;
  background: color-mix(in oklab, var(--color-base-300) 70%, transparent);
  border: 1px solid color-mix(in oklab, var(--color-base-content) 8%, transparent);
}
.wiki-markdown :deep(code:not(pre code)) {
  padding: 0.1rem 0.35rem;
  border-radius: 0.35rem;
  font-size: 0.85em;
  background: color-mix(in oklab, var(--color-base-content) 8%, transparent);
}
.wiki-markdown :deep(.wiki-copy-code) {
  position: absolute;
  top: 0.45rem;
  right: 0.45rem;
  width: 1.8rem;
  height: 1.8rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.45rem;
  border: 1px solid color-mix(in oklab, var(--color-base-content) 14%, transparent);
  background: var(--color-base-100);
  color: var(--color-base-content);
  opacity: 0;
  transition: opacity 0.15s ease;
}
.wiki-markdown :deep(pre:hover .wiki-copy-code) {
  opacity: 1;
}
.wiki-markdown :deep(.wiki-callout) {
  margin: 1rem 0;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid color-mix(in oklab, var(--color-base-content) 10%, transparent);
  border-left-width: 4px;
  background: color-mix(in oklab, var(--color-base-200) 75%, transparent);
}
.wiki-markdown :deep(.wiki-callout-label) {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.35rem;
}
.wiki-markdown :deep(.wiki-callout p) {
  margin: 0.2rem 0;
}
.wiki-markdown :deep(.wiki-callout-tip) { border-left-color: #22c55e; }
.wiki-markdown :deep(.wiki-callout-tip .wiki-callout-label) { color: #16a34a; }
.wiki-markdown :deep(.wiki-callout-note) { border-left-color: #3b82f6; }
.wiki-markdown :deep(.wiki-callout-note .wiki-callout-label) { color: #2563eb; }
.wiki-markdown :deep(.wiki-callout-warning) { border-left-color: #f59e0b; }
.wiki-markdown :deep(.wiki-callout-warning .wiki-callout-label) { color: #d97706; }
.wiki-markdown :deep(.wiki-callout-important) { border-left-color: #a855f7; }
.wiki-markdown :deep(.wiki-callout-important .wiki-callout-label) { color: #9333ea; }
.wiki-markdown :deep(.wiki-callout-caution) { border-left-color: #ef4444; }
.wiki-markdown :deep(.wiki-callout-caution .wiki-callout-label) { color: #dc2626; }
.wiki-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.88rem;
}
.wiki-markdown :deep(th),
.wiki-markdown :deep(td) {
  border: 1px solid color-mix(in oklab, var(--color-base-content) 12%, transparent);
  padding: 0.45rem 0.6rem;
  text-align: left;
  vertical-align: top;
}
.wiki-markdown :deep(th) {
  background: color-mix(in oklab, var(--color-base-200) 80%, transparent);
}
.wiki-markdown :deep(ul),
.wiki-markdown :deep(ol) {
  margin: 0.6rem 0 0.6rem 1.25rem;
}
.wiki-markdown :deep(li) {
  margin: 0.25rem 0;
}
.wiki-markdown :deep(blockquote:not(.wiki-callout)) {
  border-left: 3px solid color-mix(in oklab, var(--color-primary) 40%, transparent);
  padding-left: 0.9rem;
  opacity: 0.85;
}
.wiki-markdown :deep(.wiki-heading) {
  scroll-margin-top: 5rem;
}
.wiki-markdown :deep(img) {
  border-radius: 0.75rem;
  max-width: 100%;
}
.wiki-markdown-compact {
  font-size: 0.88rem;
}
.wiki-markdown-compact :deep(h1),
.wiki-markdown-compact :deep(h2) {
  font-size: 1.05rem;
  margin: 1rem 0 0.4rem;
  border-bottom: none;
}
.wiki-hide-title :deep(h1:first-of-type) {
  display: none;
}
</style>
