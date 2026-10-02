<script setup>
</script>

<template>
  <div class="dropdown dropdown-end">
    <button
      tabindex="0"
      role="button"
      :class="['btn btn-sm gap-2', $chats.statusBtnClass(status)]"
      title="Change chat status"
    >
      <i :class="$chats.statusIcon(status)"></i>
      <span class="capitalize">{{ $chats.statusLabel(status) }}</span>
      <i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
    </button>
    <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box shadow-lg border border-base-100 z-150 w-44 p-1 mt-1">
      <li v-for="option in $chats.statusList" :key="option.value">
        <a
          @click="$emit('status-changed', option.value); closeDropdown()"
          :class="['flex items-center gap-2 text-sm', option.value === status ? 'active' : '']"
        >
          <i :class="[option.icon, option.textColor]"></i>
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
  methods: {
    closeDropdown() {
      document.activeElement?.blur()
    }
  }
}
</script>