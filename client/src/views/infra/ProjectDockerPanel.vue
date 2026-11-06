<template>
  <div>
    <!-- ── Scan header ───────────────────────────────────────────────────── -->
    <div class="flex flex-wrap items-start gap-3 mb-3">
      <div class="min-w-0">
        <h3 class="font-bold flex items-center gap-2">
          <i class="fas fa-folder-tree text-primary"></i>
          Docker assets in the active project
        </h3>
        <p class="text-xs opacity-60 mt-0.5">
          <span v-if="projectName"><b>{{ projectName }}</b> · </span>
          {{ roots.length }} folder(s) scanned
          <span v-if="state.projectDocker?.scanned_at"> · {{ fmtTime(state.projectDocker.scanned_at) }}</span>
          <span v-if="state.projectDocker?.cached" class="opacity-70"> (cached)</span>
        </p>
      </div>
      <div class="flex-1"></div>
      <button class="btn btn-sm btn-ghost" :disabled="refreshing" @click="refreshScan">
        <span v-if="refreshing" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fas fa-radar"></i>
        {{ refreshing ? 'Scanning…' : 'Rescan' }}
      </button>
      <button class="btn btn-sm btn-ghost" title="Copy the scanned folders"
              :disabled="!roots.length" @click="copyRoots">
        <i class="fas fa-copy"></i> Roots
      </button>
    </div>

    <div v-if="state.projectDocker?.message" class="alert alert-info py-2 mb-3">
      <i class="fas fa-circle-info"></i>
      <span class="text-sm">{{ state.projectDocker.message }}</span>
    </div>

    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-box-open text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">No docker assets found</h3>
        <p class="text-sm opacity-60 max-w-md">
          The scan looks for <span class="font-mono">compose.yaml</span>,
          <span class="font-mono">docker-compose.yml</span> (and overrides),
          <span class="font-mono">Dockerfile*</span> and
          <span class="font-mono">Containerfile*</span> inside the active project
          and its child projects.
        </p>
        <p v-if="!state.projectDocker" class="text-xs opacity-50">
          The Docker asset scan is not available for this project/backend yet.
        </p>
      </div>
    </div>

    <div v-else class="space-y-6">
      <!-- ── Compose projects ─────────────────────────────────────────── -->
      <section v-if="composeItems.length">
        <h4 class="font-bold text-sm mb-2 flex items-center gap-2">
          <i class="fas fa-layer-group text-primary"></i>
          Compose projects
          <span class="badge badge-sm badge-ghost">{{ composeItems.length }}</span>
        </h4>
        <div class="grid gap-3" :class="layout.twoCol ? 'grid-cols-2' : 'grid-cols-1'">
          <div v-for="item in composeItems" :key="item.key"
               class="card bg-base-200 border border-base-300 shadow-sm">
            <div class="card-body p-3 gap-2">
              <div class="flex items-start gap-2">
                <i class="fas fa-layer-group text-primary mt-1"></i>
                <div class="min-w-0 grow">
                  <div class="font-bold truncate">{{ item.label || item.name }}</div>
                  <div class="text-[11px] opacity-50 font-mono truncate" :title="item.path">
                    {{ item.relative_path || item.path }}
                  </div>
                </div>
                <span class="badge badge-sm shrink-0" :class="statusBadge(liveStatus(item))">
                  {{ liveStatus(item) }}
                </span>
              </div>

              <div class="flex flex-wrap items-center gap-1">
                <span v-if="item.project" class="badge badge-xs badge-outline">{{ item.project }}</span>
                <span v-for="file in item.files || []" :key="file"
                      class="badge badge-xs badge-ghost font-mono" :title="file">
                  {{ fileName(file) }}
                </span>
                <span v-if="item.error" class="badge badge-xs badge-error" :title="item.error">config error</span>
              </div>

              <div class="flex items-center gap-2">
                <span class="text-xs opacity-60">
                  {{ liveStack(item)?.running || 0 }}/{{ item.total || (item.declared_services || []).length }}
                  services running
                </span>
                <progress class="progress grow h-1 progress-primary"
                          :value="item.total ? ((liveStack(item)?.running || 0) / item.total) * 100 : 0"
                          max="100"></progress>
              </div>

              <div class="flex flex-wrap gap-1">
                <span v-for="name in item.declared_services || []" :key="name"
                      class="badge badge-xs badge-outline font-mono">{{ name }}</span>
              </div>

              <div class="flex flex-wrap items-center gap-1.5 pt-2 border-t border-base-300">
                <button v-if="liveStack(item)?.running" class="btn btn-xs btn-error btn-outline grow"
                        :disabled="stackActionBusy(item.name)" @click="askStackAction(liveStack(item), 'stop')">
                  <i class="fas fa-stop"></i> Stop
                </button>
                <button v-else class="btn btn-xs btn-success grow"
                        :disabled="stackActionBusy(item.name)" @click="askStackAction(liveStack(item), 'up')">
                  <i class="fas fa-play"></i> Start
                </button>
                <button class="btn btn-xs btn-square btn-ghost" title="Build images"
                        aria-label="Build images" :disabled="stackActionBusy(item.name)"
                        @click="askStackAction(liveStack(item), 'build')">
                  <i class="fas fa-hammer"></i>
                </button>
                <button class="btn btn-xs btn-square btn-ghost" title="Pull images"
                        aria-label="Pull images" :disabled="stackActionBusy(item.name)"
                        @click="askStackAction(liveStack(item), 'pull')">
                  <i class="fas fa-download"></i>
                </button>
                <button v-if="hasRuntime(item)" class="btn btn-xs btn-square btn-ghost"
                        title="Compose logs" aria-label="Compose logs" @click="openStackLogs(liveStack(item))">
                  <i class="fas fa-file-lines"></i>
                </button>
                <button class="btn btn-xs btn-ghost" @click="openStack(item)">
                  <i class="fas fa-arrow-up-right-from-square"></i> Stacks
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ── Dockerfiles ──────────────────────────────────────────────── -->
      <section v-if="dockerfileItems.length">
        <h4 class="font-bold text-sm mb-2 flex items-center gap-2">
          <i class="fas fa-box text-primary"></i>
          Dockerfiles
          <span class="badge badge-sm badge-ghost">{{ dockerfileItems.length }}</span>
        </h4>
        <div class="grid gap-3" :class="layout.twoCol ? 'grid-cols-2' : 'grid-cols-1'">
          <div v-for="item in dockerfileItems" :key="item.key"
               class="card bg-base-200 border border-base-300 shadow-sm">
            <div class="card-body p-3 gap-2">
              <div class="flex items-start gap-2">
                <i class="fas fa-file-code text-primary mt-1"></i>
                <div class="min-w-0 grow">
                  <div class="font-bold truncate">{{ item.name }}</div>
                  <div class="text-[11px] opacity-50 font-mono truncate" :title="item.path">
                    {{ item.relative_path }}
                  </div>
                </div>
                <button class="btn btn-xs btn-primary shrink-0" @click="openBuild(item)">
                  <i class="fas fa-hammer"></i> Build
                </button>
              </div>

              <div class="flex flex-wrap items-center gap-1">
                <span v-if="item.project" class="badge badge-xs badge-outline">{{ item.project }}</span>
                <span v-if="item.compose_service" class="badge badge-xs badge-info badge-outline"
                      :title="item.compose_project">
                  compose: {{ item.compose_service }}
                </span>
                <span class="badge badge-xs badge-ghost">{{ item.stage_count }} stage(s)</span>
                <span v-if="item.has_dockerignore" class="badge badge-xs badge-ghost">.dockerignore</span>
              </div>

              <div class="flex flex-wrap gap-1">
                <span v-for="image in item.base_images || []" :key="image"
                      class="badge badge-xs badge-outline font-mono" :title="image">
                  FROM {{ image }}
                </span>
              </div>

              <div class="text-[11px] opacity-50 font-mono truncate" :title="item.context">
                context: {{ item.context }}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- ── Dockerfile build dialog ──────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="build.open" class="modal modal-open">
        <div class="modal-box max-w-3xl">
          <h3 class="font-bold text-lg flex items-center gap-2">
            <i class="fas fa-hammer"></i> Build {{ build.file?.name }}
          </h3>
          <p class="text-xs opacity-60 font-mono mt-1 truncate" :title="build.file?.path">
            {{ build.file?.relative_path }}
          </p>

          <div class="py-3 space-y-3">
            <div>
              <label class="label-text text-xs" for="build-tag">Image tag *</label>
              <input id="build-tag" class="input input-bordered input-sm w-full font-mono"
                     :class="{ 'input-error': build.errors.tag }"
                     :value="build.tag" @input="build.tag = $event.target.value" />
              <p v-if="build.errors.tag" class="text-error text-xs mt-1">{{ build.errors.tag }}</p>
            </div>

            <div class="grid gap-3" :class="layout.twoCol ? 'grid-cols-2' : 'grid-cols-1'">
              <div>
                <label class="label-text text-xs" for="build-target">Target stage (optional)</label>
                <input id="build-target" class="input input-bordered input-sm w-full font-mono"
                       placeholder="e.g. runtime" :value="build.target"
                       @input="build.target = $event.target.value" />
              </div>
              <div>
                <label class="label-text text-xs" for="build-context">Build context</label>
                <input id="build-context" class="input input-bordered input-sm w-full font-mono"
                       :value="build.context" @input="build.context = $event.target.value" />
              </div>
            </div>

            <div>
              <label class="label-text text-xs" for="build-args">Build arguments</label>
              <textarea id="build-args" class="textarea textarea-bordered w-full font-mono text-xs"
                        rows="3" placeholder="NODE_ENV=production&#10;VERSION=1.2.3"
                        :value="build.args" @input="build.args = $event.target.value"></textarea>
              <p class="text-xs opacity-50 mt-1">One KEY=VALUE per line (passed as --build-arg).</p>
            </div>

            <div v-if="build.error" class="alert alert-error py-2 text-sm">
              <i class="fas fa-circle-xmark"></i>
              <span class="whitespace-pre-wrap break-words">{{ build.error }}</span>
            </div>

            <div v-if="build.output.length" class="rounded-lg bg-base-300 p-2">
              <div class="text-xs font-bold mb-1">Build output</div>
              <pre class="text-[11px] max-h-56 overflow-auto whitespace-pre-wrap">{{ build.output.join('\n') }}</pre>
            </div>
          </div>

          <div class="modal-action">
            <button class="btn btn-sm btn-ghost" :disabled="build.busy" @click="closeBuild">Close</button>
            <button class="btn btn-sm btn-primary" :disabled="build.busy || !build.file" @click="submitBuild">
              <span v-if="build.busy" class="loading loading-spinner loading-xs"></span>
              <i v-else class="fas fa-hammer"></i>
              {{ build.busy ? 'Building…' : 'Build image' }}
            </button>
          </div>
        </div>
        <div class="modal-backdrop" @click="build.busy ? null : closeBuild()"></div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { API } from '../../api/api'
