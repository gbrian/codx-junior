<script setup>
import ChatIcon from './chat/ChatIcon.vue';
</script>

<template>
  <div class="card w-full p-4 border border-gray-200 rounded-lg shadow-md text-center">
    <div class="flex justify-center">
      <div class="avatar indicator">
        <span class="indicator-item badge">
          <ChatIcon :mode="profile.chat_mode || 'chat'" />
        </span>
        <div class="h-20 w-20 rounded-lg">
          <img :src="useAvatar" :alt="profile.name" />
        </div>
      </div>
    </div>
    <div class="flex flex-col gap-1 items-center mt-4 tooltip" :data-tip="profile.name">
      <h2 class="text-lg font-semibold overflow-hidden text-ellipsis">
        {{ profile.name }}
      </h2>
      <p class="badge badge-xs badge-success badge-outline">{{ profile.category }} {{ profile.file_match  }}</p>
      <div class="flex gap-1 justify-center">
        <div v-for="profile in profile.profiles" :key="profile.id" class="badge-xs badge badge-secondary">
          {{ profile }}
        </div>
      </div>
      <p class="text-gray-500 h-20 overflow-hidden text-xs text-ellipsis">{{ profile.description }}</p>
      <div class="flex justify-center mt-2 space-x-2">
        <span v-for="badge in badges" :key="badge" class="badge badge-secondary">{{ badge }}</span>
      </div>
      <div class="flex">
        <div>
          <div class="font-bold text-xs">Skills</div>
          <div class="flex gap-2">
            <div>
              <i class="fa-solid fa-book" :class="profile.use_knowledge ? 'text-info' : 'text-slate-400'" ></i>
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