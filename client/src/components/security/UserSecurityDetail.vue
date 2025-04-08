<script setup>
</script>

<template>
  <div class="w-full h-full flex gap-2">
    <div class="flex flex-col gap-4">
      <div class="flex justify-between">
        <div class="flex flex-col">
          <div>Username</div>
          <div>
            <input type="text" placeholder="Username" class="input input-bordered input-sm" v-model="user.username" />
          </div>
        </div>
        <div class="flex flex-col">
          <div>Role</div>
          <select class="select select-bordered select-sm" v-model="user.role">
            <option value="admin">admin</option>
            <option value="user">user</option>
          </select>

        </div>
      </div>
      <div>Email</div>
      <input type="email" placeholder="Email" class="input input-bordered input-sm" v-model="user.email" />

      <div>Password</div>
      <input type="password" placeholder="Password" class="input input-bordered input-sm" v-model="user.password" />

      <div>Avatar URL</div>
      <input type="text" placeholder="Avatar URL" class="input input-bordered input-sm" v-model="user.avatar" />

      <div class="flex flex-col gap-2">
        <div>
          Projects
          <button type="button" class="btn btn-sm btn-secondary" @click="addProject">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
        <div v-for="(project, index) in user.projects" :key="index" class="flex items-center gap-2">
          <select class="select select-bordered select-sm" v-model="project.project_id">
            <option v-for="proj in allProjects" :key="proj.project_id" :value="proj.project_id">
              {{ proj.project_name }}
            </option>
          </select>
          <select class="select select-bordered select-sm" v-model="project.permissions">
            <option value="admin">admin</option>
            <option value="user">user</option>
          </select>
          <button type="button" class="btn btn-error btn-sm" @click="removeProject(index)">
            <i class="fa-solid fa-minus"></i>
          </button>
        </div>
      </div>
      <button class="btn btn-primary" @click="$emit('save', user)">
        Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['user'],
  data() {
    return {}
  },
  computed: {
    allProjects () {
      return this.$projects.allProjects
    }
  },
  methods: {
    addProject() {
      if (!this.user.projects) {
        this.user.projects = []
      }
      this.user.projects.push({ project_id: '', permissions: 'user' })
    },
    removeProject(index) {
      this.user.projects.splice(index, 1)
    }
  }
}
</script>