<template>
  <div class="w-full space-y-4">
    <!-- ── Header ────────────────────────────────────────────────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body p-4 gap-3">
        <div class="flex flex-wrap items-start gap-3">
          <div class="w-10 h-10 rounded-lg bg-primary/15 text-primary flex items-center justify-center shrink-0">
            <i class="fa-solid fa-diagram-project"></i>
          </div>
          <div class="min-w-0 grow">
            <h2 class="font-bold flex flex-wrap items-center gap-2">
              DSH Harness
              <span class="badge badge-sm" :class="statusBadgeClass">{{ statusLabel }}</span>
              <span v-if="config.board" class="badge badge-sm badge-ghost">
                board: {{ config.board }}
              </span>
              <span v-if="usage.cost" class="badge badge-sm badge-ghost">
                cost: {{ usage.cost }}
              </span>
            </h2>
            <p class="text-xs opacity-70 mt-1">
              DSH connects <span class="font-semibold">to</span> codx-junior. It registers,
              heartbeats and long-polls commands, so codx-junior never needs to reach DSH.
              The conversation stays in DSH; the board keeps the task identity and hierarchy.
            </p>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button class="btn btn-sm btn-ghost" :disabled="loadingStatus" @click="refreshStatus" title="Refresh status">
              <i class="fa-solid fa-arrows-rotate" :class="{ 'animate-spin': loadingStatus }"></i>
            </button>
            <button class="btn btn-sm btn-primary" :disabled="!connected" @click="openBoard">
              <i class="fa-solid fa-table-columns"></i>
              <span class="hidden sm:inline">Open board</span>
            </button>
          </div>
        </div>

        <div v-if="error" class="alert alert-error py-2">
          <i class="fa-solid fa-circle-exclamation"></i>
          <span class="text-xs break-all">{{ error }}</span>
          <button class="btn btn-xs btn-ghost" @click="refreshStatus">Retry</button>
        </div>
        <div v-else-if="!config.has_agent_token" class="alert alert-warning py-2">
          <i class="fa-solid fa-key"></i>
          <span class="text-xs">
            Generate an agent token below, then configure it in the DSH plugin
            (or let DSH read <code class="bg-base-300 px-1 rounded">.dsh-codx-junior/token</code>).
          </span>
        </div>
        <div v-else-if="!onlineInstances.length" class="alert alert-info py-2">
          <i class="fa-solid fa-satellite-dish"></i>
          <span class="text-xs">
            No DSH instance is connected. Start the DSH plugin with
            <code class="bg-base-300 px-1 rounded">codxApiUrl</code> pointing at this API and the token below.
          </span>
        </div>
      </div>
    </div>

    <div class="grid gap-4 xl:grid-cols-3">
      <!-- ── Agent connection ───────────────────────────────────────────── -->
      <div class="card bg-base-200 border border-base-300 shadow-sm xl:col-span-2">
        <div class="card-body p-4 gap-4">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="font-semibold flex items-center gap-2">
              <i class="fa-solid fa-key text-primary"></i>
              Agent channel
            </h3>
            <span class="badge badge-sm badge-ghost">
              {{ config.agent_token_source === 'missing' ? 'not configured' : config.agent_token_source }}
            </span>
          </div>

          <label class="form-control">
            <div class="label py-1">
              <span class="label-text text-xs font-semibold">Agent token</span>
              <button class="label-text-alt text-[11px] link link-primary" @click="copyToken" :disabled="!config.agent_token">
                Copy
              </button>
            </div>
            <div class="join w-full">
              <input
                :type="showToken ? 'text' : 'password'"
                class="input input-bordered input-sm join-item grow font-mono text-xs"
                :value="config.agent_token || ''"
                readonly
                placeholder="No token generated yet"
              />
              <button class="btn btn-sm join-item" type="button" @click="showToken = !showToken" :title="showToken ? 'Hide token' : 'Show token'">
                <i class="fa-solid" :class="showToken ? 'fa-eye-slash' : 'fa-eye'"></i>
              </button>
            </div>
            <div class="label py-1">
              <span class="label-text-alt text-[11px] opacity-60">
                DSH sends this as <code>Authorization: Bearer …</code>.
                <span v-if="status?.token_file">The backend also writes <code>{{ status.token_file }}</code>.</span>
              </span>
            </div>
          </label>

          <div class="flex flex-wrap items-center gap-2">
            <button class="btn btn-sm btn-outline" :disabled="rotating" @click="generateToken">
              <i class="fa-solid fa-rotate" :class="{ 'animate-spin': rotating }"></i>
              {{ config.has_agent_token ? 'Rotate token' : 'Generate token' }}
            </button>
            <button class="btn btn-sm btn-ghost" @click="copySnippet" :disabled="!config.agent_token">
              <i class="fa-solid fa-copy"></i>
              Copy DSH config
            </button>
            <button class="btn btn-sm btn-ghost" @click="copyTokenFileHint" :disabled="!status?.token_file">
              <i class="fa-solid fa-file-shield"></i>
              Token file
            </button>
          </div>

          <div class="rounded-lg bg-base-100 border border-base-300 p-3">
            <div class="text-[11px] uppercase tracking-wide opacity-50 mb-1">DSH plugin config</div>
            <pre class="text-[11px] whitespace-pre-wrap break-all m-0">{{ pluginSnippet }}</pre>
          </div>

          <div class="grid gap-3 md:grid-cols-2">
            <label class="form-control">
              <div class="label py-1"><span class="label-text text-xs font-semibold">Mirror board</span></div>
              <input v-model="form.board" type="text" class="input input-bordered input-sm w-full" placeholder="DSH" />
              <div class="label py-1">
                <span class="label-text-alt text-[11px] opacity-60">Created automatically on the first sync.</span>
              </div>
            </label>

            <label class="form-control">
              <div class="label py-1"><span class="label-text text-xs font-semibold">Default instance</span></div>
              <select v-model="form.default_instance_id" class="select select-bordered select-sm w-full">
                <option value="">Auto (most recently seen online)</option>
                <option v-for="instance in instances" :key="instance.id" :value="instance.id">
                  {{ instance.name }} · {{ instance.status }}
                </option>
              </select>
              <div class="label py-1">
                <span class="label-text-alt text-[11px] opacity-60">Used by new tasks and sync when no instance is selected.</span>
              </div>
            </label>

            <label class="label cursor-pointer justify-start gap-3 rounded-lg bg-base-100 border border-base-300 px-3 py-2">
              <input v-model="form.enabled" type="checkbox" class="toggle toggle-primary toggle-sm" />
              <span class="label-text text-xs">
                <span class="font-semibold">Mirror DSH tasks</span>
                <span class="block opacity-60">Accept events and upsert board tasks.</span>
              </span>
            </label>

            <label class="label cursor-pointer justify-start gap-3 rounded-lg bg-base-100 border border-base-300 px-3 py-2">
              <input v-model="form.only_project" type="checkbox" class="toggle toggle-primary toggle-sm" />
              <span class="label-text text-xs">
                <span class="font-semibold">Only this project</span>
                <span class="block opacity-60">Ignore sessions whose working directory is outside this project.</span>
              </span>
            </label>

            <label class="label cursor-pointer justify-start gap-3 rounded-lg bg-base-100 border border-base-300 px-3 py-2">
              <input v-model="form.sandbox_enabled" type="checkbox" class="toggle toggle-primary toggle-sm" />
              <span class="label-text text-xs">
                <span class="font-semibold">Project sandbox</span>
                <span class="block opacity-60">Reject cwd/session paths outside the project; mount only this workspace in the harness container.</span>
              </span>
            </label>
          </div>

          <div class="flex flex-wrap items-center gap-2 pt-1">
            <button class="btn btn-sm btn-primary" :disabled="saving" @click="save">
              <i class="fa-solid fa-floppy-disk" :class="{ 'animate-pulse': saving }"></i>
              Save settings
            </button>
            <button class="btn btn-sm btn-secondary" :disabled="syncing || !selectedInstance" @click="syncNow">
              <i class="fa-solid fa-arrows-rotate" :class="{ 'animate-spin': syncing }"></i>
              {{ syncing ? 'Syncing…' : 'Sync from instance' }}
            </button>
            <span v-if="lastSavedAt" class="text-[11px] opacity-50 ml-auto">Saved {{ lastSavedAt }}</span>
          </div>
        </div>
      </div>

      <!-- ── Instances / quick start ────────────────────────────────────── -->
      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-4 gap-3">
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-semibold flex items-center gap-2">
              <i class="fa-solid fa-server text-primary"></i>
              Instances
            </h3>
            <span class="badge badge-sm" :class="onlineInstances.length ? 'badge-success' : 'badge-ghost'">
              {{ onlineInstances.length }}/{{ instances.length }} online
            </span>
          </div>

          <div v-if="!instances.length" class="text-xs opacity-60 rounded-lg border border-dashed border-base-300 p-3">
            No instance has registered yet. Start DSH with the agent token; it appears here within a few seconds.
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="instance in instances"
              :key="instance.id"
              class="w-full text-left rounded-lg border px-3 py-2 transition-colors"
              :class="selectedInstanceId === instance.id
                ? 'border-primary bg-primary/10'
                : 'border-base-300 bg-base-100 hover:bg-base-300/40'"
              @click="selectInstance(instance)"
            >
              <div class="flex items-center gap-2">
                <span class="badge badge-xs" :class="instance.status === 'online' ? 'badge-success' : 'badge-ghost'">
                  {{ instance.status }}
                </span>
                <span class="font-semibold text-xs truncate">{{ instance.name }}</span>
                <span v-if="form.default_instance_id === instance.id" class="badge badge-xs badge-primary">default</span>
                <i class="fa-solid fa-check ml-auto text-primary" v-if="selectedInstanceId === instance.id"></i>
              </div>
              <div class="text-[11px] opacity-60 mt-1 truncate">{{ instance.cwd || '—' }}</div>
              <div class="text-[11px] opacity-50 mt-0.5">
                {{ instance.sessions }} sessions · {{ instance.running }} running
                <span v-if="instance.version"> · v{{ instance.version }}</span>
                · {{ formatLastSeen(instance.last_seen) }}
              </div>
            </button>
          </div>

          <div class="divider my-1"></div>

          <h4 class="font-semibold text-sm flex items-center gap-2">
            <i class="fa-solid fa-rocket text-primary"></i>
            Quick start
          </h4>
          <ol class="text-xs opacity-75 space-y-2 list-decimal list-inside">
            <li>Generate the agent token.</li>
            <li>Set <code class="bg-base-300 px-1 rounded">codxApiUrl</code> and the token in the DSH plugin.</li>
            <li>Start or reload DSH; the instance appears here.</li>
            <li>Save the board and click <span class="font-semibold">Sync from instance</span>.</li>
            <li>Open the board or create a task below.</li>
          </ol>
        </div>
      </div>
    </div>

    <!-- ── Trigger task ───────────────────────────────────────────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body p-4 gap-3">
        <div class="flex flex-wrap items-start gap-2">
          <div class="w-9 h-9 rounded-lg bg-secondary/15 text-secondary flex items-center justify-center shrink-0">
            <i class="fa-solid fa-play"></i>
          </div>
          <div class="min-w-0 grow">
            <h3 class="font-semibold">Trigger a DSH task</h3>
            <p class="text-xs opacity-60">
              Sends a command to <span class="font-semibold">{{ selectedInstance?.name || 'the selected instance' }}</span>.
              DSH creates the Session and runs it; codx-junior mirrors the task and reads the conversation live.
            </p>
          </div>
        </div>

        <div class="grid gap-3 md:grid-cols-3">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">Instance</span></div>
            <select v-model="selectedInstanceId" class="select select-bordered select-sm w-full" @change="onInstanceChanged">
              <option v-for="instance in instances" :key="instance.id" :value="instance.id">
                {{ instance.name }} · {{ instance.status }}
              </option>
            </select>
          </label>
          <label class="form-control md:col-span-2">
            <div class="label py-1"><span class="label-text text-xs font-semibold">Task title</span></div>
            <input v-model="createForm.name" type="text" class="input input-bordered input-sm w-full" placeholder="What should DSH work on?" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">Board column</span></div>
            <select v-model="createForm.column" class="select select-bordered select-sm w-full">
              <option v-for="column in columnOptions" :key="column" :value="column">{{ column }}</option>
            </select>
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">Model</span></div>
            <select v-model="createForm.model" class="select select-bordered select-sm w-full">
              <option value="">DSH default</option>
              <option v-for="model in models" :key="model.name" :value="model.name">
                {{ model.name }} · {{ model.ai_provider }}
              </option>
            </select>
            <div class="label py-1">
              <span class="label-text-alt text-[11px] opacity-60">
                Models come from codx-junior. Map one with <code>metadata.dsh</code> when DSH uses a different id.
              </span>
            </div>
          </label>
          <label class="form-control md:col-span-2">
            <div class="label py-1"><span class="label-text text-xs font-semibold">Prompt</span></div>
            <textarea
              v-model="createForm.prompt"
              class="textarea textarea-bordered w-full text-sm"
              rows="3"
              placeholder="Describe the task. DSH receives this as the first message of the Session."
            ></textarea>
          </label>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button class="btn btn-sm btn-primary" :disabled="!canCreate || creating" @click="createTask">
            <i class="fa-solid fa-paper-plane" :class="{ 'animate-pulse': creating }"></i>
            {{ creating ? 'Creating…' : 'Create DSH task' }}
          </button>
          <span class="text-[11px] opacity-50">The task becomes visible in DSH immediately.</span>
        </div>

        <div v-if="lastCreated" class="alert alert-success py-2">
          <i class="fa-solid fa-circle-check"></i>
          <span class="text-xs">
            Created <span class="font-semibold">{{ lastCreated.chat?.name || lastCreated.session_id }}</span>
            on {{ instanceName(lastCreated.instance_id) }} ({{ lastCreated.session_id }}).
          </span>
        </div>
        <div
          v-if="lastCreated?.chat?.harness_metadata?.model_selection && lastCreated.chat.harness_metadata.model_selection.applied === false"
          class="alert alert-warning py-2"
        >
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span class="text-xs">
            The model could not be applied in DSH:
            {{ lastCreated.chat.harness_metadata.model_selection.error || 'unknown error' }}.
            Add a <code>metadata.dsh</code> mapping to the model or configure DSH's default model.
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
const DEFAULT_FORM = () => ({
  board: 'DSH',
  enabled: true,
  only_project: true,
  sandbox_enabled: true,
  default_instance_id: '',
})

