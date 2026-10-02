<script setup>
</script>

<template>
  <div class="flex items-center gap-1">
    <!-- Current branch display -->
    <div class="dropdown dropdown-hover">
      <div tabindex="0" class="flex items-center gap-1 cursor-pointer hover:text-primary transition-colors">
        <i class="fa-solid fa-code-branch text-info"></i>
        <span class="font-mono text-sm font-semibold">{{ currentBranch }}</span>
        <i class="fa-solid fa-chevron-down text-xs opacity-60"></i>
      </div>
      
      <!-- Branch dropdown menu -->
      <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-48 p-1 shadow border border-base-content/10 max-h-60 overflow-y-auto">
        <li v-for="branch in branches" :key="branch">
          <a 
            :class="currentBranch === branch ? 'active bg-primary/20 text-primary' : ''"
            @click="$emit('branch-selected', branch)">
            <span class="text-xs font-mono">{{ branch }}</span>
            <span v-if="currentBranch === branch" class="badge badge-xs badge-primary ml-auto">
              <i class="fa-solid fa-check"></i>
            </span>
          </a>
        </li>
        <li class="divider my-1" v-if="branches.length"></li>
        <li>
          <a @click="$emit('create-branch')" class="text-primary">
            <i class="fa-solid fa-plus text-xs"></i>
            <span class="text-xs">New branch</span>
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    currentBranch: {
      type: String,
      default: 'main'
    },
    branches: {
      type: Array,
      default: () => ['main']
    }
  }
}
</script>