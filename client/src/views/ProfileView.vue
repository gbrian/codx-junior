<script setup>
import Markdown from '@/components/Markdown.vue'
</script>
<template>
<div class="flex flex-col gap-2 h-full justify-between p-4">
  <div class="text-xl flex gap-2 items-center">
    Profiles
    <input type="text" class="text text-xs text-bordered" v-model="newProfile" v-if="newProfile" />
    <select class="select select-xs select-bordered" v-model="profileName" @change="loadProfile" v-else>
      <option :value="p" v-for="p in profiles" :key="p">{{ p }}</option>
    </select>
    <button class="btn btn-sm" @click="createNewProfile" v-if="!newProfile">
      <i class="fa-solid fa-plus"></i>
    </button>
    <div class="grow"></div>
    <button class="btn btn-sm" @click="editProfile = !editProfile" v-if="profile && !editProfile">
      <i class="fa-solid fa-edit"></i>
    </button>
    <button class="btn btn-error btn-sm" @click="deleteProfile" v-if="profile && !newProfile">
      <i class="fa-solid fa-trash"></i>
      <span v-if="isDeleteProfile">
        Sure? <span class="hover:underline">YES</span> / 
        <span class="hover:underline" @click.stop="isDeleteProfile = false">CANCEL</span>
      </span>
    </button>
  </div>
  <div class="mt-2 grow relative" v-if="profile">
    <div :class="['absolute top-0 left-0 right-0 bottom-0 border-slate-200 p-2 rounded-md overflow-auto', editProfile && 'bg-neutral text-neutral-content']">
      <Markdown :text="profile.content" />
    </div>
  </div>
  <div v-if="editProfile" class="flex flex-col gap-2 items-cinput input-bordered w-full">
    <label class="form-control w-full">
      <div class="label">
        <span class="label-text">Add your comments to update the profile</span>
      </div>
      <textarea class="textarea textarea-bordered h-24 w-full"
        v-model="changeInput"
        placeholder="Change ..."></textarea>
    </label>
    <div class="flex justify-end gap-2">
      <button class="btn btn-sm" @click="reloadProfile" v-if="profile && !newProfile">
        <i class="fa-solid fa-rotate"></i> Cancel
      </button>  
      <button class="btn btn-primary btn-sm" @click="sendChat">
        <i class="fa-solid fa-edit"></i> Update
      </button>
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
      advanced: false,
      changeInput: '',
      isDeleteProfile: false
    }
  },
  async mounted () {
    this.init()
  },
  methods: {
    async init() {
      await this.loadProfiles()
      this.loadProfile()
      this.editProfile = false
      this.isDeleteProfile = false
    },
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
      this.editProfile = false
    },
    async saveProfile () {
      this.profile.content = this.$refs.profileContentEditor.innerText
      await API.profiles.save(this.profile)
      this.profileName = this.profile.name
      await this.loadProfiles()
      this.loadProfile()
    },
    async deleteProfile () {
      if (this.isDeleteProfile) {
        await API.profiles.delete(this.profileName)
        this.init()
      } else  {
        this.isDeleteProfile = true
      }
    },
    async sendChat() {
      if (this.changeInput?.trim()) {
        this.profile.user_comment = this.changeInput
        const { data:profile }= await API.profiles.save(this.profile)
        this.profile = profile
        this.changeInput = '';
      }
    }
  }
}
</script>