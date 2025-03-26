<script setup>
</script>

<template>
  <div class="card w-full p-4 border border-gray-200 rounded-lg shadow-md">
    <img class="w-16 h-16 rounded-full mx-auto" :src="useAvatar" alt="Workmate Icon" />
    <div class="mt-4 text-center">
      <h2 class="text-lg font-semibold text-gray-700">{{ profile.name }}</h2>
      <p class="badge badge-xs badge-success badge-outline">{{ profile.category }} {{ profile.file_match  }}</p>
      <p class="text-gray-500 h-20 overflow-auto text-xs">{{ profile.description }}</p>
      <div class="flex justify-center mt-2 space-x-2">
        <span v-for="badge in badges" :key="badge" class="badge badge-secondary">{{ badge }}</span>
      </div>
      <div class="flex justify-between items-end">
        <div>
          <div class="font-bold text-xs">Skills</div>
          <div class="flex gap-2">
            <div>
            <i class="fa-solid fa-book" :class="profile.use_knowledge ? 'text-info' : 'text-error'" ></i>
          </div>
          <div class="tooltip" data-tip="Expose profile in the API">
            <i class="fa-solid fa-share-nodes" :class="profile.api_settings.active ? 'text-warning' : 'text-slate-500'" ></i>
          </div>
          </div>
        </div>
        <p class="text-xs text-warning"
          v-if="profile.llm_model"
        ><i class="fa-solid fa-brain"></i> {{ profile.llm_model }}</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['profile'],
  data() {
    return {}
  },
  computed: {
    useAvatar() {
      return this.profile.avatar ||
        `https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r=${this.profile.name}`
    }
  },
  watch: {},
  methods: {}
}
</script>