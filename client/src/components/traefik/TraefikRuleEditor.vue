<template>
  <Teleport to="body">
    <div class="modal modal-open z-50">
      <div class="modal-box w-11/12 max-w-3xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-start gap-3">
          <div class="w-9 h-9 rounded-lg bg-primary/15 text-primary flex items-center justify-center shrink-0">
            <i class="fa-solid fa-route"></i>
          </div>
          <div class="min-w-0 grow">
            <h3 class="font-bold text-lg">
              {{ mode === 'edit' ? 'Edit Traefik rule' : 'New Traefik rule' }}
            </h3>
            <p class="text-xs opacity-60">
              {{ scope === 'global' ? 'Global rule' : `Project rule · ${projectName || 'this project'}` }}
            </p>
          </div>
          <button class="btn btn-ghost btn-sm btn-circle" @click="$emit('cancel')" aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="divider my-3"></div>

        <div class="space-y-4">
          <!-- Name / description -->
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs font-semibold">Name</span></label>
              <input v-model="form.name" class="input input-bordered input-sm" placeholder="My service" />
            </div>
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs font-semibold">Description</span></label>
              <input v-model="form.description" class="input input-bordered input-sm" placeholder="Optional" />
            </div>
          </div>

          <!-- Target type -->
          <div>
            <div class="text-xs font-semibold mb-1">Target</div>
            <div role="tablist" class="tabs tabs-boxed tabs-sm bg-base-200 w-full">
              <button v-for="option in targetTypeOptions" :key="option.id" role="tab"
                      class="tab gap-1.5" :class="{ 'tab-active': form.target_type === option.id }"
                      @click="setTargetType(option.id)">
                <i class="fas" :class="option.icon"></i>
                {{ option.label }}
              </button>
            </div>
          </div>

          <!-- Workspace app -->
          <div v-if="form.target_type === 'workspace_app'" class="grid gap-3 sm:grid-cols-2">
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs">Workspace</span></label>
              <select v-model="form.workspace_slug" class="select select-bordered select-sm"
                      @change="onWorkspaceChange">
                <option value="">Select a workspace…</option>
                <option v-for="ws in workspaceOptions" :key="ws.slug" :value="ws.slug">
                  {{ ws.name }} ({{ ws.slug }})
                </option>
              </select>
            </div>
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs">App</span></label>
              <select v-model="form.app_id" class="select select-bordered select-sm"
                      :disabled="!form.workspace_slug" @change="onAppChange">
                <option value="">Select an app…</option>
                <option v-for="app in appOptions" :key="app.id" :value="app.id" :disabled="!app.targetable">
                  {{ app.name }} {{ app.port ? `· :${app.port}` : (app.external ? '· URL' : '') }}
                  {{ app.targetable ? '' : '· not targetable' }}
                </option>
              </select>
            </div>
            <div v-if="selectedApp && !selectedApp.targetable" class="sm:col-span-2 alert alert-warning py-2">
              <i class="fas fa-triangle-exclamation"></i>
              <span class="text-xs">
                This app has no container port and no external URL, so a custom rule cannot target it.
              </span>
            </div>
            <div v-else-if="selectedApp" class="sm:col-span-2 text-xs opacity-60">
              <i class="fas fa-link mr-1"></i>
              <span v-if="selectedApp.external">External URL: <span class="font-mono">{{ selectedApp.path }}</span></span>
              <span v-else>Container port: <span class="font-mono">{{ selectedApp.port }}</span></span>
              <div class="text-[11px] opacity-60 mt-1">
                Reuses the Traefik service created by the workspace labels. A custom compose file
                must define the same service for this app.
              </div>
            </div>
          </div>

          <!-- Running container -->
          <div v-if="form.target_type === 'container'" class="space-y-3">
            <div class="grid gap-3 sm:grid-cols-2">
              <div class="form-control">
                <label class="label py-1"><span class="label-text text-xs">Container</span></label>
                <select v-model="form.container_name" class="select select-bordered select-sm" @change="onContainerChange">
                  <option value="">Select a running container…</option>
                  <option v-for="container in containerOptions" :key="container.id" :value="container.name">
                    {{ container.name }} · {{ container.image }}
                  </option>
                </select>
              </div>
              <div class="form-control">
                <label class="label py-1"><span class="label-text text-xs">Container port</span></label>
                <input v-model.number="form.container_port" type="number" min="1" max="65535"
                       class="input input-bordered input-sm" placeholder="3000" />
              </div>
            </div>

            <div v-if="selectedContainer" class="rounded-lg bg-base-200/60 p-2 text-xs space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="badge badge-xs" :class="selectedContainer.running ? 'badge-success' : 'badge-ghost'">
                  {{ selectedContainer.state || 'unknown' }}
                </span>
                <span class="opacity-60 font-mono">{{ selectedContainer.image }}</span>
              </div>
              <div class="opacity-60">
                <i class="fas fa-network-wired mr-1"></i>
                {{ (selectedContainer.networks || []).join(', ') || 'no docker network' }}
              </div>
              <div v-if="selectedContainer.ports?.length" class="flex flex-wrap items-center gap-1">
                <span class="opacity-60">Detected ports:</span>
                <button v-for="port in selectedContainer.ports" :key="port" type="button"
                        class="badge badge-xs badge-outline font-mono cursor-pointer"
                        :class="{ 'badge-primary': Number(form.container_port) === port }"
                        @click="form.container_port = port">
                  {{ port }}
                </button>
              </div>
              <div v-if="selectedContainer.reachable === false" class="text-warning">
                <i class="fas fa-triangle-exclamation mr-1"></i>
                Traefik is not attached to any of this container's networks. The route may fail.
              </div>
              <div v-else-if="selectedContainer.reachable === true" class="text-success">
                <i class="fas fa-circle-check mr-1"></i>
                Traefik shares a network with this container.
              </div>
            </div>

            <div v-if="targets.error" class="alert alert-warning py-2">
              <i class="fas fa-triangle-exclamation"></i>
              <span class="text-xs">Docker discovery unavailable: {{ targets.error }}</span>
            </div>
          </div>

          <!-- URL -->
          <div v-if="form.target_type === 'url'" class="form-control">
            <label class="label py-1"><span class="label-text text-xs">Service URL</span></label>
            <input v-model="form.url" class="input input-bordered input-sm font-mono"
                   placeholder="http://host:8080/app" @change="onUrlChange" />
            <label class="label py-1">
              <span class="label-text-alt opacity-60">
                Traefik forwards to this URL. A path in the URL is preserved by the strip middleware.
              </span>
            </label>
          </div>

          <!-- Rule expression -->
          <div>
            <div class="flex items-center gap-2">
              <label class="label py-1 grow"><span class="label-text text-xs font-semibold">Traefik rule</span></label>
              <button class="btn btn-xs btn-ghost" type="button" @click="generateRule">
                <i class="fas fa-wand-magic-sparkles"></i> Generate
              </button>
            </div>
            <textarea v-model="form.rule" rows="2"
                      class="textarea textarea-bordered w-full font-mono text-xs"
                      placeholder="Host(`app.example.com`) && PathPrefix(`/app`)"></textarea>
            <div class="text-[11px] opacity-50 mt-1">
              Full Traefik rule expression. Use Host/PathPrefix/Path or any Traefik matcher.
            </div>
          </div>

          <!-- Path prefix + strip -->
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs">Public path prefix</span></label>
              <input v-model="form.path_prefix" class="input input-bordered input-sm font-mono"
                     placeholder="/app" />
              <label class="label py-1">
                <span class="label-text-alt opacity-60">Used by the strip middleware and the default rule.</span>
              </label>
            </div>
            <div class="flex flex-col justify-center gap-2">
              <label class="label cursor-pointer justify-start gap-2 py-0">
                <input type="checkbox" v-model="form.strip_prefix" class="checkbox checkbox-sm" />
                <span class="label-text text-sm">Strip the public path prefix</span>
              </label>
              <label class="label cursor-pointer justify-start gap-2 py-0">
                <input type="checkbox" v-model="form.auth" class="checkbox checkbox-sm" />
                <span class="label-text text-sm">Require codx-junior authentication</span>
              </label>
            </div>
          </div>

          <!-- Entrypoints / middleware / priority -->
          <div class="grid gap-3 sm:grid-cols-3">
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs">Entrypoints</span></label>
              <div class="flex flex-wrap gap-3">
                <label v-for="ep in entrypointOptions" :key="ep" class="label cursor-pointer gap-1.5 py-0">
                  <input type="checkbox" class="checkbox checkbox-xs"
                         :checked="form.entrypoints.includes(ep)" @change="toggleEntrypoint(ep)" />
                  <span class="label-text text-xs">{{ ep }}</span>
                </label>
              </div>
            </div>
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs">Extra middlewares</span></label>
              <input v-model="middlewaresText" class="input input-bordered input-sm font-mono"
                     placeholder="compress, secure-headers" />
            </div>
            <div class="form-control">
              <label class="label py-1"><span class="label-text text-xs">Priority</span></label>
              <input v-model.number="form.priority" type="number" class="input input-bordered input-sm"
                     placeholder="default" />
            </div>
          </div>

          <label class="label cursor-pointer justify-start gap-2 py-0">
            <input type="checkbox" v-model="form.enabled" class="toggle toggle-sm toggle-primary" />
            <span class="label-text text-sm">Publish this rule to Traefik</span>
          </label>

          <div v-if="error" class="alert alert-error py-2">
            <i class="fas fa-circle-exclamation"></i>
            <span class="text-xs">{{ error }}</span>
          </div>
        </div>

        <div class="modal-action">
          <button class="btn btn-sm btn-ghost" @click="$emit('cancel')">Cancel</button>
          <button class="btn btn-sm btn-primary gap-2" :disabled="busy" @click="submit">
            <span v-if="busy" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fas fa-floppy-disk"></i>
            {{ mode === 'edit' ? 'Save changes' : 'Create rule' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="$emit('cancel')"></form>
    </div>
  </Teleport>
</template>

<script>
import {
  createTraefikRule,
  createTraefikRuleId,
} from '@/api/model/traefik.js'

const TARGET_TYPES = [
  { id: 'workspace_app', label: 'Workspace app', icon: 'fa-cubes' },
  { id: 'container', label: 'Running container', icon: 'fa-cube' },
  { id: 'url', label: 'URL', icon: 'fa-globe' },
]

export default {
  props: {
    value: { type: Object, default: () => ({}) },
    targets: { type: Object, default: () => ({}) },
    scope: { type: String, default: 'global' },
    projectName: { type: String, default: '' },
    mode: { type: String, default: 'create' },
    busy: { type: Boolean, default: false },
  },
  emits: ['save', 'cancel'],
  data() {
    return {
      form: this.normalise(this.value),
      error: null,
      autoRule: '',
      targetTypeOptions: TARGET_TYPES,
    }
  },
  computed: {
    workspaceOptions() {
      return this.targets?.workspaces || []
    },
    selectedWorkspace() {
      return this.workspaceOptions.find(ws => ws.slug === this.form.workspace_slug) || null
    },
    appOptions() {
      return this.selectedWorkspace?.apps || []
    },
    selectedApp() {
      return this.appOptions.find(app => app.id === this.form.app_id) || null
    },
    containerOptions() {
      return this.targets?.containers || []
    },
    selectedContainer() {
      return this.containerOptions.find(c => c.name === this.form.container_name) || null
    },
    defaults() {
      return this.targets?.defaults || {}
    },
    domain() {
      return this.defaults.domain || globalThis.location?.hostname || 'localhost'
    },
    entrypointOptions() {
      const values = new Set([...(this.defaults.entrypoints || []), ...(this.form.entrypoints || [])])
      return Array.from(values)
    },
    middlewaresText: {
      get() {
        return (this.form.middlewares || []).join(', ')
      },
      set(value) {
        this.form.middlewares = String(value || '')
          .split(',')
          .map(item => item.trim())
          .filter(Boolean)
      },
    },
  },
  methods: {
    normalise(value) {
      const form = createTraefikRule(value || {})
      form.entrypoints = Array.isArray(form.entrypoints) ? [...form.entrypoints] : []
      form.middlewares = Array.isArray(form.middlewares) ? [...form.middlewares] : []
      if (!['workspace_app', 'container', 'url'].includes(form.target_type)) {
        form.target_type = 'workspace_app'
      }
      return form
    },
    setTargetType(type) {
      if (this.form.target_type === type) return
      this.form.target_type = type
      this.error = null
      // Only regenerate when the user has not written a custom rule.
      if (!this.form.rule || this.form.rule === this.autoRule) {
        this.generateRule()
      }
    },
    onWorkspaceChange() {
      this.form.app_id = ''
      this.generateRule()
    },
    onAppChange() {
      this.generateRule()
    },
    onContainerChange() {
      const container = this.selectedContainer
      if (container?.ports?.length) {
        this.form.container_port = container.ports[0]
      }
      this.generateRule()
    },
    onUrlChange() {
      this.generateRule()
    },
    toggleEntrypoint(entrypoint) {
      const index = this.form.entrypoints.indexOf(entrypoint)
      if (index >= 0) {
        this.form.entrypoints.splice(index, 1)
      } else {
        this.form.entrypoints.push(entrypoint)
      }
    },
    sanitize(value) {
      return String(value || '')
        .toLowerCase()
        .replace(/[^a-z0-9_.-]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'app'
    },
    defaultPrefix() {
      if (this.form.target_type === 'workspace_app') {
        const app = this.selectedApp
        if (!app) return ''
        if (app.external) {
          return app.route_path
            || `/ws/${this.selectedWorkspace?.slug || this.form.workspace_slug}/${app.id}`
        }
        return app.route_path || app.path || `/${this.sanitize(app.name || app.id)}`
      }
      if (this.form.target_type === 'container') {
        return this.form.container_name ? `/${this.sanitize(this.form.container_name)}` : ''
      }
      if (this.form.target_type === 'url') {
        try {
          const parsed = new URL(this.form.url)
          if (parsed.pathname && parsed.pathname !== '/') return parsed.pathname.replace(/\/+$/, '')
        } catch (err) {
          // URL not complete yet — fall through to the name-based prefix.
        }
        return this.form.name ? `/${this.sanitize(this.form.name)}` : ''
      }
      return ''
    },
    generateRule() {
      const prefix = this.defaultPrefix()
      if (!prefix) return
      this.form.path_prefix = prefix
      this.form.rule = `Host(\`${this.domain}\`) && PathPrefix(\`${prefix}\`)`
      this.autoRule = this.form.rule
    },
    validate() {
      if (!this.form.name?.trim()) return 'Give the rule a name.'
      if (!this.form.rule?.trim()) return 'The Traefik rule expression is required.'
      if (this.form.target_type === 'workspace_app') {
        if (!this.form.workspace_slug) return 'Select a workspace.'
        if (!this.form.app_id) return 'Select a workspace app.'
        if (this.selectedApp && !this.selectedApp.targetable) {
          return 'This workspace app has no container port and no external URL.'
        }
      } else if (this.form.target_type === 'container') {
        if (!this.form.container_name) return 'Select a running container.'
        const port = Number(this.form.container_port)
        if (!port || port < 1 || port > 65535) return 'Enter a valid container port.'
      } else if (this.form.target_type === 'url') {
        if (!/^https?:\/\//i.test(this.form.url || '')) {
          return 'Enter an absolute http:// or https:// service URL.'
        }
      }
      if (this.form.strip_prefix && !this.form.path_prefix) {
        return 'Set a public path prefix or disable "Strip the public path prefix".'
      }
      return null
    },
    submit() {
      this.error = this.validate()
      if (this.error) return
      const rule = {
        ...this.form,
        id: this.form.id || createTraefikRuleId(),
        name: (this.form.name || '').trim(),
        rule: (this.form.rule || '').trim(),
        path_prefix: (this.form.path_prefix || '').trim(),
        container_port: this.form.container_port ? Number(this.form.container_port) : null,
        priority: this.form.priority === '' || this.form.priority == null
          ? null
          : Number(this.form.priority),
        entrypoints: [...(this.form.entrypoints || [])],
        middlewares: [...(this.form.middlewares || [])],
      }
      this.$emit('save', rule)
    },
  },
}
</script>
