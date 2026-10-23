<script setup>
import WallAvatar from './WallAvatar.vue'
</script>

<template>
  <div class="flex flex-col gap-3 pb-6">
    <!-- Search -->
    <label class="input input-bordered flex items-center gap-2 rounded-full">
      <i class="fa-solid fa-magnifying-glass text-base-content/40"></i>
      <input
        :value="query"
        type="search"
        class="grow"
        placeholder="Search activity…"
        aria-label="Search activity"
        @input="$emit('search', $event.target.value)"
      />
    </label>

    <!-- Trending boards -->
    <div class="card bg-base-200">
      <div class="card-body p-4 gap-2">
        <h2 class="font-bold text-lg">Trending boards</h2>
        <button
          v-for="trend in trends"
          :key="trend.query"
          class="text-left hover:bg-base-300 rounded-lg p-2 -mx-2 transition-colors"
          @click="$emit('search', trend.query)"
        >
          <div class="text-xs text-base-content/50">{{ trend.label }}</div>
          <div class="font-bold text-sm">{{ trend.query }}</div>
          <div class="text-xs text-base-content/50">{{ trend.count }} task(s)</div>
        </button>
        <div v-if="!trends.length" class="text-sm text-base-content/50">No boards yet</div>
      </div>
    </div>

    <!-- Who to follow -->
    <div class="card bg-base-200">
      <div class="card-body p-4 gap-2">
        <h2 class="font-bold text-lg">Who to follow</h2>
        <div v-for="account in suggestions" :key="account.id" class="flex items-center gap-3">
          <WallAvatar :account="account" :size="8" />
          <div class="flex-1 min-w-0">
            <div class="font-bold text-sm truncate">{{ account.name }}</div>
            <div class="text-xs text-base-content/50 truncate">@{{ account.handle }}</div>
          </div>
          <button
            class="btn btn-sm rounded-full"
            :class="following.includes(account.id) ? 'btn-outline' : 'btn-neutral'"
            @click="$emit('follow', account.id)"
          >
            {{ following.includes(account.id) ? 'Following' : 'Follow' }}
          </button>
        </div>
        <div v-if="!suggestions.length" class="text-sm text-base-content/50">No suggestions</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    query: { type: String, default: '' },
    trends: { type: Array, default: () => [] },
    suggestions: { type: Array, default: () => [] },
    following: { type: Array, default: () => [] }
  },
  emits: ['search', 'follow']
}
</script>
