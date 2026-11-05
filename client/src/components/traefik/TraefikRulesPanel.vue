<template>
  <div class="w-full space-y-4">
    <!-- ── Header ────────────────────────────────────────────────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body p-3 gap-3">
        <div class="flex flex-wrap items-start gap-2">
          <div class="w-9 h-9 rounded-lg bg-primary/15 text-primary flex items-center justify-center shrink-0">
            <i class="fa-solid fa-route"></i>
          </div>
          <div class="min-w-0 grow">
            <h2 class="font-bold flex flex-wrap items-center gap-2">
              Traefik routes
              <span class="badge badge-sm" :class="scope === 'global' ? 'badge-primary' : 'badge-secondary'">
                {{ scope === 'global' ? 'Global' : (projectName || 'Project') }}
              </span>
            </h2>
            <p class="text-xs opacity-60 mt-0.5">
              <template v-if="scope === 'global'">
                Global rules apply to every project. Project rules are shown read-only here;
                edit them from each project's settings.
              </template>
              <template v-else>
                These rules are stored with this project's <code class="bg-base-300 px-1 rounded">.codx/project.json</code>
                and travel with it. Global rules are inherited read-only.
              </template>
            </p>
            <div class="text-[11px] opacity-45 mt-1">
              <i class="fas fa-circle-info mr-1"></i>
              Custom rules are additive. Use <span class="font-semibold">Priority</span> to make one win over a generated route.
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 shrink-0">
            <button class="btn btn-sm btn-ghost" :disabled="loading" @click="refresh" title="Reload routes">
              <i class="fas fa-arrows-rotate" :class="{ 'animate-spin': loading }"></i>
            </button>
            <button class="btn btn-sm btn-ghost" @click="openPreview" title="Preview generated config">
              <i class="fas fa-code"></i>
              <span class="hidden sm:inline">Preview</span>
            </button>
            <button class="btn btn-sm btn-primary" @click="openCreate">
              <i class="fas fa-plus"></i>
              New rule
            </button>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <div v-for="stat in statCards" :key="stat.id"
               class="rounded-lg bg-base-100 border border-base-300 px-2 py-1.5">
            <div class="text-[10px] uppercase tracking-wide opacity-50 flex items-center gap-1">
              <i class="fas" :class="stat.icon"></i>{{ stat.label }}
            </div>
            <div class="font-bold text-lg leading-tight" :class="stat.class">{{ stat.value }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Errors ────────────────────────────────────────────────────────── -->
    <div v-if="error" class="alert alert-error py-2">
      <i class="fas fa-circle-exclamation"></i>
      <span class="text-xs">{{ error }}</span>
      <button class="btn btn-xs btn-ghost" @click="refresh">Retry</button>
    </div>
    <div v-if="targets.error" class="alert alert-warning py-2">
      <i class="fas fa-triangle-exclamation"></i>
      <span class="text-xs">Docker target discovery unavailable: {{ targets.error }}</span>
    </div>

    <!-- ── Filters ───────────────────────────────────────────────────────── -->
    <div class="flex flex-wrap items-center gap-2">
      <label class="input input-bordered input-sm flex items-center gap-2 flex-1 min-w-52">
        <i class="fas fa-magnifying-glass opacity-50"></i>
        <input v-model="filters.q" type="text" class="grow min-w-0"
               placeholder="Search by name, rule or target…" />
      </label>
      <select v-model="filters.source" class="select select-bordered select-sm w-40">
        <option v-for="option in sourceFilterOptions" :key="option.id" :value="option.id">
          {{ option.label }}
        </option>
      </select>
      <select v-model="filters.enabled" class="select select-bordered select-sm w-36">
        <option value="all">All states</option>
        <option value="enabled">Enabled</option>
        <option value="disabled">Disabled</option>
      </select>
      <span class="text-xs opacity-50 ml-auto">{{ filteredRoutes.length }} route(s)</span>
    </div>

    <!-- ── Loading / empty ───────────────────────────────────────────────── -->
    <div v-if="loading && !routes.length" class="card bg-base-200 border border-base-300">
      <div class="card-body p-4 space-y-2">
        <div v-for="i in 4" :key="i" class="skeleton h-12 w-full"></div>
      </div>
    </div>

    <div v-else-if="!filteredRoutes.length" class="card bg-base-200 border border-base-300">
      <div class="card-body items-center text-center py-10">
        <i class="fas fa-route text-4xl text-primary/40"></i>
        <h3 class="font-bold mt-2">No matching routes</h3>
        <p class="text-sm opacity-60 max-w-md">
          Workspace apps appear here automatically. Add a custom rule to route a running
          container, another workspace service or an external URL.
        </p>
        <button class="btn btn-sm btn-primary mt-2" @click="openCreate">
          <i class="fas fa-plus"></i> New rule
        </button>
      </div>
    </div>

    <!-- ── Route list ────────────────────────────────────────────────────── -->
    <div v-else class="flex flex-col gap-2">
      <div v-for="row in filteredRoutes" :key="rowKey(row)"
           class="card bg-base-100 border border-base-200 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-start gap-2">
            <div class="w-7 h-7 rounded-md bg-base-200 flex items-center justify-center shrink-0"
                 :class="sourceIconClass(row)">
              <i class="fas" :class="sourceIcon(row)"></i>
            </div>

            <div class="min-w-0 grow">
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="font-semibold text-sm">{{ row.name || row.id }}</span>
                <span class="badge badge-xs" :class="sourceBadgeClass(row)">{{ sourceLabel(row) }}</span>
                <span v-if="row.managed_by" class="badge badge-xs badge-ghost">{{ managedLabel(row) }}</span>
                <span v-if="!row.enabled" class="badge badge-xs badge-warning badge-outline">disabled</span>
                <span v-if="row.issues?.length" class="badge badge-xs badge-error badge-outline gap-1">
                  <i class="fas fa-triangle-exclamation"></i>{{ row.issues.length }}
                </span>
                <span v-if="!row.editable" class="badge badge-xs badge-ghost gap-1">
                  <i class="fas fa-lock"></i> read-only
                </span>
              </div>

              <div class="text-[11px] opacity-50 mt-0.5 flex flex-wrap items-center gap-2">
                <span v-if="row.workspace_name">
                  <i class="fas fa-cubes mr-1"></i>{{ row.workspace_name }}
                </span>
                <span v-if="row.project_name">
                  <i class="fas fa-diagram-project mr-1"></i>{{ row.project_name }}
                </span>
                <span v-if="row.priority != null">
                  <i class="fas fa-ranking-star mr-1"></i>priority {{ row.priority }}
                </span>
                <span v-if="row.entrypoints?.length">
                  <i class="fas fa-right-to-bracket mr-1"></i>{{ row.entrypoints.join(', ') }}
                </span>
              </div>
            </div>

            <div class="flex items-center gap-1 shrink-0">
              <button v-if="row.editable" class="btn btn-xs btn-ghost" title="Edit rule"
                      @click="openEdit(row)">
                <i class="fas fa-pen"></i>
              </button>
              <button class="btn btn-xs btn-ghost" title="Clone as a new rule" @click="cloneRoute(row)">
                <i class="fas fa-copy"></i>
              </button>
              <button v-if="row.editable" class="btn btn-xs btn-ghost text-error" title="Delete rule"
                      @click="askDelete(row)">
                <i class="fas fa-trash-can"></i>
              </button>
            </div>
          </div>

          <div class="rounded-md bg-base-200/70 px-2 py-1 font-mono text-[11px] break-all">
            <span class="opacity-40">rule </span>{{ row.rule || '—' }}
          </div>

          <div class="flex flex-wrap items-center gap-2 text-xs">
            <span class="opacity-60 min-w-0 break-all">
              <i class="fas fa-arrow-right mr-1"></i>{{ targetLabel(row) }}
            </span>
            <span v-for="middleware in row.middlewares || []" :key="middleware"
                  class="badge badge-xs badge-outline font-mono">{{ middleware }}</span>
          </div>

          <ul v-if="row.issues?.length" class="text-[11px] text-warning space-y-0.5">
            <li v-for="(issue, index) in row.issues" :key="index">
              <i class="fas fa-triangle-exclamation mr-1"></i>{{ issue }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- ── Editor ────────────────────────────────────────────────────────── -->
    <TraefikRuleEditor
      v-if="showEditor"
      :value="editing"
      :targets="targets"
      :scope="scope"
      :project-name="projectName"
      :mode="editorMode"
      :busy="saving"
      @save="saveDraft"
      @cancel="closeEditor"
    />

    <!-- ── Delete confirmation ───────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="deleting" class="modal modal-open z-50">
        <div class="modal-box">
          <h3 class="font-bold text-lg flex items-center gap-2">
            <i class="fas fa-triangle-exclamation text-error"></i>
            Delete Traefik rule?
          </h3>
          <p class="py-3 text-sm opacity-80">
            Delete <strong>{{ deleting.name || deleting.id }}</strong>?
            Traefik will remove the route after its next configuration poll.
          </p>
          <div class="modal-action">
            <button class="btn btn-sm btn-ghost" :disabled="saving" @click="deleting = null">Cancel</button>
            <button class="btn btn-sm btn-error gap-2" :disabled="saving" @click="confirmDelete">
              <span v-if="saving" class="loading loading-spinner loading-xs"></span>
              <i v-else class="fas fa-trash-can"></i>
              Delete
            </button>
          </div>
        </div>
        <form method="dialog" class="modal-backdrop" @click="deleting = null"></form>
      </div>
    </Teleport>

    <!-- ── Config preview ────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showPreview" class="modal modal-open z-50">
        <div class="modal-box w-11/12 max-w-5xl max-h-[90vh] flex flex-col">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-primary/15 text-primary flex items-center justify-center">
              <i class="fas fa-code"></i>
            </div>
            <div class="grow min-w-0">
              <h3 class="font-bold">Generated Traefik config</h3>
              <p class="text-xs opacity-60">
                Exactly what <code class="bg-base-200 px-1 rounded">GET /api/traefik/config</code>
                returns to Traefik.
              </p>
            </div>
            <button class="btn btn-ghost btn-sm btn-circle" @click="showPreview = false" aria-label="Close">
              <i class="fas fa-xmark"></i>
            </button>
          </div>

          <div class="divider my-2"></div>

          <div class="flex-1 overflow-auto rounded-lg bg-base-200 p-3">
            <div v-if="previewLoading" class="flex items-center justify-center py-12">
              <span class="loading loading-spinner loading-lg text-primary"></span>
            </div>
            <pre v-else class="text-[11px] font-mono whitespace-pre-wrap break-all">{{ previewJson }}</pre>
          </div>

          <div v-if="preview?.issues?.length" class="mt-2 max-h-28 overflow-auto">
            <div class="text-xs font-semibold text-warning mb-1">Issues</div>
            <ul class="text-[11px] text-warning space-y-0.5">
              <li v-for="(issue, index) in preview.issues" :key="index">
                <i class="fas fa-triangle-exclamation mr-1"></i>{{ issue }}
              </li>
            </ul>
          </div>

          <div class="modal-action">
            <button class="btn btn-sm" @click="showPreview = false">Close</button>
          </div>
        </div>
        <form method="dialog" class="modal-backdrop" @click="showPreview = false"></form>
      </div>
    </Teleport>
  </div>
</template>

<script>
import TraefikRuleEditor from './TraefikRuleEditor.vue'
import {
  createTraefikRule,
  createTraefikRuleId,
} from '@/api/model/traefik.js'

const SOURCE_ORDER = { workspace: 0, global: 1, project: 2 }

export default {
  components: { TraefikRuleEditor },
  props: {
    scope: { type: String, default: 'global' }, // global | project
    projectId: { type: String, default: '' },
    projectName: { type: String, default: '' },
    rules: { type: Array, default: () => [] },
  },
  emits: ['update:rules', 'saved'],
  data() {
    return {
      loading: false,
      saving: false,
      error: null,
      routes: [],
      stats: {},
      issues: [],
      targets: { workspaces: [], containers: [], traefik_networks: [], defaults: {} },
      filters: { q: '', source: 'all', enabled: 'all' },
      showEditor: false,
      editorMode: 'create',
      editing: null,
      deleting: null,
      showPreview: false,
      previewLoading: false,
      preview: null,
      sourceFilterOptions: [
        { id: 'all', label: 'All sources' },
        { id: 'workspace', label: 'Workspace' },
        { id: 'global', label: 'Global rules' },
        { id: 'project', label: 'Project rules' },
      ],
    }
  },
  computed: {
    statCards() {
      const stats = this.stats || {}
      const computed = {
        total: this.routes.length,
        workspace: this.routes.filter(row => row.source === 'workspace').length,
        global: this.routes.filter(row => row.source === 'custom' && row.scope === 'global').length,
        project: this.routes.filter(row => row.source === 'custom' && row.scope === 'project').length,
        issues: this.issues.length,
      }
      const value = key => (stats[key] != null ? stats[key] : computed[key])
      return [
        { id: 'total', label: 'Routes', icon: 'fa-route', value: value('total'), class: 'text-primary' },
        { id: 'workspace', label: 'Workspace', icon: 'fa-cubes', value: value('workspace'), class: '' },
        { id: 'global', label: 'Global', icon: 'fa-globe', value: value('global'), class: '' },
        { id: 'project', label: 'Project', icon: 'fa-diagram-project', value: value('project'), class: '' },
        { id: 'issues', label: 'Issues', icon: 'fa-triangle-exclamation', value: value('issues'), class: 'text-warning' },
      ]
    },
    filteredRoutes() {
      const term = (this.filters.q || '').trim().toLowerCase()
      return [...this.routes]
        .filter(row => {
          if (this.filters.enabled === 'enabled' && !row.enabled) return false
          if (this.filters.enabled === 'disabled' && row.enabled) return false
          if (this.filters.source === 'workspace' && row.source !== 'workspace') return false
          if (this.filters.source === 'global' && !(row.source === 'custom' && row.scope === 'global')) return false
          if (this.filters.source === 'project' && !(row.source === 'custom' && row.scope === 'project')) return false
          if (!term) return true
          return [row.name, row.description, row.rule, row.target, row.target_url, row.workspace_name, row.project_name]
            .filter(Boolean)
            .some(value => String(value).toLowerCase().includes(term))
        })
        .sort((a, b) => {
          const order = (SOURCE_ORDER[a.scope] ?? 9) - (SOURCE_ORDER[b.scope] ?? 9)
          if (order) return order
          return String(a.name || a.id).localeCompare(String(b.name || b.id))
        })
    },
    previewJson() {
      return JSON.stringify(this.preview?.config || {}, null, 2)
    },
  },
  watch: {
    projectId() {
      this.load()
    },
  },
  mounted() {
    // The global view needs every project's rules; ask the backend to refresh
    // its project snapshot on the first load. Project view reads its own
    // project.json directly and does not need the extra scan.
    this.load(this.scope === 'global')
  },
  methods: {
    getApi() {
      return this.$project?.$api || this.$storex?.api
    },
    notify(text, type = 'info') {
      this.$ui?.addNotification({ text, type })
    },
    async load(refresh = false) {
      if (this.scope === 'project' && !this.projectId) {
        this.error = 'Project is not loaded yet.'
        return
      }

      const api = this.getApi()
      if (!api?.traefik) {
        this.error = 'Traefik API is not available.'
        return
      }

      this.loading = true
      this.error = null
      try {
        const [routesResult, targetsResult] = await Promise.allSettled([
          api.traefik.routes({
            projectId: this.scope === 'project' ? this.projectId : undefined,
            refresh,
          }),
          api.traefik.targets(),
        ])

        if (routesResult.status !== 'fulfilled') {
          throw routesResult.reason
        }

        const routesResponse = routesResult.value
        this.routes = routesResponse?.routes || []
        this.stats = routesResponse?.stats || {}
        this.issues = routesResponse?.issues || []

        if (targetsResult.status === 'fulfilled') {
          this.targets = targetsResult.value || this.targets
        } else {
          // Docker discovery is optional for viewing existing rules; keep the
          // route list usable and surface the target error separately.
          this.targets = {
            ...this.targets,
            error: targetsResult.reason?.message || String(targetsResult.reason),
          }
        }
      } catch (err) {
        console.error('[TraefikRulesPanel] load failed', err)
        this.error = err?.response?.data?.detail || err?.message || String(err)
      } finally {
        this.loading = false
      }
    },
    refresh() {
      return this.load(true)
    },
    async saveRules(nextRules) {
      if (this.scope === 'project' && !this.projectId) {
        this.error = 'Project is not loaded yet.'
        return false
      }

      const api = this.getApi()
      if (!api?.traefik) {
        this.error = 'Traefik API is not available.'
        return false
      }

      this.saving = true
      this.error = null
      try {
        const response = this.scope === 'global'
          ? await api.traefik.global.saveRules(nextRules)
          : await api.traefik.projects.saveRules(this.projectId, nextRules)
        const savedRules = response?.rules || nextRules
        this.$emit('update:rules', savedRules)
        this.$emit('saved', response)
        this.notify('Traefik rules saved', 'success')
        await this.load()
        return true
      } catch (err) {
        console.error('[TraefikRulesPanel] save failed', err)
        this.error = err?.response?.data?.detail || err?.message || String(err)
        this.notify(this.error, 'error')
        return false
      } finally {
        this.saving = false
      }
    },
    openCreate() {
      const hasTargetableApp = (this.targets.workspaces || [])
        .some(workspace => (workspace.apps || []).some(app => app.targetable))
      this.editing = createTraefikRule({
        target_type: hasTargetableApp ? 'workspace_app' : 'url',
        auth: true,
        strip_prefix: true,
        entrypoints: this.targets.defaults?.entrypoints?.length
          ? [...this.targets.defaults.entrypoints]
          : ['web', 'websecure'],
      })
      this.editorMode = 'create'
      this.showEditor = true
    },
    findStoredRule(id) {
      return (this.rules || []).find(rule => rule.id === id) || null
    },
    ruleFromRow(row) {
      const generated = new Set([
        'codx-junior-auth',
        'codx-junior-auth@docker',
        `${row.router_id}-strip`,
        `${row.router_id}-strip@docker`,
      ])
      const middlewares = row.middlewares || []
      return createTraefikRule({
        id: row.id,
        name: row.name,
        description: row.description,
        enabled: row.enabled,
        target_type: row.target_type,
        url: row.target_type === 'url' ? (row.target_url || '') : '',
        workspace_slug: row.workspace_slug || '',
        app_id: row.app_id || '',
        container_name: row.container_name || '',
        container_port: row.container_port ?? null,
        rule: row.rule || '',
        path_prefix: row.path_prefix || '',
        entrypoints: [...(row.entrypoints || [])],
        middlewares: middlewares.filter(middleware => !generated.has(middleware)),
        auth: middlewares.some(middleware => middleware.startsWith('codx-junior-auth')),
        strip_prefix: middlewares.some(middleware =>
          middleware === `${row.router_id}-strip` ||
          middleware === `${row.router_id}-strip@docker`
        ),
        priority: row.priority ?? null,
      })
    },
    openEdit(row) {
      if (!row.editable) return
      const stored = this.findStoredRule(row.id)
      this.editing = stored
        ? JSON.parse(JSON.stringify(stored))
        : this.ruleFromRow(row)
      this.editorMode = 'edit'
      this.showEditor = true
    },
    cloneRoute(row) {
      const copy = this.ruleFromRow(row)
      copy.id = createTraefikRuleId()
      copy.name = `Copy of ${row.name || row.id}`
      copy.enabled = true
      if (!copy.entrypoints.length) {
        copy.entrypoints = [...(this.targets.defaults?.entrypoints || ['web', 'websecure'])]
      }
      this.editing = copy
      this.editorMode = 'create'
      this.showEditor = true
    },
    async saveDraft(rule) {
      const list = this.rules || []
      const exists = list.some(item => item.id === rule.id)
      const nextRules = this.editorMode === 'edit' && exists
        ? list.map(item => (item.id === rule.id ? rule : item))
        : [...list, rule]
      const saved = await this.saveRules(nextRules)
      if (saved) this.closeEditor()
    },
    closeEditor() {
      this.showEditor = false
      this.editing = null
    },
    askDelete(row) {
      if (!row.editable) return
      this.deleting = row
    },
    async confirmDelete() {
      if (!this.deleting) return
      const nextRules = (this.rules || []).filter(rule => rule.id !== this.deleting.id)
      const saved = await this.saveRules(nextRules)
      if (saved) this.deleting = null
    },
    async openPreview() {
      const api = this.getApi()
      if (!api?.traefik) {
        this.error = 'Traefik API is not available.'
        return
      }
      this.showPreview = true
      this.previewLoading = true
      this.preview = null
      try {
        this.preview = await api.traefik.preview({
          projectId: this.scope === 'project' ? this.projectId : undefined,
        })
      } catch (err) {
        console.error('[TraefikRulesPanel] preview failed', err)
        this.error = err?.response?.data?.detail || err?.message || String(err)
      } finally {
        this.previewLoading = false
      }
    },
    rowKey(row) {
      return `${row.scope}:${row.project_id || ''}:${row.id}:${row.router_id || ''}`
    },
    sourceLabel(row) {
      if (row.source === 'workspace') return 'Workspace'
      if (row.scope === 'global') return 'Global'
      return row.project_name || 'Project'
    },
    sourceBadgeClass(row) {
      if (row.source === 'workspace') return 'badge-info badge-outline'
      if (row.scope === 'global') return 'badge-primary badge-outline'
      return 'badge-secondary badge-outline'
    },
    sourceIcon(row) {
      if (row.source === 'workspace') return 'fa-cubes'
      if (row.scope === 'global') return 'fa-globe'
      return 'fa-diagram-project'
    },
    sourceIconClass(row) {
      if (row.source === 'workspace') return 'text-info'
      if (row.scope === 'global') return 'text-primary'
      return 'text-secondary'
    },
    managedLabel(row) {
      if (row.managed_by === 'docker-labels') return 'docker labels'
      if (row.managed_by === 'http-provider') return 'http provider'
      return ''
    },
    targetLabel(row) {
      if (row.target) return row.target
      if (row.target_url) return row.target_url
      return '—'
    },
  },
}
</script>
