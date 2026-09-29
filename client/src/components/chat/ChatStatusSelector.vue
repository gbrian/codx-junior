<script setup>
</script>

<template>
  <div class="dropdown dropdown-end">
    <button
      tabindex="0"
      role="button"
      :class="['btn btn-sm gap-2', getStatusClass(status)]"
      title="Change chat status"
    >
      <i :class="getStatusIcon(status)"></i>
      <span class="capitalize">{{ getStatusLabel(status) }}</span>
      <i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
    </button>
    <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box shadow-lg border border-base-300 z-150 w-44 p-1 mt-1">
      <li v-for="option in statusOptions" :key="option.value">
        <a
          @click="$emit('status-changed', option.value); closeDropdown()"
          :class="['flex items-center gap-2 text-sm', option.value === status ? 'active' : '']"
        >
          <i :class="option.icon"></i>
          {{ option.label }}
        </a>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'ChatStatusSelector',
  props: {
    status: { type: String, required: true }
  },
  emits: ['status-changed'],
  data() {
    return {
      statusOptions: [
        { value: 'todo',     label: 'To Do',    icon: 'fa-solid fa-circle-dot' },
        { value: 'doing',    label: 'Doing',    icon: 'fa-solid fa-circle-play text-primary' },
        { value: 'onhold',   label: 'On Hold',  icon: 'fa-solid fa-circle-pause text-warning' },
        { value: 'done',     label: 'Done',     icon: 'fa-solid fa-circle-check text-success' },
        { value: 'rejected', label: 'Rejected', icon: 'fa-solid fa-circle-xmark text-error' }
      ]
    }
  },
  methods: {
    getStatusIcon(status) {
      const option = this.statusOptions.find(o => o.value === status)
      return option ? option.icon : 'fa-solid fa-circle-dot text-info'
    },
    getStatusLabel(status) {
      const option = this.statusOptions.find(o => o.value === status)
      return option ? option.label : 'To Do'
    },
    getStatusClass(status) {
      const statusClasses = {
        'todo':     'btn-info btn-outline',
        'doing':    'btn-primary btn-outline',
        'onhold':   'btn-warning btn-outline',
        'done':     'btn-success btn-outline',
        'rejected': 'btn-error btn-outline'
      }
      return statusClasses[status] || 'btn-info btn-outline'
    },
    closeDropdown() {
      document.activeElement?.blur()
    }
  }
}
</script>