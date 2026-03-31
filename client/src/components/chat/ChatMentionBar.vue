<script setup>
</script>

<template>
  <div class="flex flex-col gap-1">
    <!-- Mention autocomplete suggestions -->
    <div class="flex gap-2" v-if="suggestions.length">
      <div
        class="badge badge-info badge-outline click"
        v-for="mention in suggestions"
        :key="mention.searchIndex"
        @click="$emit('add-mention', mention)"
      >
        @{{ mention.name }}
      </div>
    </div>

    <!-- Active mentions in message -->
    <div class="flex gap-2 flex-wrap" v-if="activeMentions.length">
      <span
        class="badge tooltip flex gap-2 items-center"
        :data-tip="mention.tooltip"
        :class="{
          'badge-primary': mention.project,
          'badge-success badge-outline': mention.profile
        }"
        v-for="mention in activeMentions"
        :key="mention.name"
        :title="mention.file || mention.name"
      >
        <i class="fa-solid fa-magnifying-glass" v-if="mention.project"></i>
        <img class="w-4 rounded-full" :src="mention.profile.avatar" v-if="mention.profile?.avatar" />
        <i class="fa-solid fa-user" v-if="mention.profile && !mention.profile.avatar"></i>
        <i class="fa-solid fa-file-lines" v-if="mention.file"></i>
        <i class="fa-solid fa-file-arrow-up" @click="$emit('add-file', mention.file)" v-if="mention.file"></i>
        <div class="-mt-1">{{ mention.name }}</div>
        <span class="click" @click="$emit('remove-mention', mention)">X</span>
      </span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    suggestions: { type: Array, default: () => [] },
    activeMentions: { type: Array, default: () => [] }
  },
  emits: ['add-mention', 'remove-mention', 'add-file']
}
</script>