<template>
  <!-- ── Admin container shell ───────────────────────────────────────────────
       Teleported to <body> so it is viewport-sized even when opened from a
       resizable dockview panel or from the container detail modal. The xterm
       instance is created lazily on "Open shell": the app never pays for the
       terminal bundle until an admin actually uses it. -->
  <Teleport to="body">
    <div v-if="container" class="fixed inset-0 z-[100] flex items-center justify-center p-2 sm:p-4">
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="requestClose"></div>

      <div ref="dialogEl" role="dialog" aria-modal="true"
           :aria-label="`Container shell: ${container.name || container.id}`"
           class="relative z-10 flex flex-col w-full max-w-6xl h-[92vh] bg-base-100 border border-base-300 rounded-xl shadow-2xl overflow-hidden">

        <!-- ── Header ─────────────────────────────────────────────────────── -->
        <header class="shrink-0 px-4 py-3 border-b border-base-300 bg-base-200">
          <div class="flex items-center gap-2 min-w-0">
            <i class="fas fa-terminal text-primary shrink-0"></i>
            <div class="min-w-0 grow">
              <div class="text-lg font-bold leading-tight truncate flex items-center gap-2">
                {{ container.name || container.id }}
                <span class="badge badge-sm badge-outline">shell</span>
                <span class="badge badge-sm" :class="statusBadgeClass">{{ statusLabel }}</span>
              </div>
              <div class="text-xs opacity-50 font-mono truncate">
                {{ container.image || container.id }} · host {{ hostId }}
              </div>
            </div>

            <label class="hidden sm:flex items-center gap-1 text-xs opacity-70">
              Shell
              <select class="select select-bordered select-xs font-mono"
                      :value="shell" :disabled="busy" @change="shell = $event.target.value">
                <option v-for="s in SHELLS" :key="s" :value="s">{{ s }}</option>
              </select>
            </label>

            <button class="btn btn-sm btn-ghost btn-square shrink-0"
                    aria-label="Close container shell" title="Close" @click="requestClose">
              <i class="fas fa-xmark"></i>
            </button>
          </div>
        </header>

        <!-- ── Body ───────────────────────────────────────────────────────── -->
        <div class="grow min-h-0 flex flex-col bg-[#0b1220]">

          <!-- Intro: explicit consent before opening an exec session. -->
          <div v-if="status === 'idle'" class="grow min-h-0 overflow-auto p-5">
            <div class="max-w-2xl mx-auto space-y-4 text-sm">
              <div class="flex items-start gap-3 rounded-xl border border-warning/40 bg-warning/10 p-4">
                <i class="fas fa-triangle-exclamation text-warning text-xl mt-0.5"></i>
                <div class="space-y-1">
                  <p class="font-semibold">You are about to open an interactive shell inside a container.</p>
                  <p class="opacity-70 text-xs">
                    Commands run as the container's user with the container's permissions.
                    Changes are immediate and are not undoable through codx-junior.
                  </p>
                </div>
              </div>

              <div class="rounded-xl border border-base-300 bg-base-200 p-4 space-y-3">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-xs uppercase tracking-wide opacity-50">Container</span>
                  <span class="font-mono text-xs">{{ container.name || container.id }}</span>
                  <span class="badge badge-xs" :class="container.state === 'running' ? 'badge-success' : 'badge-ghost'">
                    {{ container.state || 'unknown' }}
                  </span>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-xs uppercase tracking-wide opacity-50">Shell</span>
                  <select class="select select-bordered select-sm font-mono" v-model="shell">
                    <option v-for="s in SHELLS" :key="s" :value="s">{{ s }}</option>
                  </select>
                  <span class="text-xs opacity-50">
                    If the container has no bash, use /bin/sh (or /bin/ash on Alpine).
                  </span>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-xs uppercase tracking-wide opacity-50">Session</span>
                  <span class="text-xs">Admin-only · single-use ticket · terminates when you close this panel</span>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <button class="btn btn-primary" :disabled="container.state !== 'running'" @click="start">
                  <i class="fas fa-terminal"></i> Open shell
                </button>
                <span v-if="container.state !== 'running'" class="text-xs text-warning">
                  Start the container before opening a shell.
                </span>
              </div>
            </div>
          </div>

          <!-- Terminal -->
          <div v-show="status !== 'idle'" class="grow min-h-0 flex flex-col">
            <div v-if="error" class="shrink-0 m-2 alert alert-error py-2 text-xs">
              <i class="fas fa-circle-exclamation"></i>
              <span class="min-w-0 break-words">{{ error }}</span>
            </div>

            <div ref="wrapEl" class="grow min-h-0 p-1.5 sm:p-2">
              <div ref="termEl" class="h-full w-full"></div>
            </div>
          </div>
        </div>

        <!-- ── Footer ─────────────────────────────────────────────────────── -->
        <footer class="shrink-0 px-4 py-2 border-t border-base-300 bg-base-200 flex flex-wrap items-center gap-3 text-xs">
          <span class="inline-flex items-center gap-1.5">
            <span class="inline-block w-2 h-2 rounded-full" :class="statusDotClass"></span>
            {{ statusLabel }}
          </span>
          <span v-if="status === 'connected'" class="opacity-50 hidden sm:inline">
            Ctrl+C interrupts · close this panel to end the session
          </span>
          <div class="flex-1"></div>

          <button v-if="status === 'closed' || status === 'error'" class="btn btn-xs btn-primary"
                  @click="start">
            <i class="fas fa-rotate-right"></i> Reconnect
          </button>
          <button v-if="busy" class="btn btn-xs btn-error btn-outline" @click="disconnect">
            <i class="fas fa-plug-circle-xmark"></i> Disconnect
          </button>
          <button v-else class="btn btn-xs btn-ghost" @click="requestClose">
            Close
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { API } from '../../api/api'

