<script setup>
</script>
<template>
  <div class="w-full h-full flex flex-col gap-2 h-96">
    <input type="text" placeholder="Filter profiles..." class="input input-xs input-bordered" v-model="filterText" />
    <div class="h-60 overflow-auto">
      <ul class="menu">
        <li class="mb-2" v-for="profile in filteredProfiles" :key="profile.id" @click="$emit('select', profile)">
          <a class="flex flex-col gap-2 p-2 border items-start">
            <div class="flex gap-2 items-center">
              <div class="avatar">
                <div class="w-8 rounded">
                  <img
                    :src="profile.avatar"
                    :alt="profile.name" />
                </div>
              </div>
              <div class="text-xl">{{ profile.name }}</div>
            </div>
            <div class="h-20 overflow-hidden">{{ profile.description }}</div>
          </a>    
        </li>
      </ul>
    </div>
  </div>
</template>
<script>
export default {
  data() {
    return {
      filterText: ''
    }
  },
  computed: {
    profiles() {
      return this.$projects.profiles
    },
    filteredProfiles() {
      const filterText = this.filterText.toLowerCase()
      return this.profiles.filter(profile => profile.name.toLowerCase().includes(filterText))
    }
  }
}
</script>