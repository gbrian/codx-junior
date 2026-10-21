<script setup>
import { computed, onMounted, ref } from 'vue'
import { $storex } from '@/store'
import { useSolopreneur } from './useSolopreneur'
import { useSolopreneurProjects } from './useSolopreneurProjects'

const { t, goModule } = useSolopreneur()

const {
  ui,
  sprintBoards,
  selectedSprint,
  visibleColumns,
  statusFilters,
  sprintStats,
  openTicket,
  ticketMessages,
  relative,
  statusLabel,
  ensureReady,
  setSprint,
  setFilter,
  setQuery,
  openTicketById,
  closeTicket,
  setTicketStatus,
  resumeTicket,
  sendTicketMessage,
  createTicket,
  createSprint
} = useSolopreneurProjects()

const projectName = computed(() => $storex.projects.activeProject?.project_name || '')

// When a single status chip is picked only that column is shown, so the board
// never becomes a wall of empty columns.
const boardColumns = computed(() =>
  ui.filter === 'all'
    ? visibleColumns.value
    : visibleColumns.value.filter(column => column.status === ui.filter)
)

const stats = computed(() => [
  { value: sprintStats.value.done, label: t('sp.done') },
  { value: sprintStats.value.doing, label: t('sp.doing') },
  { value: sprintStats.value.todo, label: t('sp.todo') },
  { value: sprintStats.value.onhold, label: t('sp.onhold'), warn: true }
])

// Statuses the drawer offers: the sprint's own columns (their labels included).
const drawerStatuses = computed(() =>
  visibleColumns.value.map(column => ({ value: column.status, label: column.title }))
)

const currentStatus = computed(() => openTicket.value?.status || 'todo')

const ticketDescription = computed(() => {
  const chat = openTicket.value
  if (!chat) return ''
  const field = String(chat.description || '').trim()
  if (field) return field
  const first = (chat.messages || []).find(m => m.role === 'user' && m.content)
  return first ? String(first.content).trim() : ''
})

const conversation = computed(() =>
  ticketMessages.value
    .filter(m => String(m.content || '').trim())
    .slice(-10)
)

function messageWho(message) {
  return message.role === 'user' ? t('sp.you') : t('sp.team')
}

// ── drawer composer ─────────────────────────────────────────────────────────
const message = ref('')

async function submitMessage() {
  const text = message.value
  const sent = await sendTicketMessage(text)
  if (sent) message.value = ''
}

async function moveTo(status) {
  await setTicketStatus(status)
}

// ── new ticket dialog ───────────────────────────────────────────────────────
const showNewTicket = ref(false)
const ticketName = ref('')
const ticketDetails = ref('')

function openNewTicket() {
  ticketName.value = ''
  ticketDetails.value = ''
  ui.errors = {}
  showNewTicket.value = true
}

function closeNewTicket() {
  showNewTicket.value = false
  ui.errors = {}
}

async function submitTicket() {
  const chat = await createTicket({ name: ticketName.value, details: ticketDetails.value })
  if (!chat) return
  closeNewTicket()
}

// ── new sprint dialog ───────────────────────────────────────────────────────
const showNewSprint = ref(false)
const sprintName = ref('')
const sprintDescription = ref('')

function openNewSprint() {
  sprintName.value = ''
  sprintDescription.value = ''
  ui.errors = {}
  showNewSprint.value = true
}

function closeNewSprint() {
  showNewSprint.value = false
  ui.errors = {}
}

async function submitSprint() {
  const board = await createSprint({ name: sprintName.value, description: sprintDescription.value })
  if (!board) return
  closeNewSprint()
}

onMounted(() => {
  ensureReady()
})
</script>

