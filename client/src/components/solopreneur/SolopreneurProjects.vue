<script setup>
import { ref, computed } from 'vue'
import { useSolopreneur } from './useSolopreneur'

const { state, t, shortDate, openModal } = useSolopreneur()

const query = ref('')
const sort = ref('progress')
const openProject = ref(null)

const list = computed(() => {
  const q = query.value.trim().toLowerCase()
  return state.projects
    .filter(p => !q || p.name.toLowerCase().includes(q))
    .slice()
    .sort((a, b) => (sort.value === 'name' ? a.name.localeCompare(b.name) : b.progress - a.progress))
})

function tasksOf(project) {
  return state.tasks.filter(x => x.context === project.name)
}

function toggle(project) {
  openProject.value = openProject.value === project.id ? null : project.id
}
</script>

<template>
  <div class="mx-auto w-full max-w-5xl">
    <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 md:p-8">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-base font-semibold">{{ t('pr.title') }}</h2>
          <p class="text-sm text-base-content/50 mt-1.5">{{ t('pr.desc') }}</p>
        </div>
        <button
          type="button"
          class="h-9 px-4 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition shrink-0"
          @click="openModal('newProject')"
        >{{ t('addProject') }}</button>
      </div>

      <!-- Toolbar -->
      <div class="flex flex-wrap items-center gap-3 mt-5">
        <label class="sr-only" for="solo-project-search">{{ t('pr.filter') }}</label>
        <input
          id="solo-project-search"
          v-model="query"
          type="search"
          :placeholder="t('pr.filter')"
          class="h-10 flex-1 min-w-[200px] max-w-sm rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
        />
        <label class="sr-only" for="solo-project-sort">Sort</label>
        <select
          id="solo-project-sort"
          v-model="sort"
          class="h-10 rounded-xl border border-base-content/15 bg-base-100 px-3 text-sm outline-none focus:border-codx-primary"
        >
          <option value="progress">{{ t('pr.sortProgress') }}</option>
          <option value="name">{{ t('pr.sortName') }}</option>
        </select>
      </div>

      <!-- Rows -->
      <div v-if="list.length" class="mt-5 flex flex-col gap-3">
        <div
          v-for="p in list"
          :key="p.id"
          class="border border-base-content/10 rounded-xl p-4"
          :class="openProject === p.id ? 'bg-base-200' : 'bg-base-100'"
        >
          <button
            type="button"
            class="flex items-center gap-4 w-full text-left"
            :aria-expanded="openProject === p.id"
            @click="toggle(p)"
          >
            <div class="flex-1 min-w-0">
              <h3 class="text-sm font-semibold">{{ p.name }}</h3>
              <small class="text-xs text-base-content/50">{{ p.tasks }} {{ t('pr.tasks') }} · {{ shortDate(p.updated) }}</small>
            </div>
            <div class="hidden sm:block w-40 h-1.5 rounded-full bg-base-content/10 overflow-hidden">
              <div class="h-full rounded-full bg-codx-primary" :style="{ width: p.progress + '%' }"></div>
            </div>
            <span class="text-sm font-semibold w-12 text-right">{{ p.progress }}%</span>
          </button>

          <div v-if="openProject === p.id" class="mt-4 pt-4 border-t border-dashed border-base-content/15">
            <ul v-if="tasksOf(p).length" class="flex flex-col gap-4">
              <li v-for="task in tasksOf(p)" :key="task.id" class="flex gap-3.5">
                <span
                  class="w-2 h-2 rounded-full shrink-0 mt-1.5"
                  :class="task.status === 'done' ? 'bg-success' : 'bg-codx-primary'"
                  aria-hidden="true"
                ></span>
                <div :class="task.status === 'done' ? 'opacity-60' : ''">
                  <button
                    type="button"
                    class="text-left text-sm font-semibold hover:text-codx-primary transition-colors"
                    :class="task.status === 'done' ? 'line-through' : ''"
                    @click="openModal('task', task.id)"
                  >{{ task.title }}</button>
                  <p class="text-xs text-base-content/50 mt-1">{{ task.time }} · {{ task.context }}</p>
                </div>
              </li>
            </ul>
            <p v-else class="text-sm text-base-content/50">{{ t('pr.noTasks') }}</p>
          </div>
        </div>
      </div>

      <div v-else class="mt-5 py-14 text-center text-sm text-base-content/50 bg-base-200 border border-dashed border-base-content/15 rounded-xl">
        {{ t('pr.empty') }}
      </div>
    </section>
  </div>
</template>