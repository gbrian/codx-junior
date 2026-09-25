<script setup>
import { v4 as uuidv4 } from 'uuid'
import { ChatSearchRequest } from '@/api/model/ChatSearchRequest'
</script>

<template>
  <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
    <!-- Search Query Input -->
    <div class="flex gap-2">
      <div class="flex-1 flex input input-sm input-bordered items-center gap-2">
        <i class="fa-solid fa-magnifying-glass text-base-content/50"></i>
        <input
          v-model="localQuery"
          type="text"
          class="bg-transparent w-full min-w-0"
          placeholder="Search chats..."
          @keydown.enter="onSearch"
        />
        <span v-if="localQuery" class="text-error cursor-pointer" @click="clearSearch">
          <i class="fa-regular fa-circle-xmark"></i>
        </span>
      </div>
      <button class="btn btn-sm btn-primary" @click="onSearch" :disabled="isSearching">
        <span v-if="isSearching" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-search"></i>
      </button>
    </div>

    <!-- Status Message -->
    <div v-if="searchStatus" class="text-xs px-2 py-1 rounded" :class="statusClass">
      {{ searchStatus }}
    </div>

    <!-- Expand/Collapse Settings -->
    <button 
      @click="toggleSettings"
      class="btn btn-xs btn-ghost gap-1 justify-start"
    >
      <i :class="showSettings ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'"></i>
      <span>{{ showSettings ? 'Hide' : 'Show' }} Settings</span>
    </button>

    <!-- Date Filter Toggle -->
    <div v-if="showSettings" class="flex gap-2 items-center">
      <label class="label cursor-pointer flex gap-2 flex-1">
        <input type="checkbox" v-model="useDateFilter" class="checkbox checkbox-sm" />
        <span class="label-text text-sm">Date filter</span>
      </label>
    </div>

    <!-- Date Range Options -->
    <div v-if="showSettings && useDateFilter" class="flex flex-col gap-2 p-2 bg-base-100 rounded">
      <!-- Preset Options -->
      <div class="flex gap-2 flex-wrap">
        <button
          v-for="preset in datePresets"
          :key="preset.value"
          class="btn btn-xs"
          :class="selectedPreset === preset.value ? 'btn-primary' : 'btn-ghost'"
          @click="selectPreset(preset.value)"
        >
          {{ preset.label }}
        </button>
        <button
          class="btn btn-xs"
          :class="selectedPreset === 'custom' ? 'btn-primary' : 'btn-ghost'"
          @click="selectedPreset = 'custom'"
        >
          Custom
        </button>
      </div>

      <!-- Custom Date Range -->
      <div v-if="selectedPreset === 'custom'" class="flex gap-2">
        <div class="flex flex-col flex-1 gap-1">
          <label class="label label-text text-xs">From</label>
          <input v-model="customFromDate" type="date" class="input input-sm input-bordered" />
        </div>
        <div class="flex flex-col flex-1 gap-1">
          <label class="label label-text text-xs">To</label>
          <input v-model="customToDate" type="date" class="input input-sm input-bordered" />
        </div>
      </div>
    </div>

    <!-- Search Field Filters -->
    <div v-if="showSettings" class="flex gap-2 items-center">
      <label class="label cursor-pointer flex gap-2 flex-1">
        <input type="checkbox" v-model="useCustomFilters" class="checkbox checkbox-sm" />
        <span class="label-text text-sm">Customize search fields</span>
      </label>
    </div>

    <!-- Filter Checkboxes -->
    <div v-if="showSettings && useCustomFilters" class="flex flex-col gap-2 p-2 bg-base-100 rounded">
      <div class="grid grid-cols-2 gap-2">
        <label v-for="(label, key) in filterLabels" :key="key" class="label cursor-pointer flex gap-2">
          <input type="checkbox" v-model="searchFilters[key]" class="checkbox checkbox-sm" />
          <span class="label-text text-sm">{{ label }}</span>
        </label>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    initialQuery: {
      type: String,
      default: null
    },
    userId: {
      type: String,
      default: null
    },
    isSearching: {
      type: Boolean,
      default: false
    },
    searchStatus: {
      type: String,
      default: null
    }
  },
  emits: ['search', 'clear'],
  data() {
    return {
      localQuery: this.initialQuery || '',
      showSettings: false,
      useDateFilter: true,
      selectedPreset: '3days',
      customFromDate: null,
      customToDate: null,
      useCustomFilters: true,
      searchFilters: {
        search_name: true,
        search_description: true,
        search_messages: true,
        search_message_metadata: true,
        search_history: true,
        search_files: true,
        search_model: true,
        search_status: true,
        search_mode: true
      },
      filterLabels: {
        search_name: 'Chat Name',
        search_description: 'Description',
        search_messages: 'Messages',
        search_message_metadata: 'Message Metadata',
        search_history: 'History',
        search_files: 'Files',
        search_model: 'LLM Model',
        search_status: 'Status',
        search_mode: 'Mode'
      },
      datePresets: [
        { label: 'Today', value: '1days' },
        { label: 'Last 3 days', value: '3days' },
        { label: 'Last 5 days', value: '5days' },
        { label: 'Last 7 days', value: '7days' },
        { label: 'Last 30 days', value: '30days' },
        { label: 'Last 90 days', value: '90days' },
        { label: 'All time', value: 'alltime' }
      ]
    }
  },
  computed: {
    statusClass() {
      if (!this.searchStatus) return ''
      if (this.searchStatus.includes('error') || this.searchStatus.includes('Error')) {
        return 'bg-error/20 text-error'
      }
      if (this.searchStatus.includes('No results')) {
        return 'bg-warning/20 text-warning'
      }
      return 'bg-info/20 text-info'
    },
    dateRange() {
      if (!this.useDateFilter) return { from_date: null, to_date: null }

      const now = new Date()
      let fromDate = null

      if (this.selectedPreset === 'custom') {
        fromDate = this.customFromDate ? new Date(this.customFromDate) : null
        const toDate = this.customToDate ? new Date(this.customToDate) : now
        return {
          from_date: fromDate ? fromDate.toISOString().split('T')[0] : null,
          to_date: toDate.toISOString().split('T')[0]
        }
      }

      const daysMap = { '1days': 1, '3days': 3, '5days': 5, '7days': 7, '30days': 30, '90days': 90, 'alltime': null }
      const days = daysMap[this.selectedPreset]

      if (days) {
        fromDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
      }

      return {
        from_date: fromDate ? fromDate.toISOString().split('T')[0] : null,
        to_date: now.toISOString().split('T')[0]
      }
    }
  },
  methods: {
    toggleSettings() {
      this.showSettings = !this.showSettings
    },
    selectPreset(preset) {
      this.selectedPreset = preset
    },
    onSearch() {
      const { from_date, to_date } = this.dateRange

      const searchPayload = {
        query: this.localQuery,
        dateRange: { from_date, to_date },
        filters: this.useCustomFilters ? this.searchFilters : {},
        page: 1,
        pageSize: 20
      }

      // Collapse settings after search
      this.showSettings = false

      this.$emit('search', searchPayload)
    },
    clearSearch() {
      this.localQuery = ''
      this.$emit('clear')
    },
    resetFilters() {
      this.selectedPreset = '3days'
      this.customFromDate = null
      this.customToDate = null
      Object.keys(this.searchFilters).forEach(key => {
        this.searchFilters[key] = true
      })
    }
  }
}
</script>