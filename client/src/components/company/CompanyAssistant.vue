<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { API } from '@/api/api'

/**
 * The always-present codx-junior assistant of the company shell.
 *
 * This is the product: managers talk to it instead of opening screens. It asks
 * ONE question at a time (`state` from the backend), offers big quick-reply
 * buttons and only shows a settings form when the user explicitly asks for the
 * full settings view.
 *
 * It posts to `POST /api/companies/<id>/assistant` (see company/assistant.py).
 */
const props = defineProps({
  companyId: { type: String, default: '' },
  companyName: { type: String, default: '' },
  view: { type: String, default: 'overview' },
  canManage: { type: Boolean, default: false },
  canAdmin: { type: Boolean, default: false },
  // Docked panel on desktop; drawer/floating on phones.
  docked: { type: Boolean, default: false }
})

const emit = defineEmits(['refresh', 'navigate', 'deleted'])

const api = API.companies

const messages = ref([])
const question = ref('')
const thinking = ref(false)
const error = ref('')
const form = ref(null)
const formValues = reactive({})
const formError = ref('')
const submitting = ref(false)
const collapsed = ref(false)
const mobileOpen = ref(false)
const rootEl = ref(null)
const messagesEl = ref(null)
const inputEl = ref(null)
// Multi-turn slot filling: the backend returns the next question's state, the
// next message is the answer and the flow continues without any form.
const conversation = ref(null)
const quickOptions = ref([])
const remoteSuggestions = ref([])

const canManage = computed(() => props.canManage)
const canAdmin = computed(() => props.canAdmin)

const suggestions = computed(() => {
  if (conversation.value) return []
  if (remoteSuggestions.value.length) return remoteSuggestions.value.slice(0, 6)
  const general = [
    'What needs my attention?',
    'Show teams',
    'Show missions'
  ]
  if (canAdmin.value) general.push('Add a person')
  if (canManage.value) general.push('I need a team', 'Open company settings')
  return [...new Set(general)].slice(0, 6)
})

const placeholder = computed(() => (
  conversation.value ? 'Type your answer…' : 'Tell me what you need…'
))

const showLauncher = computed(() => !props.docked && !mobileOpen.value)

function optionLabel(option) {
  if (typeof option === 'string') return option
  return option?.label || option?.value || ''
}

function optionValue(option) {
  if (typeof option === 'string') return option
  return option?.value ?? option?.label ?? ''
}

// ── Rendering helpers ───────────────────────────────────────────────────────

