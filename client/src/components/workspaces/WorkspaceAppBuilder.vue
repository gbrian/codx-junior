<script setup>
import AppIcon from '../apps/AppIcon.vue'
</script>

<template>
  <div class="space-y-3">
    <div v-if="!apps.length" class="alert alert-info">
      <i class="fa-solid fa-lightbulb"></i>
      <span>Add apps to make them accessible in this workspace</span>
    </div>

    <div v-for="(app, idx) in apps" :key="idx" class="card bg-base-100 border border-base-200">
      <div class="card-body p-4 space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="font-semibold text-sm">App {{ idx + 1 }}</h4>
          <button class="btn btn-ghost btn-xs text-error" @click="removeApp(idx)">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="form-control">
            <label class="label label-text-alt">Name</label>
            <input
              v-model="app.name"
              type="text"
              placeholder="App Name"
              class="input input-bordered input-sm"
            />
          </div>
          <div class="form-control">
            <label class="label label-text-alt">Icon</label>
            <input
              v-model="app.icon"
              type="text"
              placeholder="fa-globe"
              class="input input-bordered input-sm"
            />
          </div>
          <div class="form-control">
            <label class="label label-text-alt">Path</label>
            <input
              v-model="app.path"
              type="text"
              placeholder="/app"
              class="input input-bordered input-sm"
            />
          </div>
          <div class="form-control">
            <label class="label label-text-alt">Port</label>
            <input
              v-model.number="app.port"
              type="number"
              placeholder="3000"
              class="input input-bordered input-sm"
            />
          </div>
        </div>

        <div class="form-control">
          <label class="label label-text-alt">Description</label>
          <input
            v-model="app.description"
            type="text"
            placeholder="What does this app do?"
            class="input input-bordered input-sm"
          />
        </div>

        <div class="flex items-center gap-3">
          <label class="label cursor-pointer flex-1">
            <span class="label-text-alt">VNC App</span>
            <input v-model="app.is_vnc" type="checkbox" class="checkbox checkbox-sm" />
          </label>
          <label class="label cursor-pointer flex-1">
            <span class="label-text-alt">HTTPS</span>
            <input
              v-model="app.scheme"
              type="checkbox"
              class="checkbox checkbox-sm"
              @change="app.scheme = app.scheme ? 'https' : 'http'"
            />
          </label>
        </div>

        <div class="form-control">
          <label class="label label-text-alt">Access Roles</label>
          <div class="flex gap-2">
            <label class="label cursor-pointer flex-1">
              <span class="label-text-alt">User</span>
              <input
                :checked="app.roles?.includes('user')"
                type="checkbox"
                class="checkbox checkbox-sm"
                @change="toggleRole(app, 'user')"
              />
            </label>
            <label class="label cursor-pointer flex-1">
              <span class="label-text-alt">Admin</span>
              <input
                :checked="app.roles?.includes('admin')"
                type="checkbox"
                class="checkbox checkbox-sm"
                @change="toggleRole(app, 'admin')"
              />
            </label>
          </div>
        </div>
      </div>
    </div>

    <button class="btn btn-outline btn-sm w-full" @click="addApp">
      <i class="fa-solid fa-plus"></i> Add App
    </button>
  </div>
</template>

<script>
export default {
  props: ['apps'],
  emits: ['update'],
  methods: {
    addApp() {
      const newApps = [...this.apps, {
        name: '',
        icon: 'fa-globe',
        description: '',
        path: '',
        port: null,
        roles: ['admin'],
        is_vnc: false,
        scheme: 'http'
      }]
      this.$emit('update', newApps)
    },
    removeApp(idx) {
      const newApps = this.apps.filter((_, i) => i !== idx)
      this.$emit('update', newApps)
    },
    toggleRole(app, role) {
      if (!app.roles) app.roles = []
      const idx = app.roles.indexOf(role)
      if (idx > -1) {
        app.roles.splice(idx, 1)
      } else {
        app.roles.push(role)
      }
    }
  }
}
</script>