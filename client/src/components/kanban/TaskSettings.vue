<script setup>
import ProfileSelector from '../profile/ProfileSelector.vue'
</script>

<template>
  <div class="flex flex-col gap-2">
    <h3 class="font-bold text-lg">Task Settings</h3>
    <div class="py-4">
      <label class="block">
        <span>Task Name</span>
        <input type="text" class="input input-bordered w-full" v-model="taskData.name"/>
      </label>
      <label class="block mt-4">
        <span>Associated project</span>
        <select class="input input-bordered w-full" v-model="taskData.project_id">
          <option :value="null">{{ $project.project_name }}</option>
          <option v-for="project in projects" :key="project.project_id" :value="project.project_id">{{ project.project_name }}</option>
        </select>
      </label>
      <label class="block mt-4">
        <span>Board</span>
        <select class="input input-bordered w-full" v-model="taskData.board">
          <option v-for="_, board in boards" :key="board" :value="board">{{ board }}</option>
        </select>
      </label>
      <label class="block mt-4">
        <span>Column</span>
        <select class="input input-bordered w-full" v-model="taskData.column">
          <option v-for="column in columns" :key="column.title" :value="column.title">{{ column.title }}</option>
        </select>
      </label>
      <label class="block mt-4">
        <span>Mode</span>
        <select class="input input-bordered w-full" v-model="taskData.mode">
          <option v-for="mode in ['chat', 'task']" :key="mode" :value="mode">{{ mode }}</option>
        </select>
      </label>
      <label class="block mt-4">
        <span>Profiles</span>
        <button class="btn btn-sm" @click="showProfileSelector = true">
          <i class="fa-solid fa-plus"></i>
        </button>
        <div class="flex gap-2">
          <div class="badge badge-sm badge-primary" v-for="profile in taskData.profiles" :key="profile">{{ profile }}</div>
        </div>
      </label>
      <label class="block mt-4">
        <span>AI Model</span>
        <select class="input input-bordered w-full" v-model="taskData.llm_model">
          <option value="">-- default --</option>
          <option v-for="model in aiModels" :key="model.name" :value="model.name">
            {{ model.name }} <span v-if="model.ai_model"> ({{ model.ai_model }})</span>
          </option>
        </select>
      </label>
    </div>
    <div class="modal-action">
      <button class="btn btn-ghost" @click="$emit('close')">Discard</button>
      <button class="btn btn-primary" :class="!canSaveColumn && 'disabled'" :disabled="!canSaveColumn" @click="saveChanges">Save</button>
    </div>
    <div tabindex="0" class="collapse">
      <input type="checkbox" />
      <div class="collapse-title font-semibold text-error">Delete</div>
      <div class="collapse-content text-sm">
        <button class="mt-2 btn btn-error btn-wide" @click.stop="deleteTask">Confirm delete</button>
      </div>
    </div>
    <modal close="true" @close="showProfileSelector = false" v-if="showProfileSelector">
      <ProfileSelector @select="addProfile($event)" :project="taskProject" />
    </modal>
  </div>
</template>

<script>
export default {
  props: ['taskData'],
  data() {
    return {
      showProfileSelector: false
    }
  },
  computed: {
    taskAIModel() {
      return this.aiModels.find(m => m.name === this.taskData.llm_model)
    },
    aiModels() {
      return this.$projects.ai.models
    },
    boards() {
      return this.$projects.kanban.boards
    },
    columns() {
      return this.$projects.kanban.boards[this.taskData.board]?.columns
    },
    canSaveColumn() {
      return this.taskData.name?.length &&
              this.taskData.board?.length &&
              this.taskData.column?.length
    },
    projects() {
      return this.$projects.allProjects
        .sort((a, b) => a.project_name.toLowerCase() > b.project_name.toLowerCase() ? 1: -1)
    },
    taskProject() {
      if (this.taskData.project_id) {
        return this.projects.find(p => p.project_id === this.taskData.project_id)
      }
      return this.$project
    }
  },
  watch: {
    taskData() {
      if (!this.columns.find(c => c.title === this.taskData.column)) {
        this.taskData.column = ''
      }
    } 
  },
  methods: {
    saveChanges() {
      this.$projects.saveChatInfo(this.taskData)
      this.$emit('close')
    },
    deleteTask() {
      this.$projects.deleteChat(this.taskData)
      this.$emit('close')
    },
    addProfile(profile) {
      if (!this.taskData.profiles.includes(profile.name)) {
        this.taskData.profiles.push(profile.name)
      }
      this.showProfileSelector = false
    }
  }
}
</script>