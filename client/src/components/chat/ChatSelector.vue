<script setup>
</script>

<template>
  <div class="w-full h-full flex gap-2">
    <input type="text" v-model="freeTextSearch" placeholder="Search chats" class="input input-bordered w-full" />
    <select v-model="selectedProject" class="select select-bordered w-full">
      <option v-for="project in projects" :key="project.id" :value="project">
        {{ project.name }}
      </option>
    </select>
    <table class="table w-full">
      <thead>
        <tr>
          <th>Project</th>
          <th>Kanban</th>
          <th>Column</th>
          <th>Name</th>
          <th>Tags</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="chatResult in chatResults" :key="chatResult.chat.name">
          <td>{{ chatResult.project.project_name }}</td>
          <td>{{ chatResult.chat.board }}</td>
          <td>{{ chatResult.chat.column }}</td>
          <td>{{ chatResult.chat.name }}</td>
          <td> <!-- Tags column will go here, if available --></td>
        </tr>
      </tbody>
    </table>
    <div v-for="chat in chats" :key="chat.id" @select="selectChat(chat)">
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedProjectContext: null,
      freeTextSearch: '',
      selectedProject: null
    }
  },
  computed: {
    projects() {
      return this.$storex.projects.allProjects
    },
    chats() {
      return this.selectedProject?.allChats
    },
    chatResults() {
      return [{
        project: { project_name: 'Project A' },
        chat: { name: 'Chat', board: 'Kanban A', column: 'To Do' }
      }]
    }
  },
  methods: {
    async selectProject(project) {
      this.selectedProjectContext = await this.$service.loadProjectContext(project)
    },
    selectChat(chat) {
      this.$emit('select', chat)
    }
  }
}
</script>