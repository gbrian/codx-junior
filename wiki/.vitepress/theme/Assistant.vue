<script setup>
import { computed, nextTick, ref } from 'vue'
import { useData, useRoute } from 'vitepress'

const { site } = useData()
const route = useRoute()
const open = ref(false)
const loading = ref(false)
const input = ref('')
const messages = ref([
  {
    role: 'assistant',
    content: 'Ask me anything about this documentation. I answer from the generated wiki pages.'
  }
])
const scroller = ref(null)
const suggestions = [
  'What is this project and what problem does it solve?',
  'How do I install it?',
  'Give me a tour of the main features.'
]

const endpoint = computed(() => {
  const base = String(site.value.base || '/').replace(/\/$/, '')
  return `${base}/api/assistant`
})

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function renderMarkdown(value) {
  let html = escapeHtml(value)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="language-${escapeHtml(lang)}">${code}</code></pre>`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>')
  html = html.replace(/\n{2,}/g, '</p><p>')
  html = html.replace(/\n/g, '<br>')
  return `<p>${html}</p>`
}

function focusInput() {
  nextTick(() => document.getElementById('wiki-assistant-input')?.focus())
}

function scrollToBottom() {
  nextTick(() => {
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  })
}

async function send(question) {
  const text = (question || input.value || '').trim()
  if (!text || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  scrollToBottom()
  try {
    const history = messages.value.slice(-8).map(message => ({
      role: message.role,
      content: message.content
    }))
    const response = await fetch(endpoint.value, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: text,
        page: route.path,
        history
      })
    })
    if (!response.ok) throw new Error(`Assistant HTTP ${response.status}`)
    const data = await response.json()
    messages.value.push({
      role: 'assistant',
      content: data.answer || 'No answer available.',
      citations: data.citations || []
    })
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: 'The local AI is unavailable. Check the wiki server configuration.',
      citations: []
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<template>
  <div class="wiki-assistant">
    <button class="wiki-assistant-fab" type="button" aria-label="Open documentation assistant" @click="open = !open">
      <span v-if="open">×</span>
      <span v-else>AI</span>
    </button>

    <section v-if="open" class="wiki-assistant-panel">
      <header>
        <strong>Documentation assistant</strong>
        <small>Local AI · answers from this wiki</small>
      </header>

      <div ref="scroller" class="wiki-assistant-messages">
        <article v-for="(message, index) in messages" :key="index" :class="message.role">
          <div v-if="message.role === 'assistant'" class="wiki-assistant-markdown" v-html="renderMarkdown(message.content)"></div>
          <div v-else>{{ message.content }}</div>
          <div v-if="message.citations?.length" class="wiki-assistant-citations">
            <a v-for="citation in message.citations" :key="citation.path" :href="`${site.base}${citation.path}`">
              {{ citation.title || citation.path }}
            </a>
          </div>
        </article>

        <div v-if="messages.length === 1" class="wiki-assistant-suggestions">
          <button v-for="suggestion in suggestions" :key="suggestion" type="button" @click="send(suggestion)">
            {{ suggestion }}
          </button>
        </div>
        <div v-if="loading" class="wiki-assistant-loading">Searching the docs…</div>
      </div>

      <form class="wiki-assistant-input" @submit.prevent="send()">
        <input id="wiki-assistant-input" v-model="input" placeholder="Ask about the project…" />
        <button type="submit" :disabled="loading || !input.trim()">Send</button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.wiki-assistant { position: fixed; right: 1.25rem; bottom: 1.25rem; z-index: 100; font-family: var(--vp-font-family-base); }
.wiki-assistant-fab { width: 3rem; height: 3rem; border-radius: 999px; border: 1px solid var(--vp-c-divider); background: var(--vp-c-bg); color: var(--vp-c-text-1); font-weight: 700; cursor: pointer; box-shadow: 0 8px 30px rgba(0,0,0,.18); }
.wiki-assistant-panel { position: absolute; right: 0; bottom: 4rem; width: min(24rem, calc(100vw - 2rem)); height: min(32rem, calc(100vh - 8rem)); display: flex; flex-direction: column; background: var(--vp-c-bg); border: 1px solid var(--vp-c-divider); border-radius: 1rem; box-shadow: 0 20px 60px rgba(0,0,0,.25); overflow: hidden; }
.wiki-assistant-panel header { display: flex; flex-direction: column; gap: .1rem; padding: .8rem 1rem; border-bottom: 1px solid var(--vp-c-divider); }
.wiki-assistant-panel header small { color: var(--vp-c-text-2); }
.wiki-assistant-messages { flex: 1; overflow-y: auto; padding: .8rem; display: flex; flex-direction: column; gap: .6rem; }
.wiki-assistant-messages article { max-width: 92%; padding: .55rem .7rem; border-radius: .7rem; line-height: 1.5; font-size: .86rem; }
.wiki-assistant-messages article.user { align-self: flex-end; background: var(--vp-c-brand-1); color: #fff; }
.wiki-assistant-messages article.assistant { align-self: flex-start; background: var(--vp-c-bg-soft); }
.wiki-assistant-markdown :deep(pre) { overflow-x: auto; padding: .5rem; border-radius: .4rem; background: var(--vp-c-bg-alt); }
.wiki-assistant-markdown :deep(code) { font-size: .8em; }
.wiki-assistant-citations { display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .4rem; }
.wiki-assistant-citations a { font-size: .7rem; color: var(--vp-c-brand-1); text-decoration: underline; }
.wiki-assistant-suggestions { display: flex; flex-direction: column; gap: .35rem; }
.wiki-assistant-suggestions button { text-align: left; padding: .45rem .55rem; border: 1px solid var(--vp-c-divider); border-radius: .5rem; background: transparent; color: var(--vp-c-text-2); font-size: .75rem; cursor: pointer; }
.wiki-assistant-input { display: flex; gap: .4rem; padding: .6rem; border-top: 1px solid var(--vp-c-divider); }
.wiki-assistant-input input { flex: 1; min-width: 0; padding: .5rem .6rem; border: 1px solid var(--vp-c-divider); border-radius: .45rem; background: var(--vp-c-bg); color: var(--vp-c-text-1); }
.wiki-assistant-input button { padding: .45rem .7rem; border: 0; border-radius: .45rem; background: var(--vp-c-brand-1); color: #fff; cursor: pointer; }
.wiki-assistant-input button:disabled { opacity: .5; cursor: default; }
.wiki-assistant-loading { font-size: .75rem; color: var(--vp-c-text-2); }
</style>
