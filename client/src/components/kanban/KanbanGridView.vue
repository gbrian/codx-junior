<script setup>
import TaskCard from './TaskCard.vue'
import ChatIcon from '../chat/ChatIcon.vue'
import Collapsible from '../Collapsible.vue'
</script>

<template>
  <div class="flex flex-col gap-3 h-full">
    <!-- Filter bar via Collapsible -->
    <Collapsible>
      <!-- Icon -->
      <template #icon>
        <i class="fa-solid fa-filter text-xs opacity-60"></i>
      </template>

      <!-- Title -->
      <template #title>Filters</template>

      <!-- Active filter chips in header summary -->
      <template #summary>
        <span
          v-for="chip in activeFilterChips"
          :key="chip.key"
          class="badge badge-sm badge-primary gap-1"
        >
          {{ chip.label }}
          <i class="fa-solid fa-xmark cursor-pointer" @click.stop="clearFilter(chip.key)"></i>
        </span>
      </template>

      <!-- Header actions -->
      <template #actions>
        <div class="badge badge-ghost badge-sm">{{ filteredTasks.length }} tasks</div>
        <button v-if="hasActiveFilters" class="btn btn-xs btn-ghost" @click.stop="clearFilters">
          <i class="fa-solid fa-xmark"></i> Clear
        </button>
        <div
          tabindex="0"
          role="button"
          class="btn btn-xs btn-primary gap-1"
          @click.stop="$emit('new-task', { mode: 'chat' })"
        >
          <i class="fa-solid fa-plus"></i> New Task
        </div>
      </template>

      <!-- Collapsible filter body -->
      <div class="flex flex-wrap gap-2 p-2">
        <!-- Text search -->
        <div class="input input-sm input-bordered flex items-center gap-2 min-w-40">
          <i class="fa-solid fa-magnifying-glass text-xs opacity-50"></i>
          <input
            type="text"
            v-model="textFilter"
            placeholder="Search..."
            class="grow bg-transparent outline-none text-sm"
          />
          <span v-if="textFilter" class="cursor-pointer" @click="textFilter = ''">
            <i class="fa-regular fa-circle-xmark text-xs"></i>
          </span>
        </div>

        <!-- Column multi-select -->
        <div class="dropdown" @click.stop>
          <div
            tabindex="0"
            role="button"
            class="btn btn-sm btn-bordered gap-1"
            :class="columnFilter.length && 'btn-primary btn-outline'"
          >
            <i class="fa-solid fa-table-columns text-xs"></i>
            Columns
            <span v-if="columnFilter.length" class="badge badge-sm">{{ columnFilter.length }}</span>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-20 w-52 p-2 shadow">
            <li v-for="opt in availableColumns" :key="opt">
              <label class="flex gap-2 items-center cursor-pointer">
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs"
                  :checked="columnFilter.includes(opt)"
                  @change="toggleFilter('columnFilter', opt)"
                />
                {{ opt }}
              </label>
            </li>
            <li v-if="!availableColumns.length" class="text-xs opacity-50 p-2">No options</li>
          </ul>
        </div>

        <!-- Profile multi-select -->
        <div class="dropdown" @click.stop>
          <div
            tabindex="0"
            role="button"
            class="btn btn-sm btn-bordered gap-1"
            :class="profileFilter.length && 'btn-primary btn-outline'"
          >
            <i class="fa-solid fa-user text-xs"></i>
            Profiles
            <span v-if="profileFilter.length" class="badge badge-sm">{{ profileFilter.length }}</span>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-20 w-52 p-2 shadow">
            <li v-for="opt in availableProfiles" :key="opt">
              <label class="flex gap-2 items-center cursor-pointer">
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs"
                  :checked="profileFilter.includes(opt)"
                  @change="toggleFilter('profileFilter', opt)"
                />
                {{ opt }}
              </label>
            </li>
            <li v-if="!availableProfiles.length" class="text-xs opacity-50 p-2">No options</li>
          </ul>
        </div>

        <!-- Mode multi-select -->
        <div class="dropdown" @click.stop>
          <div
            tabindex="0"
            role="button"
            class="btn btn-sm btn-bordered gap-1"
            :class="modeFilter.length && 'btn-primary btn-outline'"
          >
            <i class="fa-solid fa-tag text-xs"></i>
            Types
            <span v-if="modeFilter.length" class="badge badge-sm">{{ modeFilter.length }}</span>
          </div>
          <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-20 w-52 p-2 shadow">
            <li v-for="opt in availableModes" :key="opt.value">
              <label class="flex gap-2 items-center cursor-pointer">
                <input
                  type="checkbox"
                  class="checkbox checkbox-xs"
                  :checked="modeFilter.includes(opt.value)"
                  @change="toggleFilter('modeFilter', opt.value)"
                />
                <ChatIcon :mode="opt.value" />
                {{ opt.label }}
              </label>
            </li>
            <li v-if="!availableModes.length" class="text-xs opacity-50 p-2">No options</li>
          </ul>
        </div>

        <!-- Date filter -->
        <select v-model="dateFilter" class="select select-sm select-bordered">
          <option value="">Any date</option>
          <option value="today">Today</option>
          <option value="week">This week</option>
          <option value="month">This month</option>
        </select>

        <!-- Pinned toggle -->
        <label class="label cursor-pointer gap-2">
          <span class="label-text text-sm">Pinned only</span>
          <input type="checkbox" v-model="pinnedOnly" class="checkbox checkbox-sm checkbox-warning" />
        </label>

        <!-- Divider row: group + sort -->
        <div class="w-full border-t border-base-300 mt-1 pt-1 flex flex-wrap gap-2 items-center">
          <div class="flex items-center gap-1">
            <i class="fa-solid fa-layer-group text-xs opacity-60"></i>
            <span class="text-xs opacity-60">Group by:</span>
            <select v-model="groupBy" class="select select-xs select-bordered">
              <option value="none">None</option>
              <option value="column">Column</option>
              <option value="mode">Type</option>
              <option value="profile">Profile</option>
            </select>
          </div>
          <div class="flex items-center gap-1">
            <i class="fa-solid fa-arrow-up-wide-short text-xs opacity-60"></i>
            <span class="text-xs opacity-60">Sort:</span>
            <select v-model="sortBy" class="select select-xs select-bordered">
              <option value="none">No sort</option>
              <option value="name_asc">Name A→Z</option>
              <option value="name_desc">Name Z→A</option>
              <option value="date_asc">Oldest first</option>
              <option value="date_desc">Newest first</option>
              <option value="pinned">Pinned first</option>
            </select>
          </div>
        </div>
      </div>
    </Collapsible>

    <!-- Grid content -->
    <div class="grow overflow-y-auto">
      <!-- Grouped view -->
      <div v-if="groupBy !== 'none'" class="flex flex-col gap-4">
        <div v-for="(group, groupKey) in groupedTasks" :key="groupKey">
          <div class="flex items-center gap-2 mb-2 sticky top-0 bg-base-100 z-10 py-1">
            <div class="badge badge-primary badge-outline">{{ groupKey }}</div>
            <div class="text-xs opacity-50">{{ group.length }} tasks</div>
            <div class="grow border-b border-base-300"></div>
          </div>
          <div class="grid grid-cols-1 @sm:grid-cols-2 @lg:grid-cols-3 @2xl:grid-cols-4 gap-3">
            <TaskCard
              v-for="task in group"
              :key="task.id"
              :task="task"
              class="cursor-pointer bg-base-200 overflow-hidden"
              :class="[
                task.pinned && 'border-warning border',
                lastUpdatedTaskId === task.id ? 'border border-primary border-dashed' : ''
              ]"
              @click="$emit('open-task', task)"
            />
          </div>
        </div>
        <div v-if="filteredTasks.length === 0" class="text-center opacity-40 py-10">
          <i class="fa-solid fa-inbox text-4xl mb-2"></i>
          <div>No tasks match your filters</div>
        </div>
      </div>

      <!-- Flat grid view -->
      <div v-else class="grid grid-cols-1 @sm:grid-cols-2 @lg:grid-cols-3 @2xl:grid-cols-4 gap-3">
        <TaskCard
          v-for="task in filteredTasks"
          :key="task.id"
          :task="task"
          class="cursor-pointer bg-base-200 overflow-hidden"
          :class="[
            task.pinned && 'border-warning border',
            lastUpdatedTaskId === task.id ? 'border border-primary border-dashed' : ''
          ]"
          @click="$emit('open-task', task)"
        />
        <div v-if="filteredTasks.length === 0" class="col-span-full text-center opacity-40 py-10">
          <i class="fa-solid fa-inbox text-4xl mb-2"></i>
          <div>No tasks match your filters</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