function scrollToEnd() {
  nextTick(() => {
    const el = messagesEl.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function pushMessage(role, text, extra = {}) {
  messages.value.push({ role, text, ...extra })
  messages.value = messages.value.slice(-40)
  scrollToEnd()
}

function history() {
  return messages.value
    .filter(message => ['user', 'assistant'].includes(message.role))
    .map(message => ({
      role: message.role === 'assistant' ? 'assistant' : 'user',
      content: message.text
    }))
    .slice(-12)
}

/** Very small markdown renderer: keeps the panel dependency-free. */
function render(text) {
  if (!text) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.+)$/gm, '<div class="font-bold text-sm mt-2">$1</div>')
    .replace(/^- (.+)$/gm, '<div class="pl-2">• $1</div>')
    .replace(/\n/g, '<br/>')
}

// A local, instant greeting. It avoids a race between the first API turn and
// a one-shot intent ("Add a person") the shell may open right after mounting.
function bootstrapMessage() {
  messages.value = []
  question.value = ''
  conversation.value = null
  quickOptions.value = []
  remoteSuggestions.value = []
  applyForm(null)
  pushMessage(
    'assistant',
    `Hi — I'm **codx-junior**, the assistant of **${props.companyName || 'your company'}**. `
    + "Tell me what you need and I'll take care of it: add a person, build a team, "
    + "start a mission, or just ask what needs your attention."
    + (canManage.value ? '' : ' Your role is read-only here, so I can answer questions but changes need a manager.')
  )
}

// ── Assistant turns ─────────────────────────────────────────────────────────

async function ask(text, { silent = false, display = '' } = {}) {
  const companyId = props.companyId
  const message = String(text || '').trim()
  if (!companyId || thinking.value) return
  if (!message && !silent) return
  error.value = ''
  if (!silent) {
    pushMessage('user', display || message)
    question.value = ''
  }
  thinking.value = true
  try {
    const response = await api.assistant(companyId, {
      message,
      view: props.view,
      history: history(),
      state: conversation.value || {}
    })
    if (props.companyId !== companyId) return
    pushMessage('assistant', response?.reply || 'I have no answer for that yet.')
    conversation.value = response?.state || null
    quickOptions.value = response?.options || []
    remoteSuggestions.value = response?.suggestions || []
    applyForm(response?.form || null)
    if (response?.deleted) emit('deleted', response)
    else if (response?.changed) emit('refresh', { source: 'assistant' })
  } catch (ex) {
    const detail = ex?.response?.data?.detail || ex?.message || String(ex)
    error.value = detail
    if (!silent) pushMessage('assistant', `I could not do that: ${detail}`)
  } finally {
    thinking.value = false
  }
}

function send() {
  const text = question.value.trim()
  if (!text || thinking.value) return
  ask(text)
}

function submitForm() {
  if (!form.value || submitting.value) return
  formError.value = ''
  const values = { ...formValues }
  // Required-field validation is client-side too, so a form never posts half
  // an answer to the assistant.
  const missing = (form.value.fields || [])
    .filter(field => {
      if (!field.required) return false
      const value = values[field.name]
      return Array.isArray(value) ? !value.length : !String(value ?? '').trim()
    })
    .map(field => field.label || field.name)
  if (missing.length) {
    formError.value = `Required: ${missing.join(', ')}`
    return
  }
  submitting.value = true
  const companyId = props.companyId
  pushMessage('user', `Submit “${form.value.title}”`)
  api.assistant(companyId, {
    form_id: form.value.id,
    values,
    view: props.view,
    history: history(),
    state: conversation.value || {}
  }).then(response => {
    if (props.companyId !== companyId) return
    pushMessage('assistant', response?.reply || 'Done.')
    conversation.value = response?.state || null
    quickOptions.value = response?.options || []
    remoteSuggestions.value = response?.suggestions || []
    applyForm(response?.form || null)
    if (response?.deleted) emit('deleted', response)
    else if (response?.changed) emit('refresh', { source: 'assistant' })
  }).catch(ex => {
    formError.value = ex?.response?.data?.detail || ex?.message || String(ex)
  }).finally(() => {
    submitting.value = false
  })
}

function cancelForm() {
  applyForm(null)
  formError.value = ''
}

function applyForm(next) {
  form.value = next || null
  formError.value = ''
  Object.keys(formValues).forEach(key => delete formValues[key])
  if (next) {
    Object.assign(formValues, next.values || {})
    // Multiselects always start as arrays (the backend accepts both).
    ;(next.fields || []).forEach(field => {
      if (field.type === 'multiselect' && !Array.isArray(formValues[field.name])) {
        formValues[field.name] = formValues[field.name]
          ? [formValues[field.name]]
          : []
      }
    })
    nextTick(() => {
      const first = rootEl.value?.querySelector('[data-assistant-form] input, [data-assistant-form] select, [data-assistant-form] textarea')
      first?.focus?.()
    })
  }
}

function toggleMulti(field, value) {
  const current = Array.isArray(formValues[field.name]) ? formValues[field.name] : []
  const index = current.indexOf(value)
  if (index === -1) current.push(value)
  else current.splice(index, 1)
  formValues[field.name] = current
}

function isMultiSelected(field, value) {
  return Array.isArray(formValues[field.name]) && formValues[field.name].includes(value)
}

// ── Window controls ─────────────────────────────────────────────────────────

function collapse() {
  if (props.docked) collapsed.value = true
  else mobileOpen.value = false
}

function expand() {
  collapsed.value = false
  mobileOpen.value = true
  nextTick(() => inputEl.value?.focus?.())
}

function openWithPrompt(prompt = '') {
  expand()
  if (prompt) {
    question.value = prompt
    ask(prompt)
  }
}

function onExternalOpen(event) {
  const prompt = event?.detail?.prompt || ''
  openWithPrompt(prompt)
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

// ── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  window.addEventListener('company-assistant:open', onExternalOpen)
  if (props.companyId) bootstrapMessage()
})

