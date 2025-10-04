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

      <div>Github name</div>
      <input type="text" placeholder="Name like 'gbrian'" class="input input-bordered input-sm" v-model="user.github" />

      <div>API Key</div>
      <input type="text" placeholder="API Key" class="input input-bordered input-sm" v-model="user.api_key" />

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

          <input type="checkbox" checked="checked" class="checkbox tooltip"
            data-tip="Same for children"
            v-model="project.children" />

          <button type="button" class="btn btn-error btn-sm" @click="removeProject(index)">
            <i class="fa-solid fa-minus"></i>
          </button>
        </div>
      </div>

      <div>
        Apps
        <select class="select select-bordered select-sm" v-model="newApp">
          <option value="autogenstudio">autogenstudio</option>
          <option value="coder">coder</option>
          <option value="viewer">viewer</option>
          <option value="tasks">tasks</option>
          <option value="files">files</option>
        </select>
        <button type="button" class="btn btn-sm btn-secondary" @click="addApp">Add App</button>
        <div class="flex gap-2 mt-2">
          <span v-for="(app, index) in user.apps" :key="index" class="badge">
            {{ app }}
            <button type="button" class="btn btn-xs btn-error ml-2" @click="removeApp(index)">
              <i class="fa-solid fa-times"></i>
            </button>
          </span>
        </div>
      </div>

      <div class="form-control w-52">
        <label class="label cursor-pointer">
          <span class="label-text">Disabled</span>
          <input type="checkbox" v-model="user.disabled" class="toggle" :class="user.disabled ? 'toggle-error' : ''" checked="checked" />
        </label>
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
    return {
      newApp: ''
    }
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
    },
    addApp() {
      if (!this.user.apps) {
        this.user.apps = []
      }
      if (this.newApp && !this.user.apps.includes(this.newApp)) {
        this.user.apps.push(this.newApp)
        this.newApp = ''
      }
    },
    removeApp(index) {
      this.user.apps.splice(index, 1)
    }
  }
}
</script>