const props = defineProps({
  /** Container object from the infra store (id/name/image/state). */
  container: { type: Object, default: null },
  /** InfraHost.id the container lives on. */
  hostId: { type: String, default: 'host-local' }
})
const emit = defineEmits(['close'])

/** Shells the backend accepts (keep in sync with infra/shell.py). */
const SHELLS = ['/bin/sh', '/bin/bash', '/bin/ash', '/bin/zsh', '/bin/dash']

const dialogEl = ref(null)
const wrapEl = ref(null)
const termEl = ref(null)

const shell = ref('/bin/sh')
// idle | connecting | connected | closed | error
const status = ref('idle')
const error = ref('')

let term = null
let fitAddon = null
let socket = null
let resizeObserver = null
let intentionalClose = false
let disposed = false

const busy = computed(() => status.value === 'connecting' || status.value === 'connected')
const statusLabel = computed(() => ({
  idle: 'Not connected',
  connecting: 'Connecting…',
  connected: 'Connected',
  closed: 'Disconnected',
  error: 'Error'
}[status.value] || status.value))
const statusBadgeClass = computed(() => ({
  idle: 'badge-ghost',
  connecting: 'badge-warning',
  connected: 'badge-success',
  closed: 'badge-ghost',
  error: 'badge-error'
}[status.value] || 'badge-ghost'))
const statusDotClass = computed(() => ({
  idle: 'bg-base-content/30',
  connecting: 'bg-warning animate-pulse',
  connected: 'bg-success',
  closed: 'bg-base-content/30',
  error: 'bg-error'
}[status.value] || 'bg-base-content/30'))

/* ── base64 helpers ────────────────────────────────────────────────────────
   PTY bytes are not guaranteed to be valid UTF-8 (they can split a multi-byte
   sequence), so frames carry base64 instead of a JSON string. */
function bytesToBase64(bytes) {
  let binary = ''
  const chunk = 0x8000
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk))
  }
  return btoa(binary)
}

function base64ToBytes(value) {
  const binary = atob(value || '')
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

function encodeText(text) {
  return bytesToBase64(new TextEncoder().encode(text))
}

/* ── terminal lifecycle ──────────────────────────────────────────────────── */
function ensureTerminal() {
  if (term || !termEl.value) return
  term = new Terminal({
    cursorBlink: true,
    cursorStyle: 'block',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
    fontSize: 13,
    lineHeight: 1.2,
    scrollback: 5000,
    convertEol: false,
    allowProposedApi: false,
    theme: {
      background: '#0b1220',
      foreground: '#dbe4f0',
      cursor: '#60a5fa',
      selectionBackground: '#334155',
      black: '#1e293b',
      red: '#f87171',
      green: '#4ade80',
      yellow: '#facc15',
      blue: '#60a5fa',
      magenta: '#c084fc',
      cyan: '#22d3ee',
      white: '#e2e8f0',
      brightBlack: '#64748b',
      brightRed: '#fca5a5',
      brightGreen: '#86efac',
      brightYellow: '#fde047',
      brightBlue: '#93c5fd',
      brightMagenta: '#d8b4fe',
      brightCyan: '#67e8f9',
      brightWhite: '#f8fafc'
    }
  })
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(termEl.value)

  term.onData((data) => send({ type: 'input', data: encodeText(data) }))
  term.onResize(({ cols, rows }) => send({ type: 'resize', cols, rows }))

  resizeObserver = new ResizeObserver(() => {
    // A hidden dockview panel reports 0×0; fitting then would collapse the
    // terminal to one column, so only fit when the element is really visible.
    if (wrapEl.value?.clientWidth > 0) fitAddon?.fit()
  })
  if (wrapEl.value) resizeObserver.observe(wrapEl.value)

  requestAnimationFrame(() => {
    fitAddon?.fit()
    term?.focus()
  })
}

function disposeTerminal() {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (term) {
    try { term.dispose() } catch (_) { /* already disposed */ }
    term = null
  }
  fitAddon = null
}

function writeBanner(text, color = '36') {
  // xterm accepts ANSI escapes; CRLF keeps the banner readable on Windows too.
  term?.writeln(`\r\n\x1b[${color}m${text}\x1b[0m`)
}

/* ── WebSocket lifecycle ─────────────────────────────────────────────────── */
function websocketUrl(path) {
  const url = new URL(path, window.location.href)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  // The backend path never needs codx_path; the ticket is the credential.
  return url.toString()
}

function send(payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false
  try {
    socket.send(JSON.stringify(payload))
    return true
  } catch (_) {
    return false
  }
}

function closeSocket() {
  if (!socket) return
  try {
    socket.onopen = null
    socket.onmessage = null
    socket.onerror = null
    socket.onclose = null
    if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
      socket.close(1000, 'client closed')
    }
  } catch (_) { /* ignore */ }
  socket = null
}

