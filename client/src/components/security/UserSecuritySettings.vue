<script setup>
import UserWalletSettings from './UserWalletSettings.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4">
    <!-- Header banner -->
    <div class="flex items-center gap-3 bg-gradient-to-r from-secondary/20 to-transparent rounded-xl px-4 py-3">
      <div class="avatar placeholder">
        <div class="bg-secondary text-secondary-content rounded-full w-10 h-10 flex items-center justify-center">
          <i class="fa-solid fa-user-shield text-lg"></i>
        </div>
      </div>
      <div>
        <div class="font-bold text-base">{{ user.username || 'User Settings' }}</div>
        <div class="text-xs text-base-content/50">{{ user.email || 'no email set' }}</div>
      </div>
      <div class="ml-auto flex gap-2">
        <span class="badge badge-xs" :class="user.role === 'admin' ? 'badge-error' : 'badge-info'">
          <i :class="user.role === 'admin' ? 'fa-solid fa-crown' : 'fa-solid fa-user'" class="mr-1"></i>
          {{ user.role || 'user' }}
        </span>
        <span v-if="user.disabled" class="badge badge-error badge-xs">
          <i class="fa-solid fa-ban mr-1"></i> Disabled
        </span>
      </div>
    </div>

    <!-- Tabs -->
    <div role="tablist" class="tabs tabs-border">
      <a role="tab" class="tab" :class="activeTab === 'general' && 'tab-active'" @click="activeTab = 'general'">
        <i class="fa-solid fa-sliders mr-1"></i> General
      </a>
      <a role="tab" class="tab" :class="activeTab === 'projects' && 'tab-active'" @click="activeTab = 'projects'">
        <i class="fa-solid fa-diagram-project mr-1"></i> Projects & Apps
      </a>
      <a role="tab" class="tab" :class="activeTab === 'wallet' && 'tab-active'" @click="activeTab = 'wallet'">
        <i class="fa-solid fa-wallet mr-1"></i> Wallet
      </a>
    </div>

    <!-- General Tab -->
    <div v-if="activeTab === 'general'" class="w-full grow flex gap-4">
      <!-- Left column -->
      <div class="flex flex-col gap-3 w-1/2">
        <!-- Identity -->
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
          <div class="text-xs font-bold uppercase tracking-widest text-primary flex items-center gap-1">
            <i class="fa-solid fa-id-card"></i> Identity
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">Username</span>
              </label>
              <input type="text" placeholder="Username" class="input input-bordered input-sm" v-model="user.username" />
            </div>
            <div class="form-control">
              <label class="label py-1">
                <span class="label-text text-xs">Role</span>
              </label>
              <select class="select select-bordered select-sm" v-model="user.role">
                <option value="admin">admin</option>
                <option value="user">user</option>
              </select>
            </div>
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">Email</span>
            </label>
            <input type="email" placeholder="Email" class="input input-bordered input-sm" v-model="user.email" />
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">Avatar URL</span>
            </label>
            <input type="text" placeholder="https://..." class="input input-bordered input-sm font-mono text-xs" v-model="user.avatar" />
          </div>
        </div>

        <!-- Access -->
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
          <div class="text-xs font-bold uppercase tracking-widest text-warning flex items-center gap-1">
            <i class="fa-solid fa-lock"></i> Access
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs">Password</span>
            </label>
            <input type="password" placeholder="Password" class="input input-bordered input-sm" v-model="user.password" />
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs"><i class="fa-solid fa-key mr-1 text-info"></i>API Key</span>
            </label>
            <input type="text" placeholder="API Key" class="input input-bordered input-sm font-mono text-xs" v-model="user.api_key" />
          </div>
          <div class="form-control">
            <label class="label py-1 cursor-pointer justify-start gap-3">
              <input type="checkbox" v-model="user.disabled" class="toggle toggle-sm" :class="user.disabled ? 'toggle-error' : 'toggle-success'" />
              <span class="label-text text-xs">Account Disabled</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Right column -->
      <div class="flex flex-col gap-3 w-1/2">
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg h-full">
          <div class="text-xs font-bold uppercase tracking-widest text-accent flex items-center gap-1">
            <i class="fa-solid fa-circle-nodes"></i> Integrations
          </div>
          <div class="form-control">
            <label class="label py-1">
              <span class="label-text text-xs"><i class="fa-brands fa-github mr-1"></i>Github Name</span>
            </label>
            <input type="text" placeholder="e.g. gbrian" class="input input-bordered input-sm font-mono text-xs" v-model="user.github" />
          </div>
          <div class="text-xs text-base-content/50 p-2 bg-base-300 rounded-lg mt-auto">
            <div class="font-semibold mb-1">User info:</div>
            <ul class="list-disc list-inside pl-2 space-y-1">
              <li><strong class="text-primary">admin</strong> — Full access to all resources.</li>
              <li><strong class="text-secondary">user</strong> — Limited to assigned projects.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- Projects & Apps Tab -->
    <div v-if="activeTab === 'projects'" class="w-full grow flex gap-4">
      <!-- Left column: Projects -->
      <div class="flex flex-col gap-3 w-1/2">
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg h-full">
          <div class="text-xs font-bold uppercase tracking-widest text-primary flex items-center gap-1 justify-between">
            <span><i class="fa-solid fa-diagram-project"></i> Projects</span>
            <button type="button" class="btn btn-xs btn-secondary" @click="addProject">
              <i class="fa-solid fa-plus"></i>
            </button>
          </div>
          <div v-for="(project, index) in user.projects" :key="index" class="flex items-center gap-2">
            <select class="select select-bordered select-sm flex-1" v-model="project.project_id">
              <option v-for="proj in allProjects" :key="proj.project_id" :value="proj.project_id">
                {{ proj.project_name }}
              </option>
            </select>
            <select class="select select-bordered select-sm" v-model="project.permissions">
              <option value="admin">admin</option>
              <option value="user">user</option>
            </select>
            <label class="flex items-center gap-1 text-xs text-base-content/60 cursor-pointer">
              <input type="checkbox" class="checkbox checkbox-xs" title="Same for children" v-model="project.children" />
              <span>sub</span>
            </label>
            <button type="button" class="btn btn-error btn-xs" @click="removeProject(index)">
              <i class="fa-solid fa-minus"></i>
            </button>
          </div>
          <div v-if="!user.projects?.length" class="text-xs text-base-content-ERROR-40 italic text-center py-3">
            No projects assigned
          </div>
        </div>
      </div>

      <!-- Right column: Apps -->
      <div class="flex flex-col gap-3 w-1/2">
        <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg h-full">
          <div class="text-xs font-bold uppercase tracking-widest text-secondary flex items-center gap-1">
            <i class="fa-solid fa-grid-2"></i> Apps
          </div>
          <div class="flex gap-2 items-center">
            <select class="select select-bordered select-sm flex-1" v-model="newApp">
              <option value="autogenstudio">autogenstudio</option>
              <option value="coder">coder</option>
              <option value="viewer">viewer</option>
              <option value="tasks">tasks</option>
              <option value="files">files</option>
            </select>
            <button type="button" class="btn btn-sm btn-secondary" @click="addApp">
              <i class="fa-solid fa-plus"></i>
            </button>
          </div>
          <div class="flex flex-wrap gap-2 mt-1">
            <span v-for="(app, index) in user.apps" :key="index" class="badge badge-outline gap-1 p-3 text-xs">
              <i class="fa-solid fa-grid-2 text-primary"></i>
              {{ app }}
              <button type="button" class="ml-1 text-error hover:text-red-400" @click="removeApp(index)">
                <i class="fa-solid fa-times"></i>
              </button>
            </span>
            <span v-if="!user.apps?.length" class="text-xs text-base-content-ERROR-40 italic">No apps assigned</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Wallet Tab: delegate entirely to UserWalletSettings -->
    <div v-if="activeTab === 'wallet'" class="w-full grow flex flex-col gap-3">
      <div v-if="!user.wallet" class="flex flex-col items-center justify-center h-full gap-3 text-base-content-ERROR-40">
        <i class="fa-solid fa-wallet text-4xl"></i>
        <span class="text-sm italic">No wallet associated with this user</span>
        <button class="btn btn-sm btn-secondary" @click="createWallet">
          <i class="fa-solid fa-plus mr-1"></i> Create Wallet
        </button>
      </div>
      <!-- UserWalletSettings owns all wallet fields: balance_cxjcoins, name, enabled, spending_limits, transactions -->
      <UserWalletSettings v-else :wallet="user.wallet" />
    </div>

    <!-- Actions -->
    <div class="flex justify-end items-center pt-1">
      <button class="btn btn-primary btn-sm" @click="save">
        <i class="fa-solid fa-floppy-disk mr-1"></i> Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['user', 'settings'],
  data() {
    return {
      activeTab: 'general',
      newApp: ''
    }
  },
  computed: {
    allProjects() {
      return this.$storex.api.allProjects || []
    }
  },
  methods: {
    addProject() {
      if (!this.user.projects) this.user.projects = []
      this.user.projects.push({ project_id: '', permissions: 'user' })
    },
    removeProject(index) {
      this.user.projects.splice(index, 1)
    },
    addApp() {
      if (!this.user.apps) this.user.apps = []
      if (this.newApp && !this.user.apps.includes(this.newApp)) {
        this.user.apps.push(this.newApp)
        this.newApp = ''
      }
    },
    removeApp(index) {
      this.user.apps.splice(index, 1)
    },
    // Initialize wallet with correct Wallet model fields
    createWallet() {
      this.user.wallet = {
        balance_cxjcoins: 0,
        name: 'Default Wallet',
        enabled: true,
        spending_limits: [],
        transactions: []
      }
    },
    // Migrate any legacy max_cxjcoins → limit_cxjcoins before saving
    normalizeLimits(wallet) {
      if (!wallet?.spending_limits) return
      wallet.spending_limits = wallet.spending_limits.map(limit => {
        if ('max_cxjcoins' in limit && !('limit_cxjcoins' in limit)) {
          const { max_cxjcoins, ...rest } = limit
          return { ...rest, limit_cxjcoins: max_cxjcoins }
        }
        return limit
      })
    },
    save() {
      if (this.user.wallet) {
        if (!this.user.wallet.spending_limits) this.user.wallet.spending_limits = []
        this.normalizeLimits(this.user.wallet)
      }
      this.$emit('save', this.user)
    }
  }
}
</script>