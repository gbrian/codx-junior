<script setup>
</script>

<template>
  <div class="dropdown dropdown-end z-50">
    <button
      tabindex="0"
      role="button"
      :class="['btn btn-sm gap-2', $chats.statusBtnClass(status), compact && 'px-2']"
      :title="compact ? $chats.statusLabel(status) : 'Change chat status'"
    >
      <i :class="$chats.statusIcon(status)"></i>
      <span class="capitalize" v-if="!compact">{{ $chats.statusLabel(status) }}</span>
      <i class="fa-solid fa-chevron-down text-xs opacity-60" v-if="!compact"></i>
    </button>
    <ul tabindex="0" class="dropdown-content bg-base-100 menu rounded-box shadow-lg w-44 p-1 z-50 text-sm">
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
    status: { type: String, required: true },
    compact: { type: Boolean, default: false }
  },
  emits: ['status-changed'],
  methods: {
    closeDropdown() {
      document.activeElement?.blur()
    }
  }
}
</script>