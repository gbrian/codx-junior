<template>
  <div class="edit-profile px-4 max-w-2xl mx-auto flex flex-col gap-2">
    <label class="text-xl">Profile</label>
    <div class="flex justify-between items-center gap-4">
      <input id="name" v-model="editProfile.name" type="text"
        :class="nameTaken && 'text-error'"
        class="bg-base-300 input input-sm input-bordered w-full" />
      <div class="flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="onSubmit" :disabled="!canSave">Save</button>
        <button type="button" @click="cancelEdit" class="btn btn-sm">Cancel</button>
        <button type="button" @click="deleteProfile" class="btn btn-sm btn-error" v-if="isOverriden">Delete</button>
      </div>
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
      <label for="content">Content</label>
      <textarea id="content" v-model="editProfile.content" class="textarea textarea-bordered w-full h-96 bg-base-300 overflow-auto"></textarea>
    </div>
    <modal v-if="confirmDelete">
      <div class="text-2xl">Confirm delete?</div>
      <div class="flex gap-2">
        <button type="button" @click="confirmDelete = false" class="btn btn-sm">Cancel</button>
        <button type="button" @click="onDeleteProfile" class="btn btn-sm btn-error">Delete</button>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['profile', 'allProfiles'],
  data() {
    return {
      editProfile: { ...this.profile },
      confirmDelete: false
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
    }
  }
}
</script>