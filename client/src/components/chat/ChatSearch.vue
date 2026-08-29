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
      <button class="btn btn-sm btn-primary" @click="onSearch" :disabled="!localQuery || isSearching">
        <span v-if="isSearching" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fa-solid fa-search"></i>
      </button>
    </div>

    <!-- Date Filter Toggle -->
    <div class="flex gap-2 items-center">
      <label class="label cursor-pointer flex gap-2 flex-1">
        <span class="label-text text-sm">Date filter</span>
        <input type="checkbox" v-model="useDateFilter" class="checkbox checkbox-sm" />
      </label>
    </div>

    <!-- Date Range Options -->
    <div v-if="useDateFilter" class="flex flex-col gap-2 p-2 bg-base-100 rounded">
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
    <div class="flex gap-2 items-center">
      <label class="label cursor-pointer flex gap-2 flex-1">
        <span class="label-text text-sm">Customize search fields</span>
        <input type="checkbox" v-model="useCustomFilters" class="checkbox checkbox-sm" />
      </label>
    </div>

    <!-- Filter Checkboxes -->
    <div v-if="useCustomFilters" class="flex flex-col gap-2 p-2 bg-base-100 rounded">
      <div class="grid grid-cols-2 gap-2">
        <label v-for="(label, key) in filterLabels" :key="key" class="label cursor-pointer flex gap-2">
          <input type="checkbox" v-model="searchFilters[key]" class="checkbox checkbox-sm" />
          <span class="label-text text-sm">{{ label }}</span>
        </label>
      </div>
    </div>

    <!-- Status Message -->
    <div v-if="searchStatus" class="text-xs" :class="statusClass">
      {{ searchStatus }}
    </div>
  </div>
</template>

<script>
export default {
  props: {
    initialQuery: {
      type: String,
      default: null
    }
  },
  data() {
    return {
      localQuery: this.initialQuery || '',
      useDateFilter: false,
      selectedPreset: '3days',
      customFromDate: null,
      customToDate: null,
      useCustomFilters: false,
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
      currentPage: 1,
      pageSize: 20,
      isSearching: false,
      searchStatus: null,
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
        return 'text-error'
      }
      if (this.searchStatus.includes('No results')) {
        return 'text-warning'
      }
      return 'text-info'
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
    selectPreset(preset) {
      this.selectedPreset = preset
    },
    async onSearch() {
      if (!this.localQuery?.trim()) {
        this.searchStatus = 'Please enter a search query'
        return
      }

      this.isSearching = true
      this.searchStatus = null
      this.currentPage = 1

      try {
        const { from_date, to_date } = this.dateRange
        
        // CHANGED: Create ChatSearchRequest instance
        const searchRequest = new ChatSearchRequest({
          query: this.localQuery,
          from_date,
          to_date,
          page: this.currentPage,
          page_size: this.pageSize,
          filters: this.useCustomFilters ? this.searchFilters : {}
        })

        const results = await this.$storex.chats.searchChats(searchRequest)

        if (!results) {
          this.searchStatus = 'Search failed, please try again'
          this.$emit('error', 'Search failed')
          return
        }

        if (results.error) {
          this.searchStatus = `Error: ${results.error}`
          this.$emit('error', results.error)
          return
        }

        if (results.total === 0) {
          this.searchStatus = 'No results found'
          this.$emit('no-results')
        } else {
          this.searchStatus = `Found ${results.total} result${results.total !== 1 ? 's' : ''}`
          this.$emit('search', {
            results,
            query: this.localQuery,
            dateRange: this.dateRange,
            page: this.currentPage,
            pageSize: this.pageSize
          })
        }
      } catch (error) {
        console.error('Search error:', error)
        this.searchStatus = `Error: ${error.message}`
        this.$emit('error', error.message)
      } finally {
        this.isSearching = false
      }
    },
    async loadPage(page) {
      if (!this.localQuery?.trim()) return

      this.isSearching = true
      this.currentPage = page

      try {
        const { from_date, to_date } = this.dateRange
        
        // CHANGED: Create ChatSearchRequest instance for pagination
        const searchRequest = new ChatSearchRequest({
          query: this.localQuery,
          from_date,
          to_date,
          page,
          page_size: this.pageSize,
          filters: this.useCustomFilters ? this.searchFilters : {}
        })

        const results = await this.$storex.chats.searchChats(searchRequest)

        if (results && !results.error) {
          this.$emit('page-changed', {
            results,
            page,
            pageSize: this.pageSize,
            total: results.total,
            totalPages: results.total_pages
          })
        }
      } catch (error) {
        console.error('Pagination error:', error)
        this.$emit('error', error.message)
      } finally {
        this.isSearching = false
      }
    },
    clearSearch() {
      this.localQuery = ''
      this.searchStatus = null
      this.currentPage = 1
      this.$storex.chats.clearChatSearch()
      this.$emit('clear')
    },
    resetFilters() {
      this.useDateFilter = false
      this.selectedPreset = '3days'
      this.customFromDate = null
      this.customToDate = null
      this.useCustomFilters = false
      Object.keys(this.searchFilters).forEach(key => {
        this.searchFilters[key] = true
      })
    }
  }
}
</script>