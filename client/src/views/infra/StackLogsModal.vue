<template>
  <!-- ── Compose logs overlay ────────────────────────────────────────────────
       Aggregated `docker compose logs` for ONE stack: every service, each line
       already prefixed by compose with its service name.

       It deliberately looks and behaves like the container log pane (tail
       selector, client-side search with highlights, follow, reload) so the
       operator reads both views the same way, and it is teleported to <body>
       so the overlay is sized by the VIEWPORT — not by the resizable dockview
       panel it was opened from. -->
  <Teleport to="body">
    <div v-if="logs.open" class="fixed inset-0 z-[80] flex items-center justify-center p-2 sm:p-4">
      <!-- backdrop -->
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeStackLogs"></div>

      <!-- dialog -->
      <div ref="dialogEl" role="dialog" aria-modal="true" tabindex="-1"
           :aria-label="`Compose logs: ${logs.name}`"
           class="relative z-10 flex flex-col w-full max-w-5xl h-[85vh] bg-base-100 border border-base-300 rounded-xl shadow-2xl overflow-hidden outline-none">

        <!-- ── Header ─────────────────────────────────────────────────────── -->
        <header class="shrink-0 px-4 py-3 border-b border-base-300 bg-base-200">
          <div class="flex items-start gap-2">
            <i class="fas fa-layer-group text-primary mt-1"></i>
            <div class="min-w-0 grow">
              <div class="text-lg font-bold leading-tight truncate flex items-center gap-2">
                {{ logs.name }}
                <span class="badge badge-sm badge-ghost">compose</span>
              </div>
              <div class="text-xs opacity-50 font-mono truncate">{{ logs.path || '—' }}</div>
            </div>
            <button class="btn btn-sm btn-ghost btn-square shrink-0"
                    aria-label="Close compose logs" title="Close (Esc)" @click="closeStackLogs">
              <i class="fas fa-xmark"></i>
            </button>
          </div>
        </header>

        <!-- ── Toolbar ────────────────────────────────────────────────────── -->
        <div class="shrink-0 flex flex-wrap items-center gap-2 px-4 py-2 border-b border-base-300">
          <span class="text-xs opacity-50 tabular-nums">
            <template v-if="logQuery.trim()">{{ logMatchCount }} of {{ logs.lines.length }} lines</template>
            <template v-else>{{ logs.lines.length }} lines</template>
          </span>

          <label class="sr-only" for="stack-log-tail">Log tail size</label>
          <select id="stack-log-tail" class="select select-bordered select-xs"
                  :value="logs.tail" :disabled="logs.loading" @change="onTailChange">
            <option :value="100">tail 100</option>
            <option :value="200">tail 200</option>
            <option :value="500">tail 500</option>
            <option :value="1000">tail 1000</option>
          </select>

          <!-- Search is CLIENT-SIDE: the tail is already in memory, so every
               keystroke filters instantly and never re-queries the daemon. -->
          <label class="input input-bordered input-xs flex items-center gap-1.5 grow min-w-40 max-w-80">
            <i class="fas fa-magnifying-glass opacity-50 text-[10px]"></i>
            <input ref="logSearchEl" type="text" class="grow min-w-0 text-xs"
                   aria-label="Search compose log lines"
                   placeholder="Search logs… (Ctrl+F)"
                   v-model="logQuery" />
            <button v-if="logQuery" type="button"
                    class="btn btn-xs btn-ghost btn-square -mr-1"
                    aria-label="Clear log search" title="Clear search"
                    @click="clearLogSearch">
              <i class="fas fa-xmark text-[10px]"></i>
            </button>
          </label>

          <span v-if="logQuery.trim()" role="status" aria-live="polite"
                class="badge badge-xs" :class="logMatchCount ? 'badge-primary' : 'badge-ghost'">
            {{ logMatchCount }} match{{ logMatchCount === 1 ? '' : 'es' }}
          </span>

          <div class="flex-1"></div>

          <label class="label cursor-pointer gap-2 py-0"
                 title="Keep the newest lines in view after reloading">
            <span class="label-text text-xs">Follow</span>
            <input type="checkbox" class="toggle toggle-xs toggle-primary" v-model="follow" />
          </label>

          <button class="btn btn-xs btn-ghost" :disabled="logs.loading" @click="reloadLogs">
            <i class="fas fa-rotate-right" :class="{ 'animate-spin': logs.loading }"></i>
            Reload
          </button>
        </div>

        <!-- ── Lines ──────────────────────────────────────────────────────── -->
        <div ref="logEl" class="grow min-h-0 overflow-auto bg-base-300/60">
          <div v-if="logs.loading && !logs.lines.length" class="p-4 space-y-2">
            <div v-for="i in 10" :key="i" class="skeleton h-4 w-full"></div>
          </div>

          <div v-else-if="logs.error" class="p-8 text-center text-xs space-y-2">
            <i class="fas fa-triangle-exclamation text-error text-2xl"></i>
            <p class="opacity-70 break-words max-w-lg mx-auto">{{ logs.error }}</p>
            <button class="btn btn-xs" @click="reloadLogs">
              <i class="fas fa-rotate-right"></i> Retry
            </button>
          </div>

          <p v-else-if="!logs.lines.length" class="p-8 text-center text-xs opacity-50">
            No log lines were returned for this stack.
          </p>

          <div v-else-if="!visibleLogs.length" class="p-8 text-center text-xs opacity-50 space-y-2">
            <i class="fas fa-magnifying-glass text-2xl"></i>
            <p>No lines match <span class="font-mono text-base-content">{{ logQuery.trim() }}</span></p>
            <button class="btn btn-xs" @click="clearLogSearch">
              <i class="fas fa-xmark"></i> Clear search
            </button>
          </div>

          <table v-else class="table table-xs font-mono text-[11px]">
            <tbody>
              <tr v-for="row in visibleLogs" :key="row.key" class="hover:bg-base-100/60">
                <td class="whitespace-nowrap opacity-40 align-top w-20">{{ fmtTime(row.line.ts) }}</td>
                <td class="whitespace-nowrap align-top w-14">
                  <span :class="logLevelClass(row.line.level)">{{ row.line.level }}</span>
                </td>
                <!-- Matches are wrapped in <mark>; `text-inherit` keeps the
                     level/monospace colour so hits only change the background. -->
                <td class="whitespace-pre-wrap break-all"><template v-for="(part, pi) in row.parts" :key="pi"><mark v-if="part.hit" class="rounded-sm bg-warning/40 px-0.5 text-inherit">{{ part.text }}</mark><span v-else>{{ part.text }}</span></template></td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ── Footer ─────────────────────────────────────────────────────── -->
        <footer class="shrink-0 px-4 py-2 border-t border-base-300 bg-base-200 flex items-center gap-3 text-xs">
          <span class="opacity-50 font-mono truncate">docker compose logs --tail {{ logs.tail }}</span>
          <div class="flex-1"></div>
          <button class="btn btn-sm btn-ghost" @click="closeStackLogs">Close</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { state, fmtTime } from './useInfra'