export default {
  props: {
    settings: { type: Object, default: () => ({}) },
  },
  data() {
    return {
      form: DEFAULT_FORM(),
      status: null,
      selectedInstanceId: '',
      loadingStatus: false,
      saving: false,
      rotating: false,
      syncing: false,
      creating: false,
      showToken: false,
      error: null,
      lastSavedAt: null,
      lastCreated: null,
      createForm: { name: '', prompt: '', column: 'Todo', model: '' },
      models: [],
    }
  },
  computed: {
    config() {
      return this.status?.config || {}
    },
    instances() {
      return this.status?.instances || []
    },
    onlineInstances() {
      return this.instances.filter((instance) => instance.status === 'online')
    },
    selectedInstance() {
      return this.instances.find((instance) => instance.id === this.selectedInstanceId)
        || this.onlineInstances[0]
        || this.instances[0]
        || null
    },
    connected() {
      return Boolean(this.config.enabled && this.config.has_agent_token && this.onlineInstances.length)
    },
    statusLabel() {
      if (!this.config.enabled) return 'Disabled'
      if (!this.config.has_agent_token) return 'No token'
      if (this.onlineInstances.length) return 'Connected'
      if (this.instances.length) return 'Instances offline'
      return 'Waiting for DSH'
    },
    statusBadgeClass() {
      if (!this.config.enabled) return 'badge-ghost'
      if (this.connected) return 'badge-success'
      if (this.instances.length || !this.config.has_agent_token) return 'badge-warning'
      return 'badge-ghost'
    },
    mirroredTasks() {
      return this.status?.mirrored_tasks ?? 0
    },
    usage() {
      return this.status?.usage || {}
    },
    columnOptions() {
      return this.config.columns?.length ? this.config.columns : ['Todo', 'Doing', 'On hold', 'Done']
    },
    pluginSnippet() {
      const token = this.config.agent_token || '<generate a token above>'
      return [
        'config:',
        '  codxApiUrl: http://127.0.0.1:19980',
        `  token: "${token}"`,
        '  agentEnabled: true',
        '  bridgeEnabled: false',
      ].join('\n')
    },
    canCreate() {
      return Boolean(this.selectedInstance && this.createForm.name.trim())
    },
  },
  watch: {
    'settings.dsh': {
      immediate: true,
      deep: true,
      handler(value) {
        if (value) this.applySettings(value)
      },
    },
  },
  created() {
    this.refreshStatus()
  },
  methods: {
    getApi() {
      return this.$project?.$api || this.$storex?.api
    },
    notify(text, type = 'info') {
      this.$ui?.addNotification({ text, type })
    },
    errorText(error) {
      return error?.response?.data?.detail || error?.message || String(error)
    },
    applySettings(value) {
      this.form = {
        board: value?.board || DEFAULT_FORM().board,
        enabled: value?.enabled !== false,
        only_project: value?.only_project !== false,
        sandbox_enabled: value?.sandbox_enabled !== false,
        default_instance_id: value?.default_instance_id || '',
      }
    },
    async refreshStatus() {
      const api = this.getApi()
      if (!api?.dsh) {
        this.error = 'DSH API is not available in this build.'
        return
      }
      this.loadingStatus = true
      this.error = null
      try {
        this.status = await api.dsh.status()
        this.pickInstance()
        if (this.status?.error) this.error = this.status.error
        try {
          const modelResponse = await api.dsh.models()
          this.models = modelResponse?.models || []
        } catch (modelError) {
          // The model catalogue is optional; task creation still works with
          // the DSH default when an older backend does not expose it.
          console.warn('[DshIntegrationPanel] model catalogue failed', modelError)
          this.models = []
        }
      } catch (error) {
        console.error('[DshIntegrationPanel] status failed', error)
        this.error = this.errorText(error)
        this.status = null
      } finally {
        this.loadingStatus = false
      }
    },
    pickInstance() {
      const wanted = this.selectedInstanceId || this.form.default_instance_id
      const found = this.instances.find((instance) => instance.id === wanted)
      if (found && (found.status === 'online' || !this.onlineInstances.length)) {
        this.selectedInstanceId = found.id
        return
      }
      const fallback = this.onlineInstances[0] || this.instances[0]
      this.selectedInstanceId = fallback?.id || ''
    },
    onInstanceChanged() {
      const instance = this.instances.find((item) => item.id === this.selectedInstanceId)
      if (instance) this.form.default_instance_id = instance.id
    },
    selectInstance(instance) {
      this.selectedInstanceId = instance.id
      this.form.default_instance_id = instance.id
    },
    async save({ silent = false } = {}) {
      const api = this.getApi()
      if (!api?.dsh) return null
      this.saving = true
      this.error = null
      try {
        const payload = {
          board: this.form.board.trim() || 'DSH',
          enabled: Boolean(this.form.enabled),
          only_project: Boolean(this.form.only_project),
          sandbox_enabled: Boolean(this.form.sandbox_enabled),
          default_instance_id: this.form.default_instance_id || '',
        }
        const response = await api.dsh.saveSettings(payload)
        if (response?.settings) {
          this.settings.dsh = {
            ...(this.settings.dsh || {}),
            ...response.settings,
          }
        }
        this.lastSavedAt = new Date().toLocaleTimeString()
        await this.refreshStatus()
        if (!silent) this.notify('DSH settings saved', 'success')
        return response
      } catch (error) {
        console.error('[DshIntegrationPanel] save failed', error)
        this.error = this.errorText(error)
        if (!silent) this.notify(this.error, 'error')
        return null
      } finally {
        this.saving = false
      }
    },
    async generateToken() {
      if (this.config.has_agent_token && !window.confirm(
        'Rotate the agent token? Running DSH instances will reconnect only after they receive the new token.',
      )) return
      const api = this.getApi()
      if (!api?.dsh) return
      this.rotating = true
      this.error = null
      try {
        const result = await api.dsh.generateToken()
        if (result?.token) {
          this.settings.dsh = {
            ...(this.settings.dsh || {}),
            agent_token: result.token,
          }
        }
        await this.refreshStatus()
        this.notify('Agent token generated', 'success')
      } catch (error) {
        console.error('[DshIntegrationPanel] token generation failed', error)
        this.error = this.errorText(error)
        this.notify(this.error, 'error')
      } finally {
        this.rotating = false
      }
    },
    async copyToken() {
      const token = this.config.agent_token
      if (!token) return
      try {
        await navigator.clipboard.writeText(token)
        this.notify('Agent token copied', 'success')
      } catch {
        this.notify('Clipboard unavailable; select the field and copy it manually', 'error')
      }
    },
    async copySnippet() {
      try {
        await navigator.clipboard.writeText(this.pluginSnippet)
        this.notify('DSH plugin config copied', 'success')
      } catch {
        this.notify('Clipboard unavailable; copy the snippet manually', 'error')
      }
    },
    async copyTokenFileHint() {
      const path = this.status?.token_file
      if (!path) return
      try {
        await navigator.clipboard.writeText(path)
        this.notify('Token file path copied', 'success')
      } catch {
        this.notify(path, 'info')
      }
    },
    async syncNow() {
      const api = this.getApi()
      if (!api?.dsh || !this.selectedInstance) return
      this.syncing = true
      this.error = null
      try {
        await this.save({ silent: true })
        const result = await api.dsh.sync(this.selectedInstance.id)
        await Promise.allSettled([
          this.$storex?.projects?.loadKanban?.(),
          this.$storex?.chats?.loadChats?.(),
        ])
        await this.refreshStatus()
        this.notify(
          `Synced ${result?.total ?? 0} task(s): ${result?.created ?? 0} new, ${result?.updated ?? 0} updated`,
          'success',
        )
      } catch (error) {
        console.error('[DshIntegrationPanel] sync failed', error)
        this.error = this.errorText(error)
        this.notify(this.error, 'error')
      } finally {
        this.syncing = false
      }
    },
    async createTask() {
      const api = this.getApi()
      if (!api?.dsh || !this.canCreate) return
      this.creating = true
      this.error = null
      try {
        await this.save({ silent: true })
        const result = await api.dsh.createTask({
          instance_id: this.selectedInstance.id,
          name: this.createForm.name.trim(),
          prompt: this.createForm.prompt.trim(),
          board: this.form.board.trim() || 'DSH',
          column: this.createForm.column,
          model: this.createForm.model || null,
        })
        this.lastCreated = result
        this.createForm = { name: '', prompt: '', column: this.createForm.column, model: this.createForm.model }
        await Promise.allSettled([
          this.$storex?.projects?.loadKanban?.(),
          this.$storex?.chats?.loadChats?.(),
        ])
        await this.refreshStatus()
        this.notify('DSH task created', 'success')
      } catch (error) {
        console.error('[DshIntegrationPanel] create task failed', error)
        this.error = this.errorText(error)
        this.notify(this.error, 'error')
      } finally {
        this.creating = false
      }
    },
    instanceName(instanceId) {
      return this.instances.find((instance) => instance.id === instanceId)?.name || instanceId || 'DSH'
    },
    formatLastSeen(value) {
      if (!value) return 'unknown'
      try {
        return new Date(value).toLocaleTimeString()
      } catch {
        return String(value)
      }
    },
    openBoard() {
      const projectName = this.$storex?.projects?.activeProject?.project_name
        || this.$project?.settings?.project_name
      if (!projectName) return
      this.$router.push({ name: 'kanban', params: { projectName } })
    },
  },
}
</script>
