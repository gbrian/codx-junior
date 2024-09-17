<script setup>
import MarkdownVue from '../components/Markdown.vue'
</script>
<template lang="pug">
<div class="flex flex-col h-full justify-between">
  <div class="text-xl flex gap-2 items-center">
    Profiles
    <input type="text" class="text text-xs text-bordered" v-model="newProfile" v-if="newProfile" />
    <select class="select select-xs select-bordered" v-model="profileName" @change="loadProfile" v-else>
      <option :value="p" v-for="p in profiles" :key="p">{{ p }}</option>
    </select>
    <button class="btn btn-sm" @click="reloadProfile" v-if="profile && !newProfile">
      <i class="fa-solid fa-rotate"></i>
    </button>
    <button class="btn btn-sm" @click="createNewProfile" v-if="!newProfile">
      <i class="fa-solid fa-plus"></i>
    </button>
    <div class="grow"></div>
    <button class="btn btn-sm" @click="editProfile = !editProfile" v-if="profile">
      <i class="fa-solid fa-edit"></i>
    </button>
    <button class="btn btn-sm" @click="saveProfile" v-if="editProfile">
      <i class="fa-solid fa-save"></i>
    </button>
    <button class="btn btn-error btn-sm" @click="deleteProfile" v-if="profile && !newProfile">
      <i class="fa-solid fa-trash"></i>
    </button>
  </div>
  <div class="mt-2 grow relative" v-if="profile">
    <div :class="['absolute top-0 left-0 right-0 bottom-0 border-slate-200 p-2 rounded-md overflow-auto', editProfile && 'bg-neutral text-neutral-content']">
      <pre class="text-wrap min-h-40" contenteditable="true" ref="profileContentEditor" v-if="editProfile">{{ profile.content }}</pre>
      <MarkdownVue :text="profile.content" v-else />
    </div>
  </div>
</div>
</template>
<script>
import { API } from '../api/api'

export default {
  data () {
    return {
      profileName: 'project',
      profile: null,
      profiles: null,
      newProfile: null,
      editProfile: false,
      advanced: false
    }
  },
  async mounted () {
    this.loadProfiles()
    this.loadProfile()
  },
  methods: {
    async loadProfiles () {
      const { data } = await API.profiles.list()
      this.profiles = data
    },
    createNewProfile () {
      this.newProfile = "new_profile"
      this.profile = {
        name: this.newProfile
      }
      this.editProfile = true
    },
    async loadProfile () {
      const { data } = await API.profiles.load(this.profileName)
      this.profile = data
      this.editProfile = false
      this.newProfile = null
    },
    async reloadProfile () {
      const { data } = await API.profiles.load(this.profile.name)
      this.profile = data
    },
    async saveProfile () {
      this.profile.content = this.$refs.profileContentEditor.innerText
      await API.profiles.save(this.profile)
      this.profileName = this.profile.name
      await this.loadProfiles()
      this.loadProfile()
    }
  }
}
</script>