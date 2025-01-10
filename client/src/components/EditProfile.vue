<script setup>
import Markdown from './Markdown.vue';
</script>
<template>
  <div class="edit-profile px-4 max-w-2xl mx-auto flex flex-col gap-2">
    <label class="text-xl flex items-center gap-2 font-bold">
      <button type="button" @click="cancelEdit" class="btn btn-sm">
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      Profile
      <div class="grow"></div>
      <button type="button" @click="onDeleteProfile" class="btn btn-sm btn-error" :disabled="loading">Delete</button>
    </label>
    <div class="flex justify-between items-center gap-4">
      <input id="name" v-model="editProfile.name" type="text"
        :class="nameTaken && 'text-error'"
        class="bg-base-300 input input-sm input-bordered w-full" />
    </div>
    <div class="form-group flex space-x-4 text-xs">
      <div class="w-1/2 flex flex-col gap-2">
        <label for="category">Category</label>
        <select id="category" v-model="editProfile.category" :disabled="profile.category"
          class="bg-base-300 input input-xs input-bordered w-full">
          <option value="project">Project</option>
          <option value="assistant">Assistant</option>
          <option value="file">File</option>
        </select>
      </div>
      <div class="w-1/2 flex flex-col gap-2">
        <label for="fileMatch">File Match</label>
        <input id="fileMatch" v-model="editProfile.file_match" type="text" class="bg-base-300 input input-xs input-bordered w-full" />
      </div>
    </div>
    <div class="form-group">
      <label for="description">Description</label>
      <textarea id="description" v-model="editProfile.description" class="bg-base-300 textarea textarea-bordered w-full"></textarea>
    </div>
    <div class="flex flex-col gap-2">
      <label for="content flex gap-2">Content
        <button class="btn btn-xs" @click="toggleContentPreview">
          <i :class="contentPreview ? 'fa-solid fa-pencil-alt' : 'fa-solid fa-eye'"></i>
        </button>
      </label>
      <Markdown class="p-2 rounded-md"
        :class="contentPreview ? 'bg-base-100 border border-slate-700' : 'bg-base-300'"
        :text="editProfile.content" v-if="contentPreview" />
      <textarea id="content" v-model="editProfile.content" class="textarea textarea-bordered w-full h-96 bg-base-300 overflow-auto" v-else></textarea>
    </div>
    <div class="flex gap-2 justify-end">
      <button type="button" class="btn btn-sm btn-primary" :class="loading && 'loading loading-spinner'" @click="onSubmit" :disabled="!canSave">Update</button>
    </div>

    <modal v-if="confirmDelete">
      <div class="text-2xl">Confirm delete?</div>
      <div class="flex gap-2">
        <button type="button" @click="confirmDelete = false" class="btn btn-sm">Cancel</button>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['profile', 'allProfiles', 'loading'],
  data() {
    return {
      editProfile: { ...this.profile },
      confirmDelete: false,
      contentPreview: true
    }
  },
  computed: {
    isOverriden () {
      return this.profile.path?.startsWith(this.$project.project_path)
    },
    nameTaken () {
      const { name } = this.editProfile
      const { name: orgName } = this.profile
      return name != orgName && this.allProfiles.find(p => p.name.toLowerCase() === name?.toLowerCase())
    },
    canSave () {
      const { name, category } = this.editProfile
      return name && category && !this.nameTaken
    }
  },
  watch: {
    profile() {
      this.editProfile = {...this.profile}
    }
  },
  methods: {
    onSubmit() {
      this.$emit('save', this.editProfile)
    },
    cancelEdit() {
      this.$emit('cancel')
    },
    deleteProfile() {
      this.confirmDelete = true
    },
    onDeleteProfile() {
      this.confirmDelete = false
      this.$emit('delete')
    },
    toggleContentPreview() {
      this.contentPreview = !this.contentPreview;
    }
  }
}
</script>