<script setup>
import ProjectSelectorContent from './ProjectSelectorContent.vue'
</script>

<template>
  <!-- Trigger Button (only when not in modal mode) -->
  <div v-if="!modal">
    <button
      class="flex gap-1 items-center group btn btn-ghost btn-sm tooltip"
      :data-tip="currentProject?.project_path"
      @click="isModalOpen = true"
      :disabled="disabled"
    >
      <div class="avatar" v-if="options?.showIcon !== false">
        <div class="rounded-full" :class="['w-' + iconSize]">
          <img :src="currentProject?.project_icon" alt="project" />
        </div>
      </div>
      <span v-if="!iconify" class="truncate">{{ currentProject?.project_name }}</span>
    </button>
  </div>

  <!-- Modal (separate root to not take space when modal=true) -->
  <div v-if="isModalOpen || modal" class="modal modal-open z-50">
    <div class="modal-box flex flex-col h-screen max-h-screen md:max-h-[80vh]">
      <!-- Header -->
      <div class="flex justify-between items-center mb-4 flex-shrink-0">
        <h2 class="text-2xl font-bold flex items-center gap-2">
          <i class="fa-solid fa-folder-open text-primary"></i>
          <span class="truncate">Select Project</span>
        </h2>
        <button
          @click="closeModal"
          class="btn btn-ghost btn-sm btn-circle flex-shrink-0"
        >
          <i class="fa-solid fa-xmark text-xl"></i>
        </button>
      </div>

      <!-- Content (scrollable) -->
      <div class="flex-1 overflow-hidden">
        <ProjectSelectorContent
          :current-project="currentProject"
          :show-new-project="showNewProject"
          @close-new-project="showNewProject = false"
          @select-project="onProjectSelected"
          @open-new-project="showNewProject = true"
        />
      </div>
    </div>

    <!-- Modal Backdrop -->
    <div class="modal-backdrop" @click="closeModal"></div>
  </div>
</template>

<script>
export default {
  props: {
    iconify: Boolean,
    options: Object,
    disabled: Boolean,
    modal: {
      type: Boolean,
      default: false
    },
    iconSize: {
      type: Number,
      default: () => 6
    },
    modelValue: {
      type: Object,
      default: () => null
    }
  },
  data() {
    return {
      isModalOpen: false,
      showNewProject: false
    }
  },
  computed: {
    currentProject() {
      return this.modelValue || this.$project
    }
  },
  watch: {
    modal(newVal) {
      if (!newVal) {
        this.closeModal()
      }
    }
  },
  methods: {
    closeModal() {
      this.isModalOpen = false
      this.showNewProject = false
      this.$emit('close')
    },
    onProjectSelected(project) {
      this.$emit('update:modelValue', project)
      this.$emit('select', project)
      if (!this.modal) {
        this.closeModal()
      }
    }
  }
}
</script>