import { stackState, closeStackLogs, loadStackLogs } from './useInfraStacks'

const logs = computed(() => stackState.logs)

/* ── log pane state ───────────────────────────────────────────────────────── */
const follow = ref(true)

/**
 * Log search (client-side).
 *
 * The tail is already in memory (100…1000 lines of every service), so filtering
 * per keystroke is instant and never re-queries the daemon — the *fetch* stays
 * governed by the tail selector + Reload.
 */
const logQuery = ref('')
const logSearchEl = ref(null)

/** True when the line contains `term` in its message or its level. */
function matchesLine(line, term) {
  return String(line.msg ?? '').toLowerCase().includes(term)
    || String(line.level ?? '').toLowerCase().includes(term)
}

/**
 * Splits `text` on every occurrence of `term`.
 * @returns {Array<{text: string, hit: boolean}>} always at least one part, so
 * the template can render a single loop whether or not a search is active.
 */
function splitMatches(text, term) {
  const source = String(text ?? '')
  if (!term) return [{ text: source, hit: false }]
  const haystack = source.toLowerCase()
  const parts = []
  let cursor = 0
  let ix = haystack.indexOf(term)
  while (ix >= 0) {
    if (ix > cursor) parts.push({ text: source.slice(cursor, ix), hit: false })
    parts.push({ text: source.slice(ix, ix + term.length), hit: true })
    cursor = ix + term.length
    ix = haystack.indexOf(term, cursor)
  }
  if (cursor < source.length) parts.push({ text: source.slice(cursor), hit: false })
  return parts.length ? parts : [{ text: source, hit: false }]
}

/**
 * Rows to render: the whole tail, or only the matching lines.
 * `key` is the ORIGINAL index, so highlight spans are never reused for a
 * different line when the filter changes.
 */
const visibleLogs = computed(() => {
  const term = logQuery.value.trim().toLowerCase()
  const rows = []
  ;(logs.value.lines || []).forEach((line, i) => {
    if (term && !matchesLine(line, term)) return
    rows.push({ key: i, line, parts: splitMatches(line.msg, term) })
  })
  return rows
})

const logMatchCount = computed(() => visibleLogs.value.length)

function clearLogSearch() {
  logQuery.value = ''
  logSearchEl.value?.focus()
}

function logLevelClass(level) {
  return {
    ERROR: 'text-error font-semibold',
    WARN: 'text-warning',
    DEBUG: 'text-info/70'
  }[level] || 'text-success'
}

/* ── actions ──────────────────────────────────────────────────────────────── */
const dialogEl = ref(null)
const logEl = ref(null)

async function scrollLogsToBottom() {
  if (!follow.value) return
  await nextTick()
  const el = logEl.value
  if (el) el.scrollTop = el.scrollHeight
}

async function reloadLogs() {
  await loadStackLogs(logs.value.tail)
  scrollLogsToBottom()
}

function onTailChange(event) {
  loadStackLogs(Number(event.target.value) || 200)
  scrollLogsToBottom()
}

/* ── keyboard ─────────────────────────────────────────────────────────────── */
function onKeydown(event) {
  if (!logs.value.open) return

  // Ctrl/Cmd+F focuses the log search instead of the browser's find dialog
  // (which cannot match anything inside this teleported table).
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') {
    event.preventDefault()
    logSearchEl.value?.focus()
    logSearchEl.value?.select()
    return
  }

  if (event.key === 'Escape') {
    event.stopPropagation()
    // Escape clears an active log search first; a second Escape closes.
    if (logQuery.value) {
      clearLogSearch()
      return
    }
    closeStackLogs()
  }
}

/* ── lifecycle / watchers ─────────────────────────────────────────────────── */
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

watch(() => logs.value.open, async (open) => {
  if (!open) {
    // Never carry a query into the next stack: it would silently hide lines the
    // operator never asked to hide.
    logQuery.value = ''
    return
  }
  await nextTick()
  dialogEl.value?.focus()
  scrollLogsToBottom()
})

// New lines arrive as a fresh array; keep following the tail.
watch(() => logs.value.lines, () => scrollLogsToBottom())

// Leaving the Stacks tab (other tab) or switching host makes the overlay
// meaningless: its lines belong to a stack of the previous host/tab.
watch(() => state.route, (route) => {
  if (logs.value.open && route !== 'stacks') closeStackLogs()
})
watch(() => state.hostId, () => {
  if (logs.value.open) closeStackLogs()
})
</script>