onBeforeUnmount(() => {
  window.removeEventListener('company-assistant:open', onExternalOpen)
})

watch(() => props.companyId, companyId => {
  if (!companyId) return
  bootstrapMessage()
})
</script>

<template>
  <!-- Desktop: permanently docked column. A tiny rail keeps it reachable even
       when collapsed, so the assistant is never absent from a company view. -->
  <aside
    v-if="docked"
    ref="rootEl"
    class="company-assistant shrink-0 h-full border-l border-base-content/10 bg-base-100 flex flex-col transition-all duration-200"
    :class="collapsed ? 'w-12' : 'w-80 xl:w-[22rem]'"
    aria-label="codx-junior company assistant"
  >
    <template v-if="collapsed">
      <button class="flex-1 flex flex-col items-center gap-3 py-4 text-primary hover:bg-base-200/60"
              title="Open the codx-junior assistant" aria-label="Open the assistant"
              @click="expand">
        <img src="/only_icon.png" alt="codx-junior" class="w-8 h-8 rounded-full bg-base-300 shrink-0" />
        <i class="fa-solid fa-chevron-left text-xs"></i>
      </button>
    </template>

    <template v-else>
      <header class="shrink-0 flex items-center gap-2 px-3 py-2.5 border-b border-base-content/10 bg-gradient-to-r from-primary/10 to-transparent">
        <img src="/only_icon.png" alt="codx-junior" class="w-8 h-8 rounded-full bg-base-300 shrink-0" />
        <div class="min-w-0 flex-1">
          <div class="text-sm font-bold leading-tight truncate">codx-junior</div>
          <div class="text-[10px] text-base-content/50 truncate">
            {{ companyName || 'Company assistant' }} · {{ view }}
          </div>
        </div>
        <button class="btn btn-ghost btn-xs btn-square" title="Collapse" aria-label="Collapse assistant" @click="collapse">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </header>

      <div ref="messagesEl" class="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-2.5" aria-live="polite">
        <div v-if="!messages.length" class="text-xs text-base-content/50">
          <span class="loading loading-dots loading-xs"></span>
          Waking up the assistant…
        </div>
        <div v-for="(message, index) in messages" :key="index" class="chat"
             :class="message.role === 'user' ? 'chat-end' : 'chat-start'">
          <div class="chat-bubble text-xs leading-relaxed whitespace-normal"
               :class="message.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-neutral'"
               v-html="render(message.text)"></div>
        </div>
        <div v-if="thinking" class="chat chat-start">
          <div class="chat-bubble chat-bubble-neutral"><span class="loading loading-dots loading-xs"></span></div>
        </div>

        <!-- Forms are rendered HERE and nowhere else: settings dialogs live in
             the assistant window. -->
        <form v-if="form" data-assistant-form
              class="rounded-xl border border-primary/30 bg-primary/5 p-2.5 flex flex-col gap-2"
              @submit.prevent="submitForm">
          <div>
            <div class="text-xs font-bold">{{ form.title }}</div>
            <p v-if="form.description" class="text-[10px] text-base-content/50 mt-0.5">{{ form.description }}</p>
          </div>
          <label v-for="field in form.fields" :key="field.name" class="form-control">
            <span class="label-text text-[10px] uppercase tracking-wide text-base-content/50">
              {{ field.label }}<span v-if="field.required" class="text-error"> *</span>
            </span>

            <textarea v-if="field.type === 'textarea'" v-model="formValues[field.name]"
                      class="textarea textarea-xs textarea-bordered" rows="2"
                      :placeholder="field.placeholder || ''"></textarea>

            <select v-else-if="field.type === 'select'" v-model="formValues[field.name]"
                    class="select select-xs select-bordered">
              <option value="">—</option>
              <option v-for="option in (field.options || [])" :key="option.value || option"
                      :value="option.value || option">
                {{ option.label || option }}
              </option>
            </select>

            <div v-else-if="field.type === 'multiselect'" class="flex flex-wrap gap-1 pt-1">
              <label v-for="option in (field.options || [])" :key="option.value || option"
                     class="badge badge-sm cursor-pointer gap-1"
                     :class="isMultiSelected(field, option.value || option) ? 'badge-primary' : 'badge-ghost'">
                <input type="checkbox" class="checkbox checkbox-xs"
                       :checked="isMultiSelected(field, option.value || option)"
                       @change="toggleMulti(field, option.value || option)" />
                {{ option.label || option }}
              </label>
            </div>

            <input v-else v-model="formValues[field.name]"
                   class="input input-xs input-bordered"
                   :type="field.type === 'password' ? 'password' : field.type === 'email' ? 'email' : 'text'"
                   :placeholder="field.placeholder || ''" />
          </label>

          <p v-if="formError" class="text-[10px] text-error">{{ formError }}</p>

          <div class="flex items-center gap-1.5">
            <button type="button" class="btn btn-ghost btn-xs" @click="cancelForm">Cancel</button>
            <button type="submit" class="btn btn-primary btn-xs flex-1" :disabled="submitting">
              <span v-if="submitting" class="loading loading-spinner loading-xs"></span>
              {{ form.submit_label || 'Save' }}
            </button>
          </div>
        </form>
      </div>

      <p v-if="error" class="shrink-0 px-3 pb-1 text-[10px] text-error">{{ error }}</p>

      <div v-if="quickOptions.length" class="shrink-0 px-2 pb-1 flex flex-wrap gap-1">
        <button v-for="(option, index) in quickOptions" :key="index" type="button"
                class="btn btn-xs btn-primary btn-outline normal-case"
                :disabled="thinking" @click="ask(optionValue(option), { display: optionLabel(option) })">
          {{ optionLabel(option) }}
        </button>
      </div>

      <div class="shrink-0 px-2 pb-1 flex flex-wrap gap-1">
        <button v-for="suggestion in suggestions" :key="suggestion" type="button"
                class="btn btn-xs btn-ghost border border-base-content/10 normal-case"
                :disabled="thinking" @click="ask(suggestion)">{{ suggestion }}</button>
      </div>

      <form class="shrink-0 flex items-center gap-1.5 p-2.5 border-t border-base-content/10" @submit.prevent="send">
        <input ref="inputEl" v-model="question" type="text"
               class="input input-sm input-bordered flex-1"
               :placeholder="placeholder" aria-label="Message the company assistant"
               @keydown="onKeydown" />
        <button type="submit" class="btn btn-sm btn-primary btn-square"
                :disabled="!question.trim() || thinking" aria-label="Send">
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </form>

      <p v-if="!canManage" class="shrink-0 px-3 pb-2 text-[10px] text-base-content/40">
        Read-only role · ask a manager for changes
      </p>
    </template>
  </aside>

  <!-- Mobile/compact: a floating launcher that opens the same assistant as a
       bottom sheet. -->
  <template v-else>
    <button v-if="showLauncher"
            class="fixed z-40 right-3 bottom-[calc(env(safe-area-inset-bottom)+4.75rem)] w-12 h-12 rounded-full text-white shadow-lg grid place-items-center bg-gradient-to-br from-primary to-secondary"
            aria-label="Open the codx-junior assistant" @click="expand">
      <i class="fa-solid fa-wand-magic-sparkles"></i>
    </button>

    <section v-else ref="rootEl" class="fixed inset-x-0 bottom-0 z-50 h-[78vh] rounded-t-2xl flex flex-col bg-base-100 border-t border-base-content/15 shadow-2xl"
             aria-label="codx-junior company assistant">
      <header class="shrink-0 flex items-center gap-2 px-3 py-2 border-b border-base-content/10">
        <img src="/only_icon.png" alt="codx-junior" class="w-8 h-8 rounded-full bg-base-300 shrink-0" />
        <div class="min-w-0 flex-1">
          <div class="text-sm font-bold">codx-junior</div>
          <div class="text-[10px] text-base-content/50 truncate">{{ companyName }} · {{ view }}</div>
        </div>
        <button class="btn btn-ghost btn-xs btn-square" aria-label="Close assistant" @click="collapse">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </header>
      <div ref="messagesEl" class="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-2.5">
        <div v-for="(message, index) in messages" :key="index" class="chat"
             :class="message.role === 'user' ? 'chat-end' : 'chat-start'">
          <div class="chat-bubble text-xs" :class="message.role === 'user' ? 'chat-bubble-primary' : 'chat-bubble-neutral'"
               v-html="render(message.text)"></div>
        </div>
        <div v-if="thinking" class="chat chat-start">
          <div class="chat-bubble chat-bubble-neutral"><span class="loading loading-dots loading-xs"></span></div>
        </div>
        <form v-if="form" data-assistant-form class="rounded-xl border border-primary/30 bg-primary/5 p-2.5 flex flex-col gap-2"
              @submit.prevent="submitForm">
          <div class="text-xs font-bold">{{ form.title }}</div>
          <label v-for="field in form.fields" :key="field.name" class="form-control">
            <span class="label-text text-[10px]">{{ field.label }}</span>
            <textarea v-if="field.type === 'textarea'" v-model="formValues[field.name]" class="textarea textarea-xs textarea-bordered" rows="2"></textarea>
            <select v-else-if="field.type === 'select'" v-model="formValues[field.name]" class="select select-xs select-bordered">
              <option value="">—</option>
              <option v-for="option in (field.options || [])" :key="option.value || option" :value="option.value || option">{{ option.label || option }}</option>
            </select>
            <div v-else-if="field.type === 'multiselect'" class="flex flex-wrap gap-1 pt-1">
              <label v-for="option in (field.options || [])" :key="option.value || option"
                     class="badge badge-sm cursor-pointer gap-1"
                     :class="isMultiSelected(field, option.value || option) ? 'badge-primary' : 'badge-ghost'">
                <input type="checkbox" class="checkbox checkbox-xs"
                       :checked="isMultiSelected(field, option.value || option)"
                       @change="toggleMulti(field, option.value || option)" />
                {{ option.label || option }}
              </label>
            </div>
            <input v-else v-model="formValues[field.name]" class="input input-xs input-bordered" :type="field.type === 'password' ? 'password' : 'text'" />
          </label>
          <p v-if="formError" class="text-[10px] text-error">{{ formError }}</p>
          <div class="flex gap-1.5">
            <button type="button" class="btn btn-ghost btn-xs" @click="cancelForm">Cancel</button>
            <button type="submit" class="btn btn-primary btn-xs flex-1" :disabled="submitting">{{ form.submit_label || 'Save' }}</button>
          </div>
        </form>
      </div>
      <p v-if="error" class="shrink-0 px-3 pb-1 text-[10px] text-error">{{ error }}</p>
      <div v-if="quickOptions.length" class="shrink-0 px-2 pb-1 flex flex-wrap gap-1">
        <button v-for="(option, index) in quickOptions" :key="index" type="button"
                class="btn btn-xs btn-primary btn-outline normal-case"
                @click="ask(optionValue(option), { display: optionLabel(option) })">
          {{ optionLabel(option) }}
        </button>
      </div>
      <div class="shrink-0 px-2 pb-1 flex flex-wrap gap-1">
        <button v-for="suggestion in suggestions" :key="suggestion" type="button"
                class="btn btn-xs btn-ghost border border-base-content/10 normal-case"
                @click="ask(suggestion)">{{ suggestion }}</button>
      </div>
      <form class="shrink-0 flex gap-1.5 p-2 border-t border-base-content/10" @submit.prevent="send">
        <input v-model="question" type="text" class="input input-sm input-bordered flex-1" :placeholder="placeholder" />
        <button type="submit" class="btn btn-sm btn-primary btn-square" :disabled="!question.trim() || thinking">
          <i class="fa-solid fa-paper-plane"></i>
        </button>
      </form>
    </section>
  </template>
</template>

<style scoped>
.chat-bubble :deep(code) {
  font-size: 0.72rem;
  padding: 0 0.2rem;
  border-radius: 0.25rem;
  background: rgba(0, 0, 0, 0.18);
}
</style>

<!-- Made with ❤️ by codx-junior -->