import {
  state, filteredList, fmtTime, pushToast, loadAll, setFilter, setRoute
} from './useInfra'
import { askStackAction, openStackLogs, stackActionBusy } from './useInfraStacks'
import { layout } from './useInfraLayout'

const refreshing = ref(false)

const composeItems = computed(
  () => filteredList.value.filter(item => item.kind === 'compose')
)
const dockerfileItems = computed(
  () => filteredList.value.filter(item => item.kind === 'dockerfile')
)
const projectName = computed(
  () => state.projectDocker?.project?.name || ''
)
const roots = computed(
  () => state.projectDocker?.roots || state.projectDocker?.project?.roots || []
)

/** The runtime stack that matches a discovered compose project, when any. */
function liveStack(item) {
  if (!item) return item
  return state.stacks.find(s => s.path === item.path)
    || state.stacks.find(s => s.name === item.name && (s.services || []).length)
    || state.stacks.find(s => s.name === item.name)
    || item
}

/** Live status shown on a compose card (falls back to the scanned status). */
function liveStatus(item) {
  return liveStack(item)?.status || item?.status || 'stopped'
}

/** True when the compose project has containers to show/log. */
function hasRuntime(item) {
  const stack = liveStack(item)
  return (stack?.services || []).length > 0 || stack?.running > 0
}