<template>
  <div class="mx-auto w-full max-w-6xl flex flex-col gap-6">
    <!-- No project -->
    <div
      v-if="!projectName"
      class="py-14 text-center text-sm text-base-content/50 bg-base-100 border border-dashed border-base-content/15 rounded-2xl"
    >
      {{ t('sp.noProject') }}
    </div>

    <template v-else>
      <!-- ══════════════ SPRINT HEADER ══════════════ -->
      <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 flex flex-col gap-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0">
            <nav class="flex items-center gap-2 text-sm text-base-content/40 min-w-0" aria-label="Breadcrumb">
              <button
                type="button"
                class="font-semibold text-base-content/60 hover:text-codx-primary transition-colors"
                @click="goModule('projects')"
              >{{ t('pp.back') }}</button>
              <span aria-hidden="true">/</span>
              <span class="truncate text-base-content/60">{{ projectName }}</span>
            </nav>

            <h1 class="text-2xl font-semibold tracking-tight mt-2.5 flex flex-wrap items-center gap-3">
              <span class="truncate">{{ selectedSprint ? selectedSprint.title : t('sp.title') }}</span>
              <span
                v-if="selectedSprint"
                class="text-[11px] font-semibold px-2.5 py-1 rounded-full text-codx-primary bg-codx-primary/10"
              >{{ sprintStats.progress }}%</span>
            </h1>
            <p class="text-sm text-base-content/50 mt-2">
              {{ selectedSprint && selectedSprint.last_update
                ? t('sp.updated') + ' ' + relative(selectedSprint.last_update)
                : t('sp.desc') }}
            </p>
          </div>

          <div class="flex flex-wrap items-end gap-3">
            <div v-if="sprintBoards.length > 1" class="flex flex-col gap-1.5">
              <label for="solo-sprint-select" class="text-[11px] font-semibold text-base-content/50 uppercase tracking-wide">
                {{ t('sp.sprint') }}
              </label>
              <select
                id="solo-sprint-select"
                :value="selectedSprint ? selectedSprint.id : ''"
                class="h-10 rounded-xl border border-base-content/15 bg-base-100 px-3 text-sm outline-none focus:border-codx-primary min-w-[200px]"
                @change="setSprint($event.target.value)"
              >
                <option v-for="board in sprintBoards" :key="board.id" :value="board.id">
                  {{ board.title }}
                </option>
              </select>
            </div>
            <button
              type="button"
              class="h-10 px-5 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition"
              @click="openNewSprint"
            >{{ t('sp.newSprint') }}</button>
            <button
              type="button"
              class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="!selectedSprint"
              @click="openNewTicket"
            >{{ t('sp.newTicket') }}</button>
          </div>
        </div>

        <!-- Progress + stats -->
        <template v-if="selectedSprint">
          <div class="h-2.5 rounded-full bg-base-content/10 overflow-hidden">
            <div class="h-full rounded-full bg-codx-primary transition-all" :style="{ width: sprintStats.progress + '%' }"></div>
          </div>

          <div class="grid gap-4 grid-cols-[repeat(auto-fit,minmax(min(100%,140px),1fr))]">
            <div
              v-for="stat in stats"
              :key="stat.label"
              class="rounded-xl p-4 flex flex-col gap-1"
              :class="stat.warn && stat.value ? 'bg-warning/15' : 'bg-base-200'"
            >
              <strong
                class="text-2xl font-semibold tracking-tight"
                :class="stat.warn && stat.value ? 'text-warning' : ''"
              >{{ stat.value }}</strong>
              <span class="text-xs text-base-content/50">{{ stat.label }}</span>
            </div>
          </div>
        </template>
      </section>

      <!-- No sprints yet -->
      <div
        v-if="!selectedSprint"
        class="py-14 px-6 text-center bg-base-100 border border-dashed border-base-content/15 rounded-2xl"
      >
        <p class="text-sm font-semibold">{{ t('sp.empty') }}</p>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('sp.emptyDesc') }}</p>
        <button
          type="button"
          class="mt-5 h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
          @click="openNewSprint"
        >{{ t('sp.createSprint') }}</button>
      </div>

      <template v-else>
        <!-- Banner: real "on hold" tasks wait on you -->
        <div
          v-if="sprintStats.onhold"
          class="flex flex-wrap items-center justify-between gap-4 bg-warning/10 border border-warning/30 rounded-2xl px-5 py-4"
        >
          <strong class="text-sm font-semibold">{{ t('sp.banner') }}</strong>
          <button
            type="button"
            class="h-9 px-4 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
            @click="setFilter('onhold')"
          >{{ t('sp.showMe') }}</button>
        </div>

        <!-- Toolbar -->
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex flex-wrap gap-2" role="group" :aria-label="t('sp.title')">
            <button
              v-for="chip in statusFilters"
              :key="chip.value"
              type="button"
              class="h-9 px-4 rounded-full border text-sm font-semibold inline-flex items-center gap-2 transition"
              :class="ui.filter === chip.value
                ? 'bg-base-content border-base-content text-base-100'
                : 'bg-base-100 border-base-content/15 text-base-content/60 hover:bg-base-200'"
              :aria-pressed="ui.filter === chip.value"
              @click="setFilter(chip.value)"
            >
              {{ chip.label }}
              <span class="text-xs opacity-60">{{ chip.count }}</span>
            </button>
          </div>
          <div class="grow"></div>
          <label class="sr-only" for="solo-sprint-search">{{ t('sp.search') }}</label>
          <input
            id="solo-sprint-search"
            :value="ui.query"
            type="search"
            autocomplete="off"
            :placeholder="t('sp.search')"
            class="h-9 w-full sm:w-56 rounded-full border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
            @input="setQuery($event.target.value)"
          />
        </div>

        <!-- Board -->
        <div
          v-if="boardColumns.length"
          class="grid gap-5 items-start grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))]"
        >
          <section
            v-for="column in boardColumns"
            :key="column.id"
            class="bg-base-200 rounded-2xl p-4 min-w-0"
            :aria-label="column.title"
          >
            <header class="flex items-center justify-between gap-2 mb-3.5 px-1">
              <h2 class="text-[11px] font-semibold uppercase tracking-wider text-base-content/60 truncate">
                {{ column.title }}
              </h2>
              <span class="text-[11px] font-semibold text-base-content/50 bg-base-content/10 rounded-full px-2 py-0.5">
                {{ column.tasks.length }}
              </span>
            </header>

            <div class="flex flex-col gap-3">
              <article
                v-for="task in column.tasks"
                :key="task.id"
                class="bg-base-100 border border-base-content/10 rounded-xl p-3.5 shadow-sm"
              >
                <button type="button" class="w-full text-left" @click="openTicketById(task.id)">
                  <div class="flex items-center gap-2 mb-2">
                    <span
                      v-if="(task.status || 'todo') === 'onhold'"
                      class="text-[10px] font-semibold px-2 py-0.5 rounded-full text-warning bg-warning/15"
                    >{{ t('sp.onhold') }}</span>
                    <span class="ml-auto text-[11px] text-base-content/40 whitespace-nowrap">
                      {{ relative(task.updated_at) }}
                    </span>
                  </div>
                  <span class="block text-sm font-semibold leading-snug break-words hover:text-codx-primary transition-colors">
                    {{ task.name || t('sp.untitled') }}
                  </span>
                </button>

                <button
                  v-if="(task.status || 'todo') === 'onhold'"
                  type="button"
                  class="mt-2.5 w-full h-8 rounded-full bg-base-content text-base-100 text-xs font-semibold hover:opacity-90 transition"
                  @click="resumeTicket(task.id)"
                >{{ t('sp.resume') }}</button>
              </article>

              <p v-if="!column.tasks.length" class="text-sm text-base-content/40 px-1 py-2">
                {{ t('sp.columnEmpty') }}
              </p>
            </div>
          </section>
        </div>

        <div
          v-else
          class="py-12 text-center text-sm text-base-content/50 bg-base-100 border border-dashed border-base-content/15 rounded-2xl"
        >
          {{ t('sp.noMatch') }}
        </div>
      </template>
    </template>

    <!-- ══════════════ TICKET DRAWER ══════════════ -->
    <div v-if="openTicket" class="fixed inset-0 z-[200]">
      <div class="absolute inset-0 bg-black/40" @click="closeTicket"></div>

      <aside
        class="absolute top-0 right-0 bottom-0 w-full max-w-lg bg-base-100 border-l border-base-content/10 shadow-2xl overflow-y-auto flex flex-col gap-4 p-6"
        role="dialog"
        aria-modal="true"
      >
        <div class="flex items-center gap-2">
          <span
            class="text-[11px] font-semibold px-2.5 py-1 rounded-full"
            :class="currentStatus === 'onhold'
              ? 'text-warning bg-warning/15'
              : currentStatus === 'done'
                ? 'text-success bg-success/15'
                : 'text-base-content/60 bg-base-content/10'"
          >{{ statusLabel(currentStatus) }}</span>
          <span class="text-xs text-base-content/40">{{ relative(openTicket.updated_at) }}</span>
          <button
            type="button"
            class="ml-auto w-9 h-9 rounded-full border border-base-content/15 hover:bg-base-200 transition grid place-items-center"
            :aria-label="t('common.close')"
            @click="closeTicket"
          >
            <i class="fa-solid fa-xmark text-sm"></i>
          </button>
        </div>

        <h2 class="text-xl font-semibold tracking-tight leading-snug break-words">
          {{ openTicket.name || t('sp.untitled') }}
        </h2>

        <!-- Description -->
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wider text-base-content/40 mb-2">
            {{ t('sp.description') }}
          </p>
          <p v-if="ticketDescription" class="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {{ ticketDescription }}
          </p>
          <p v-else class="text-sm text-base-content/50">{{ t('sp.noDescription') }}</p>
        </div>

        <!-- Status control -->
        <div v-if="drawerStatuses.length">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-base-content/40 mb-2">
            {{ t('sp.where') }}
          </p>
          <div class="inline-flex flex-wrap gap-1 bg-base-200 rounded-full p-1">
            <button
              v-for="status in drawerStatuses"
              :key="status.value"
              type="button"
              class="px-3.5 py-2 rounded-full text-xs font-semibold transition"
              :class="currentStatus === status.value
                ? 'bg-base-100 text-base-content shadow-sm'
                : 'text-base-content/50 hover:text-base-content'"
              :aria-pressed="currentStatus === status.value"
              @click="moveTo(status.value)"
            >{{ status.label }}</button>
          </div>
        </div>

        <div class="h-px bg-base-content/10"></div>

        <!-- Conversation -->
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wider text-base-content/40 mb-3">
            {{ t('sp.conversation') }}
          </p>

          <div v-if="conversation.length" class="flex flex-col gap-3.5">
            <div v-for="(m, i) in conversation" :key="i" class="flex flex-col gap-1">
              <span class="text-[10px] font-semibold uppercase tracking-wider text-base-content/40">
                {{ messageWho(m) }} · {{ relative(m.timestamp || m.created_at) }}
              </span>
              <p class="text-sm leading-relaxed whitespace-pre-wrap break-words">{{ m.content }}</p>
            </div>
          </div>
          <p v-else class="text-sm text-base-content/50">{{ t('sp.noMessages') }}</p>
        </div>

        <!-- Composer -->
        <form class="flex gap-2.5 mt-auto pt-4 sticky bottom-0 bg-base-100" @submit.prevent="submitMessage">
          <label class="sr-only" for="solo-ticket-message">{{ t('sp.commentPh') }}</label>
          <input
            id="solo-ticket-message"
            v-model="message"
            type="text"
            autocomplete="off"
            :placeholder="t('sp.commentPh')"
            class="flex-1 min-w-0 h-11 rounded-full border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
          />
          <button
            type="submit"
            :disabled="!message.trim()"
            class="h-11 px-5 rounded-full bg-codx-primary text-white text-sm font-semibold hover:opacity-90 transition disabled:opacity-40"
          >{{ t('sp.send') }}</button>
        </form>
      </aside>
    </div>

    <!-- ══════════════ NEW TICKET DIALOG ══════════════ -->
    <div v-if="showNewTicket" class="fixed inset-0 z-[200] flex items-center justify-center px-4">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeNewTicket"></div>

      <div
        class="relative w-full max-w-lg bg-base-100 border border-base-content/10 rounded-2xl shadow-2xl p-6"
        role="dialog"
        aria-modal="true"
      >
        <h2 class="text-lg font-semibold">{{ t('sp.newTicket') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('sp.newTicketDesc') }}</p>

        <form class="mt-5 flex flex-col gap-4" novalidate @submit.prevent="submitTicket">
          <div class="flex flex-col gap-1.5">
            <label for="solo-ticket-name" class="text-xs font-semibold text-base-content/60">{{ t('sp.ticketName') }}</label>
            <input
              id="solo-ticket-name"
              v-model="ticketName"
              type="text"
              :placeholder="t('sp.ticketNamePh')"
              class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
              :aria-invalid="!!ui.errors.name"
              autofocus
            />
            <span v-if="ui.errors.name" class="text-xs text-error">{{ ui.errors.name }}</span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label for="solo-ticket-details" class="text-xs font-semibold text-base-content/60">{{ t('sp.ticketDetails') }}</label>
            <textarea
              id="solo-ticket-details"
              v-model="ticketDetails"
              rows="3"
              class="rounded-xl border border-base-content/15 bg-base-100 px-4 py-3 text-sm outline-none focus:border-codx-primary resize-y"
            ></textarea>
          </div>

          <div class="flex justify-end gap-3 pt-1">
            <button
              type="button"
              class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition"
              @click="closeNewTicket"
            >{{ t('sp.cancel') }}</button>
            <button
              type="submit"
              class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
            >{{ t('sp.create') }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- ══════════════ NEW SPRINT DIALOG ══════════════ -->
    <div v-if="showNewSprint" class="fixed inset-0 z-[200] flex items-center justify-center px-4">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeNewSprint"></div>

      <div
        class="relative w-full max-w-lg bg-base-100 border border-base-content/10 rounded-2xl shadow-2xl p-6"
        role="dialog"
        aria-modal="true"
      >
        <h2 class="text-lg font-semibold">{{ t('sp.newSprint') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('sp.emptyDesc') }}</p>

        <form class="mt-5 flex flex-col gap-4" novalidate @submit.prevent="submitSprint">
          <div class="flex flex-col gap-1.5">
            <label for="solo-sprint-name" class="text-xs font-semibold text-base-content/60">{{ t('sp.sprintName') }}</label>
            <input
              id="solo-sprint-name"
              v-model="sprintName"
              type="text"
              :placeholder="t('sp.sprintNamePh')"
              class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
              :aria-invalid="!!ui.errors.sprint"
              autofocus
            />
            <span v-if="ui.errors.sprint" class="text-xs text-error">{{ ui.errors.sprint }}</span>
          </div>

          <div class="flex flex-col gap-1.5">
            <label for="solo-sprint-desc" class="text-xs font-semibold text-base-content/60">{{ t('sp.sprintDesc') }}</label>
            <input
              id="solo-sprint-desc"
              v-model="sprintDescription"
              type="text"
              class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary"
            />
          </div>

          <div class="flex justify-end gap-3 pt-1">
            <button
              type="button"
              class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition"
              @click="closeNewSprint"
            >{{ t('sp.cancel') }}</button>
            <button
              type="submit"
              class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
            >{{ t('sp.create') }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>