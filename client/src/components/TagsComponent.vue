<script setup>
</script>
<template>
  <div class="w-full h-full flex flex-col gap-2 p-4">
    <div v-for="tag in tags" :key="tag" class="badge badge-primary">
      {{ tag }}
      <button class="btn btn-xs btn-error" @click="removeTag(tag)">Remove</button>
    </div>
    <select class="select select-bordered w-full max-w-xs" v-model="selectedTag" @change="addTag">
      <option disabled value="">Select a tag</option>
      <option v-for="option in tagOptions" :key="option" :value="option">
        {{ option }}
      </option>
    </select>
    <button class="btn btn-primary mt-2" @click="showModal = true">Add New Tag</button>
    
    <div v-if="showModal" class="modal modal-open">
      <div class="modal-box">
        <input class="input input-bordered w-full mb-2" v-model="newTag" placeholder="Enter new tag" />
        <button class="btn btn-primary mr-2" @click="createNewTag">Create</button>
        <button class="btn" @click="showModal = false">Cancel</button>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    tags: {
      type: Array,
      required: true
    },
    tagOptions: {
      type: Array,
      required: true
    }
  },
  data () {
    return {
      selectedTag: '',
      showModal: false,
      newTag: ''
    }
  },
  methods: {
    removeTag(tag) {
      this.$emit('remove', tag)
    },
    addTag() {
      if (this.selectedTag) {
        this.$emit('add', this.selectedTag)
        this.selectedTag = ''
      }
    },
    createNewTag() {
      if (this.newTag) {
        this.$emit('new', this.newTag)
        this.newTag = ''
        this.showModal = false
      }
    }
  }
}
</script>