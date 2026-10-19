<script setup>
import { ref, computed, watch } from 'vue'
import { useSolopreneur } from './useSolopreneur'

const {
  state, t, money, PLANS, CREDIT_PACKS,
  closeModal, createProject, addCredits, changePlan, toggleTask, goModule, logout
} = useSolopreneur()

const modal = computed(() => state.ui.modal)

const name = ref('')
const tasksCount = ref(3)
const pack = ref(CREDIT_PACKS[0].id)
const plan = ref('basic')

const currentPlanId = computed(() => {
  const match = PLANS.find(p => p.name === state.wallet.plan)
  return match ? match.id : PLANS[0].id
})

const task = computed(() => {
  if (!modal.value || modal.value.type !== 'task') return null
  return state.tasks.find(x => x.id === modal.value.id) || null
})

const event = computed(() => {
  if (!modal.value || modal.value.type !== 'event') return null
  return state.events.find(e => e.id === modal.value.id) || null
})

watch(modal, (m) => {
  if (!m) return
  if (m.type === 'newProject') {
    name.value = ''
    tasksCount.value = 3
    state.ui.errors = {}
  }
  if (m.type === 'credits') pack.value = CREDIT_PACKS[0].id
  if (m.type === 'plan') plan.value = currentPlanId.value
})

function submitProject() {
  createProject({ name: name.value, tasks: tasksCount.value })
}

function submitCredits() { addCredits(pack.value) }
function submitPlan() { changePlan(plan.value) }

function messageTeam() {
  closeModal()
  goModule('messages')
}
</script>

<template>
  <div v-if="modal" class="fixed inset-0 z-[200] flex items-center justify-center px-4">
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeModal"></div>

    <div
      class="relative w-full max-w-lg max-h-[calc(100vh-4rem)] overflow-auto bg-base-100 border border-base-content/10 rounded-2xl shadow-2xl p-6"
      role="dialog"
      aria-modal="true"
    >
      <!-- Add new project -->
      <template v-if="modal.type === 'newProject'">
        <h2 class="text-lg font-semibold">{{ t('np.title') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('np.desc') }}</p>
        <form class="mt-5 flex flex-col gap-4" novalidate @submit.prevent="submitProject">
          <div class="flex flex-col gap-1.5">
            <label for="np-name" class="text-xs font-semibold text-base-content/60">{{ t('np.name') }}</label>
            <input
              id="np-name"
              v-model="name"
              type="text"
              :placeholder="t('np.namePh')"
              class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
              :aria-invalid="!!state.ui.errors.name"
            />
            <span v-if="state.ui.errors.name" class="text-xs text-error">{{ state.ui.errors.name }}</span>
          </div>
          <div class="flex flex-col gap-1.5">
            <label for="np-tasks" class="text-xs font-semibold text-base-content/60">{{ t('np.tasks') }}</label>
            <input
              id="np-tasks"
              v-model.number="tasksCount"
              type="number"
              min="0"
              max="50"
              class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary"
            />
          </div>
          <div class="flex justify-end gap-3 pt-1">
            <button type="button" class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition" @click="closeModal">
              {{ t('common.cancel') }}
            </button>
            <button type="submit" class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition">
              {{ t('common.create') }}
            </button>
          </div>
        </form>
      </template>

      <!-- Add credits -->
      <template v-else-if="modal.type === 'credits'">
        <h2 class="text-lg font-semibold">{{ t('wal.add') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('wal.desc') }}</p>
        <form class="mt-5 flex flex-col gap-2.5" @submit.prevent="submitCredits">
          <label
            v-for="p in CREDIT_PACKS"
            :key="p.id"
            class="flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition"
            :class="pack === p.id ? 'border-codx-primary bg-codx-primary/5' : 'border-base-content/15'"
          >
            <input v-model="pack" type="radio" name="pack" :value="p.id" class="accent-codx-primary" />
            <span class="flex flex-col text-sm">
              <strong class="font-semibold">{{ p.credits }} {{ t('wal.credits') }}</strong>
              <small class="text-base-content/50">{{ money(p.price) }}</small>
            </span>
          </label>
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition" @click="closeModal">
              {{ t('common.cancel') }}
            </button>
            <button type="submit" class="h-10 px-5 rounded-full bg-codx-primary text-white text-sm font-semibold hover:opacity-90 transition">
              {{ t('wal.buy') }}
            </button>
          </div>
        </form>
      </template>

      <!-- Change plan -->
      <template v-else-if="modal.type === 'plan'">
        <h2 class="text-lg font-semibold">{{ t('cp.title') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('cp.desc') }}</p>
        <form class="mt-5 flex flex-col gap-2.5" @submit.prevent="submitPlan">
          <label
            v-for="p in PLANS"
            :key="p.id"
            class="flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition"
            :class="plan === p.id ? 'border-codx-primary bg-codx-primary/5' : 'border-base-content/15'"
          >
            <input v-model="plan" type="radio" name="plan" :value="p.id" class="accent-codx-primary" />
            <span class="flex flex-col text-sm">
              <strong class="font-semibold">{{ p.name }} · {{ money(p.price) }}</strong>
              <small class="text-base-content/50">{{ p.note }}</small>
            </span>
          </label>
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition" @click="closeModal">
              {{ t('common.cancel') }}
            </button>
            <button type="submit" class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition">
              {{ t('common.save') }}
            </button>
          </div>
        </form>
      </template>

      <!-- Logout -->
      <template v-else-if="modal.type === 'logout'">
        <h2 class="text-lg font-semibold">{{ t('lo.title') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ t('lo.desc') }}</p>
        <div class="flex justify-end gap-3 pt-5">
          <button type="button" class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition" @click="closeModal">
            {{ t('common.cancel') }}
          </button>
          <button type="button" class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition" @click="logout">
            {{ t('logout') }}
          </button>
        </div>
      </template>

      <!-- Task -->
      <template v-else-if="modal.type === 'task' && task">
        <h2 class="text-lg font-semibold">{{ task.title }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ task.time }} · {{ task.context }}</p>
        <div class="mt-4 flex items-center justify-between gap-4 text-sm">
          <span class="text-base-content/50">{{ t('tk.progress') }}</span>
          <span class="font-semibold">{{ task.status === 'done' ? t('tk.done') : t('tk.progress') }}</span>
        </div>
        <div class="flex justify-end gap-3 pt-5">
          <button type="button" class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition" @click="closeModal">
            {{ t('common.close') }}
          </button>
          <button type="button" class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition" @click="toggleTask(task.id)">
            {{ task.status === 'done' ? t('tk.reopen') : t('tk.markDone') }}
          </button>
        </div>
      </template>

      <!-- Calendar event -->
      <template v-else-if="modal.type === 'event' && event">
        <h2 class="text-lg font-semibold">{{ event.title }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5">{{ event.group }} · {{ event.time }} · {{ event.meta }}</p>
        <div class="flex justify-end gap-3 pt-5">
          <button type="button" class="h-10 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition" @click="closeModal">
            {{ t('common.close') }}
          </button>
          <button type="button" class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition" @click="messageTeam">
            {{ t('cal.askTeam') }}
          </button>
        </div>
      </template>

      <!-- Fallback -->
      <template v-else>
        <div class="flex justify-end pt-2">
          <button type="button" class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition" @click="closeModal">
            {{ t('common.close') }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>