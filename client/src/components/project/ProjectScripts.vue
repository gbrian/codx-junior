<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-2">
    <div class="text-xl">Scripts</div>
    <!-- List of existing scripts -->
    <div v-for="script in scripts" :key="script.name"
      class="flex gap-2 justify-between items-center p-2 rounded-md click"
      @click="editScript(script)"
    >
      <div class="grow flex flex-col gap-1">
        <div>{{ script.name }}</div>
        <div class="text-xs">{{ script.description }}</div>
      </div>
      <span :class="script.background && 'text-error'"><i class="fa-solid fa-circle-play"></i></span>
      <span :class="script.restart && 'text-info'"><i class="fa-solid fa-power-off"></i></span>
      
      <div class="flex gap-2">
        <div class="divider divider-horizontal"></div>
        <button @click="deleteScript(script)" class="btn btn-sm btn-danger">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    </div>
    <div class="flex justify-end">
      <button class="btn btn-sm" @click="addScript">Add script</button>
    </div>
    
    <!-- Modal for adding/editing scripts -->
    <modal v-if="isModalOpen" :close="true" @close="isModalOpen=false">
      <div class="flex flex-col gap-2">
        <div>
          <h2>{{ isEditing ? 'Edit Script' : 'Add New Script' }}</h2>
        </div>
        
        <div class="flex flex-col gap-2">
          <input type="text" v-model="currentScript.name" placeholder="Script Name" class="input input-bordered w-full" />
          <textarea v-model="currentScript.description" placeholder="Description" class="textarea textarea-bordered w-full"></textarea>
          <textarea v-model="currentScript.script" placeholder="Bash Script" class="textarea textarea-bordered w-full"></textarea>
          <div class="flex items-center gap-2">
            <input type="checkbox" v-model="currentScript.background" class="checkbox" />
            <span>Run in background</span>
          </div>
          <div class="flex items-center gap-2">
            <input type="checkbox" v-model="currentScript.restart" class="checkbox" />
            <span>Restart if stopped</span>
          </div>
        </div>
        <button class="btn btn-sm" @click="isModalOpen = false">
          Close
        </button>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      isModalOpen: false,
      isEditing: false,
      currentScript: this.defaultScript()
    }
  },
  computed: {
    scripts() {
      return this.settings.project_scripts
    }
  },
  methods: {
    defaultScript() {
      return {
        name: '',
        description: '',
        script: '',
        background: false,
        restart: false,
      }
    },
    addScript() {
      this.settings.project_scripts = [...this.settings.project_scripts || [], {}]
    },
    editScript(script) {
      this.isEditing = true
      this.currentScript = script
      this.isModalOpen = true
    },
    deleteScript(script) {
      this.settings.project_scripts = this.settings.project_scripts.filter(s => s !== script)
    }
  }
}
</script>