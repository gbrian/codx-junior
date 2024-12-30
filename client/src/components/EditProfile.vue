<template>
  <div class="edit-profile px-4 max-w-2xl mx-auto flex flex-col gap-2">
    <label class="text-xl">Profile</label>
    <div class="flex justify-between items-center gap-4">
      <input id="name" v-model="editProfile.name" type="text" class="bg-base-300 input input-sm input-bordered w-full" />
      <div class="flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="onSubmit">Save</button>
        <button type="button" @click="cancelEdit" class="btn btn-sm">Cancel</button>
      </div>
    </div>
    <div class="form-group flex space-x-4 text-xs">
      <div class="w-1/2 flex flex-col gap-2">
        <label for="category">Category</label>
        <input id="category" v-model="editProfile.category" type="text" class="bg-base-300 input input-xs input-bordered w-full" />
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
  </div>
</template>

<script>
export default {
  props: {
    profile: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      editProfile: { ...this.profile }
    }
  },
  methods: {
    onSubmit() {
      this.$emit('save', this.editProfile)
    },
    cancelEdit() {
      this.$emit('cancel')
    }
  }
}
</script>