const MODE_LABELS = {
  chat: 'Chat',
  task: 'Document',
  topic: 'Discussion',
  prview: 'PR Review'
}

export default {
  emits: ['open-task', 'new-task'],
  props: {
    columns: { type: Array, default: () => [] },
    lastUpdatedTaskId: { type: String, default: null }
  },
  data() {
    return {
      textFilter: '',
      columnFilter: [],
      profileFilter: [],
      modeFilter: [],
      dateFilter: '',
      pinnedOnly: false,
      groupBy: 'column',
      sortBy: 'date_desc'
    }
  },
  computed: {
    // Flatten all tasks from all columns
    allTasks() {
      return this.columns.reduce((acc, col) => {
        return acc.concat(col.tasks.map(t => ({ ...t, _columnTitle: col.title, _columnColor: col.color })))
      }, [])
    },

    availableColumns() {
      return [...new Set(this.allTasks.map(t => t._columnTitle).filter(Boolean))]
    },
    availableProfiles() {
      const profiles = this.allTasks.flatMap(t => t.profiles || [])
      return [...new Set(profiles)]
    },
    availableModes() {
      const modes = [...new Set(this.allTasks.map(t => t.mode).filter(Boolean))]
      return modes.map(m => ({ value: m, label: MODE_LABELS[m] || m }))
    },

    filteredTasks() {
      return this.sortTasks(this.allTasks.filter(task => {
        if (this.columnFilter.length && !this.columnFilter.includes(task._columnTitle)) return false
        if (this.profileFilter.length && !this.profileFilter.some(p => (task.profiles || []).includes(p))) return false
        if (this.modeFilter.length && !this.modeFilter.includes(task.mode)) return false
        if (this.pinnedOnly && !task.pinned) return false
        if (this.textFilter) {
          const text = this.textFilter.toLowerCase()
          const inName = task.name?.toLowerCase().includes(text)
          const inMessages = task.messages?.some(m => m.content?.toLowerCase().includes(text))
          if (!inName && !inMessages) return false
        }
        if (this.dateFilter) {
          const updated = task.updated_at ? new Date(task.updated_at) : null
          if (!updated) return false
          const now = new Date()
          if (this.dateFilter === 'today' && updated.toDateString() !== now.toDateString()) return false
          if (this.dateFilter === 'week') {
            const weekAgo = new Date(now)
            weekAgo.setDate(now.getDate() - 7)
            if (updated < weekAgo) return false
          }
          if (this.dateFilter === 'month') {
            const monthAgo = new Date(now)
            monthAgo.setMonth(now.getMonth() - 1)
            if (updated < monthAgo) return false
          }
        }
        return true
      }))
    },

    groupedTasks() {
      return this.filteredTasks.reduce((acc, task) => {
        let key = 'Other'
        if (this.groupBy === 'column') key = task._columnTitle || 'No column'
        else if (this.groupBy === 'mode') key = MODE_LABELS[task.mode] || task.mode || 'No type'
        else if (this.groupBy === 'profile') key = (task.profiles || [])[0] || 'No profile'
        if (!acc[key]) acc[key] = []
        acc[key].push(task)
        return acc
      }, {})
    },

    hasActiveFilters() {
      return !!(
        this.textFilter ||
        this.columnFilter.length ||
        this.profileFilter.length ||
        this.modeFilter.length ||
        this.dateFilter ||
        this.pinnedOnly
      )
    },

    // Summary chips shown in collapsed filter header
    activeFilterChips() {
      const chips = []
      if (this.textFilter) chips.push({ key: 'textFilter', label: `"${this.textFilter}"` })
      if (this.columnFilter.length) chips.push({ key: 'columnFilter', label: `Cols: ${this.columnFilter.join(', ')}` })
      if (this.profileFilter.length) chips.push({ key: 'profileFilter', label: `Profiles: ${this.profileFilter.join(', ')}` })
      if (this.modeFilter.length) chips.push({ key: 'modeFilter', label: `Types: ${this.modeFilter.map(m => MODE_LABELS[m] || m).join(', ')}` })
      if (this.dateFilter) chips.push({ key: 'dateFilter', label: this.dateFilter })
      if (this.pinnedOnly) chips.push({ key: 'pinnedOnly', label: 'Pinned' })
      return chips
    }
  },
  methods: {
    toggleFilter(filterKey, value) {
      const arr = this[filterKey]
      const idx = arr.indexOf(value)
      if (idx === -1) arr.push(value)
      else arr.splice(idx, 1)
    },

    clearFilter(key) {
      if (Array.isArray(this[key])) this[key] = []
      else if (typeof this[key] === 'boolean') this[key] = false
      else this[key] = ''
    },

    clearFilters() {
      this.textFilter = ''
      this.columnFilter = []
      this.profileFilter = []
      this.modeFilter = []
      this.dateFilter = ''
      this.pinnedOnly = false
    },

    sortTasks(tasks) {
      if (this.sortBy === 'none') return tasks
      return [...tasks].sort((a, b) => {
        if (this.sortBy === 'name_asc') return (a.name || '').localeCompare(b.name || '')
        if (this.sortBy === 'name_desc') return (b.name || '').localeCompare(a.name || '')
        if (this.sortBy === 'date_asc') return new Date(a.updated_at || 0) - new Date(b.updated_at || 0)
        if (this.sortBy === 'date_desc') return new Date(b.updated_at || 0) - new Date(a.updated_at || 0)
        if (this.sortBy === 'pinned') return (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0)
        return 0
      })
    }
  }
}
</script>