function statusBadge(status) {
  return {
    running: 'badge-success',
    degraded: 'badge-warning',
    stopped: 'badge-error'
  }[status] || 'badge-ghost'
}

function fileName(path) {
  return String(path || '').split('/').filter(Boolean).pop() || path
}

/** Jump to the Stacks tab, already filtered to this project. */
function openStack(item) {
  setFilter({ stack: item.name, q: '' })
  setRoute('stacks')
}

async function refreshScan() {
  refreshing.value = true
  try {
    await loadAll({ silent: true, refreshScan: true })
    pushToast({ text: 'Docker asset scan refreshed', kind: 'success' })
  } catch (err) {
    pushToast({ text: err?.message || String(err), kind: 'error' })
  } finally {
    refreshing.value = false
  }
}

async function copyRoots() {
  try {
    await navigator.clipboard.writeText(roots.value.join('\n'))
    pushToast({ text: 'Scanned roots copied', kind: 'success' })
  } catch (err) {
    pushToast({ text: 'Could not copy the roots', kind: 'warning' })
  }
}

/* ── Dockerfile build dialog ────────────────────────────────────────────── */

function emptyBuild() {
  return {
    open: false,
    file: null,
    tag: '',
    target: '',
    context: '',
    args: '',
    busy: false,
    error: '',
    output: [],
    errors: {}
  }
}

