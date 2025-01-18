<script setup>
import moment from 'moment'
import Markdown from '../components/Markdown.vue'
</script>

<template>
  <div class="profile-container flex flex-col items-center h-full">
    <div class="projects-list mt-2 w-full flex flex-col gap-2 md:p-4">
      <div class="md:border md:border-stone-600 rounded w-full">
        <h2 class="px-2 pt-2 text-xl font-bold mb-4 border-b border-stone-600">
          <span class="ml-2 -mb-2 border-b-2 border-secondary">Recent activity</span>
        </h2>
        <div class="p-2">
          <div class="w-full" v-if="lastModifiedProjects.length">
            <div class="flex flex-col gap-1 text-xs">
              <div class="min-h-40 overflow-auto bg-base-200 rounded">
                <table class="table">
                  <thead class="">
                    <th>Board</th>
                    <th>Column</th>
                    <th>Task</th>
                    <th class="hidden md:block">Type</th>
                    <th>Last update</th>
                  </thead>
                  <tbody class="">
                    <tr class="click" @click="loadTask(task)" 
                      v-for="task in lastModifiedProjects" :key="task.id">
                      <td><div class="font-bold">{{ task.board }}</div></td>
                      <td><div class="badge badge-ouline">{{ task.column }}</div></td>
                      <td>{{  task.name  }}</td>
                      <td class="hidden md:block">{{ task.mode }}</td>
                      <td>{{ task.fromNow }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="alert click flex gap-2" @click="$ui.setActiveTab('tasks')" v-else>
            <i class="fa-solid fa-list-check"></i>
            No recent activity! Go and create your first task
          </div>
        </div>
        <h2 class="px-2 pt-2 text-xl font-bold mb-4 border-b border-stone-600">
          <span class="ml-2 -mb-2 border-b-2 border-warning">README.md</span>
        </h2>
        <Markdown class="m-auto p-2" :text="readme" />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      newProjectPath: null,
      readme: ""
    };
  },
  created() {
    this.loadReadme()
  },
  computed: {
    projectName() {
      return this.$project.project_name;
    },
    projectIcon() {
      return this.$project.project_icon;
    },
    projectDescription() {
      return this.$project.project_description;
    },
    lastModifiedProjects () {
      return this.$storex.projects.chats?.map(c => ({ ...c, fromNow: moment(c.updated_at).fromNow() }))
              .sort((a, b) => a.updated_at > b.updated_at ? -1 : 1)
              .slice(0, 5) || []
    }
  },
  methods: {
    async setProject(project) {
      this.$projects.setActiveProject(project)
    },
    lastRefresh(last_update) {
      if (last_update) {
        const ts = parseInt(last_update, 10) * 1000
        return moment(new Date(ts)).fromNow()
      }
      return null
    },
    async loadTask(task) {
      this.$ui.loadTask(task)
    },
    async loadReadme() {
      this.readme = await this.$storex.api.project.readme()
    }
  }
}
</script>