async function start() {
  if (!props.container || busy.value) return

  // A previous attempt may have left a socket behind (e.g. reconnect after an
  // error); always start from a clean transport.
  closeSocket()
  status.value = 'connecting'
  error.value = ''
  intentionalClose = false

  await nextTick()
  ensureTerminal()
  if (!term) {
    status.value = 'error'
    error.value = 'The terminal could not be initialised in this browser.'
    return
  }
  term.reset()
  fitAddon?.fit()
  term.focus()

  let ticket
  try {
    ticket = await API.infra.shellTicket(props.container.id, {
      host_id: props.hostId,
      shell: shell.value,
      cols: term.cols,
      rows: term.rows
    })
  } catch (err) {
    status.value = 'error'
    // axios errors expose the backend detail in response.data.detail
    error.value = err?.response?.data?.detail || err?.message || String(err)
    writeBanner(`Could not open shell: ${error.value}`, '31')
    return
  }
  if (disposed) return

  writeBanner(`Connecting to ${props.container.name || props.container.id} (${shell.value})…`, '36')

  try {
    socket = new WebSocket(websocketUrl(ticket.websocket_path))
  } catch (err) {
    status.value = 'error'
    error.value = err?.message || String(err)
    writeBanner(`WebSocket failed: ${error.value}`, '31')
    return
  }

  socket.onopen = () => {
    status.value = 'connected'
    error.value = ''
    send({ type: 'resize', cols: term.cols, rows: term.rows })
    requestAnimationFrame(() => {
      fitAddon?.fit()
      term.focus()
    })
  }

  socket.onmessage = (event) => {
    let message
    try {
      message = JSON.parse(event.data)
    } catch (_) {
      return
    }
    const type = message?.type
    if (type === 'ready') {
      writeBanner(`Attached to ${message.container_id?.slice(0, 12) || props.container.id} · ${message.shell || shell.value}`, '32')
      return
    }
    if (type === 'output') {
      try {
        term.write(base64ToBytes(message.data))
      } catch (_) { /* malformed frame from a proxy: ignore */ }
      return
    }
    if (type === 'error') {
      error.value = message.message || 'The shell reported an error.'
      writeBanner(`Error: ${error.value}`, '31')
      return
    }
    if (type === 'exit') {
      status.value = 'closed'
      writeBanner(`Session ended${message.code == null ? '' : ` (exit ${message.code})`}.`, '33')
      closeSocket()
    }
  }

  socket.onerror = () => {
    // The close event carries the useful information; avoid a double banner.
  }

  socket.onclose = (event) => {
    if (intentionalClose) {
      writeBanner('Disconnected.', '33')
    } else if (status.value !== 'closed') {
      writeBanner(`Connection lost${event?.code ? ` (${event.code})` : ''}.`, '33')
      error.value = 'The shell connection was closed.'
    }
    if (status.value !== 'closed') status.value = 'closed'
    socket = null
  }
}

function disconnect() {
  intentionalClose = true
  send({ type: 'close' })
  closeSocket()
  status.value = 'closed'
  writeBanner('Disconnected.', '33')
  error.value = ''
}

function requestClose() {
  if (busy.value) {
    // Closing is destructive for the session, but never for the container.
    // The footer button is explicit enough; the header X acts the same way.
    disconnect()
  }
  closeSocket()
  disposeTerminal()
  emit('close')
}

function onKeydown(event) {
  if (event.key === 'Escape' && !busy.value) {
    event.preventDefault()
    requestClose()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  nextTick(() => dialogEl.value?.focus())
})

onBeforeUnmount(() => {
  disposed = true
  window.removeEventListener('keydown', onKeydown)
  closeSocket()
  disposeTerminal()
})

// When the container changes while the modal is open, disconnect: a shell
// session is bound to one container and must never silently retarget.
watch(() => props.container?.id, () => {
  if (busy.value) disconnect()
  status.value = 'idle'
  error.value = ''
})
</script>

<style scoped>
/* xterm injects its own layout; make sure the host element owns the full area
   and never grows past the modal body (the fit addon computes rows from it). */
:deep(.xterm) {
  height: 100%;
  width: 100%;
  padding: 4px;
}
:deep(.xterm-viewport) {
  background-color: transparent !important;
  scrollbar-width: thin;
}
</style>