const build = reactive(emptyBuild())

/** Default image name derived from the folder + Dockerfile variant. */
function defaultTag(file) {
  const folder = String(file.directory || '').split('/').filter(Boolean).pop() || 'image'
  const sanitize = (value) => String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9_.-]+/g, '-')
    .replace(/^[^a-z0-9]+|[-_.]+$/g, '')
  const name = file.name || 'Dockerfile'
  const lower = name.toLowerCase()
  let variant = ''
  if (lower.startsWith('dockerfile.')) variant = name.slice('Dockerfile.'.length)
  else if (lower.startsWith('containerfile.')) variant = name.slice('Containerfile.'.length)
  else if (lower.endsWith('.dockerfile')) variant = name.slice(0, -'.dockerfile'.length)
  else if (lower.endsWith('.containerfile')) variant = name.slice(0, -'.containerfile'.length)

  const repo = sanitize(folder) || 'image'
  const suffix = variant ? sanitize(variant) : ''
  return `${repo}${suffix && suffix !== 'image' ? '-' + suffix : ''}:latest`
}

function openBuild(file) {
  Object.assign(build, emptyBuild(), {
    open: true,
    file,
    tag: defaultTag(file),
    context: file.context || file.directory || ''
  })
}

function closeBuild() {
  if (build.busy) return
  Object.assign(build, emptyBuild())
}

/** Parse the textarea into `{KEY: value}`; invalid lines are reported. */
function parseBuildArgs(text) {
  const args = {}
  for (const rawLine of String(text || '').split('\n')) {
    const line = rawLine.trim()
    if (!line) continue
    const index = line.indexOf('=')
    if (index <= 0) throw new Error(`Invalid build argument: '${line}' (expected KEY=VALUE)`)
    args[line.slice(0, index).trim()] = line.slice(index + 1)
  }
  return args
}

async function submitBuild() {
  if (!build.file || build.busy) return
  build.errors = {}
  build.error = ''
  build.output = []

  if (!String(build.tag || '').trim()) {
    build.errors.tag = 'An image tag is required'
    return
  }

  let buildArgs
  try {
    buildArgs = parseBuildArgs(build.args)
  } catch (err) {
    build.error = err.message
    return
  }

  build.busy = true
  try {
    const result = await API.infra.buildDockerfile({
      path: build.file.path,
      tag: build.tag.trim(),
      context: build.context.trim() || undefined,
      target: build.target.trim() || undefined,
      build_args: buildArgs,
      host_id: state.hostId
    })
    build.output = result?.output || []
    pushToast({ text: `Image ${result?.tag || build.tag} built`, kind: 'success' })
    // Refresh the image list and the project scan (a compose build context may
    // have changed the Dockerfile metadata).
    await loadAll({ silent: true })
  } catch (err) {
    build.error = err?.message || String(err)
  } finally {
    build.busy = false
  }
}
</script>
