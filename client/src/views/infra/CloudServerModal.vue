<template>
  <!-- ── Cloud server wizard ─────────────────────────────────────────────────
       provider → credentials → server → provisioning.

       SECURITY: the credentials typed in step 2 live in `modal.credentials`
       (memory) only. They are sent with the creation request and wiped as soon
       as the provider accepts them: nothing is written to localStorage, to the
       URL, or back to the API.

       The provider catalog comes from `GET /api/infra/cloud/providers`, so the
       form renders itself — adding a provider needs no front-end change. -->
  <Teleport to="body">
    <div v-if="modal" class="fixed inset-0 z-[85] flex items-center justify-center p-2 sm:p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close"></div>

      <div role="dialog" aria-modal="true" aria-labelledby="cloud-modal-title"
           class="relative z-10 flex flex-col w-full max-w-3xl max-h-[92vh] bg-base-100 border border-base-300 rounded-xl shadow-2xl overflow-hidden">

        <!-- ── Header ─────────────────────────────────────────────────────── -->
        <header class="shrink-0 flex items-start gap-2 px-4 py-3 border-b border-base-300 bg-base-200">
          <i class="fas fa-cloud text-primary mt-1"></i>
          <div class="min-w-0 grow">
            <h3 id="cloud-modal-title" class="font-bold leading-tight">Create a Docker server</h3>
            <p class="text-xs opacity-60">
              Provision a machine at {{ provider.name }} and register it as a Docker host.
            </p>
          </div>
          <span class="badge badge-sm badge-outline shrink-0">{{ provider.name }}</span>
          <button class="btn btn-sm btn-ghost btn-square shrink-0"
                  aria-label="Close the cloud wizard" title="Close (Esc)" @click="close">
            <i class="fas fa-xmark"></i>
          </button>
        </header>

        <!-- ── Step strip ─────────────────────────────────────────────────── -->
        <ul class="shrink-0 steps steps-horizontal w-full px-4 pt-3 text-xs">
          <li v-for="(s, ix) in CLOUD_FLOW" :key="s.id" class="step"
              :class="{ 'step-primary': stepIndex >= ix }"
              :aria-current="modal.step === s.id ? 'step' : undefined">
            {{ s.label }}
          </li>
        </ul>

        <!-- ── Body ───────────────────────────────────────────────────────── -->
        <div class="grow min-h-0 overflow-auto px-4 py-4">

          <!-- 1 · provider -->
          <div v-if="modal.step === 'provider'" class="grid gap-2 sm:grid-cols-3">
            <button v-for="p in providers" :key="p.id" type="button"
                    class="card bg-base-200 border text-left transition-colors duration-150"
                    :class="p.id === modal.providerId
                      ? 'border-primary ring-1 ring-primary'
                      : 'border-base-300 hover:border-primary/50'"
                    :aria-pressed="p.id === modal.providerId"
                    @click="chooseProvider(p.id)">
              <div class="card-body p-3 gap-1">
                <div class="flex items-center gap-2">
                  <i class="fas" :class="p.icon" aria-hidden="true"></i>
                  <span class="font-semibold">{{ p.name }}</span>
                </div>
                <p class="text-[11px] opacity-60 leading-snug">{{ p.summary }}</p>
                <span class="badge badge-xs badge-ghost mt-1">{{ (p.regions || []).length }} regions</span>
              </div>
            </button>
          </div>

          <!-- 2 · credentials (transient) -->
          <div v-else-if="modal.step === 'credentials'" class="space-y-3">
            <div class="alert alert-warning py-2" role="note">
              <i class="fas fa-shield-halved" aria-hidden="true"></i>
              <span class="text-xs">
                These credentials are sent with this request only — codx-junior does not store them.
                Prefer a scoped token and revoke it when you are done.
              </span>
            </div>

            <div class="flex justify-end">
              <label class="label cursor-pointer gap-2 py-0">
                <span class="label-text text-xs">Show secrets</span>
                <input type="checkbox" class="toggle toggle-xs" v-model="revealSecrets" />
              </label>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <div v-for="f in provider.credentials" :key="f.key"
                   :class="f.type === 'textarea' ? 'sm:col-span-2' : ''">
                <label class="label label-text text-xs" :for="`cloud-cred-${f.key}`">
                  {{ f.label }}<span v-if="f.required" class="text-error" aria-hidden="true"> *</span>
                </label>

                <textarea v-if="f.type === 'textarea'" :id="`cloud-cred-${f.key}`"
                          class="textarea textarea-bordered textarea-sm w-full font-mono text-xs"
                          :class="{ 'textarea-error': modal.errors[f.key] }"
                          rows="3" :placeholder="f.placeholder || ''"
                          :value="modal.credentials[f.key] || ''"
                          @input="onCredential(f.key, $event)"></textarea>

                <input v-else :id="`cloud-cred-${f.key}`" :type="inputType(f)"
                       class="input input-bordered input-sm w-full font-mono text-xs"
                       :class="{ 'input-error': modal.errors[f.key] }"
                       autocomplete="off" spellcheck="false"
                       :placeholder="f.placeholder || ''"
                       :value="modal.credentials[f.key] || ''"
                       @input="onCredential(f.key, $event)" />

                <p v-if="modal.errors[f.key]" class="text-error text-xs mt-1">{{ modal.errors[f.key] }}</p>
                <p v-else-if="f.help" class="text-[11px] opacity-50 mt-1">{{ f.help }}</p>
              </div>
            </div>

            <div v-if="modal.testResult" class="alert py-2" role="status"
                 :class="modal.testResult.ok ? 'alert-success' : 'alert-error'">
              <i class="fas" :class="modal.testResult.ok ? 'fa-circle-check' : 'fa-circle-xmark'" aria-hidden="true"></i>
              <div class="text-xs">
                <p class="font-semibold">{{ modal.testResult.text }}</p>
                <p v-if="modal.testResult.account" class="opacity-70 font-mono">{{ modal.testResult.account }}</p>
              </div>
            </div>
          </div>

          <!-- 3 · server -->
          <div v-else-if="modal.step === 'server'" class="space-y-4">
            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="label label-text text-xs" for="cloud-name">Server name *</label>
                <input id="cloud-name" type="text" class="input input-bordered input-sm w-full font-mono"
                       :class="{ 'input-error': modal.errors.name }"
                       placeholder="docker-edge-01" autocomplete="off"
                       :value="form.name" @input="onField('name', $event)" />
                <p v-if="modal.errors.name" class="text-error text-xs mt-1">{{ modal.errors.name }}</p>
                <p v-else class="text-[11px] opacity-50 mt-1">Lowercase letters, digits and dashes.</p>
              </div>

              <div>
                <label class="label label-text text-xs" for="cloud-region">Region *</label>
                <select id="cloud-region" class="select select-bordered select-sm w-full"
                        :class="{ 'select-error': modal.errors.region }"
                        :value="form.region" @change="onField('region', $event)">
                  <option v-for="o in provider.regions" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
                <p v-if="modal.errors.region" class="text-error text-xs mt-1">{{ modal.errors.region }}</p>
              </div>

              <div>
                <label class="label label-text text-xs" for="cloud-size">Size *</label>
                <select id="cloud-size" class="select select-bordered select-sm w-full"
                        :class="{ 'select-error': modal.errors.size }"
                        :value="form.size" @change="onField('size', $event)">
                  <option v-for="o in provider.sizes" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
                <p v-if="modal.errors.size" class="text-error text-xs mt-1">{{ modal.errors.size }}</p>
              </div>

              <div>
                <label class="label label-text text-xs" for="cloud-image">Image *</label>
                <select id="cloud-image" class="select select-bordered select-sm w-full"
                        :class="{ 'select-error': modal.errors.image }"
                        :value="form.image" @change="onField('image', $event)">
                  <option v-for="o in provider.images" :key="o.value" :value="o.value">{{ o.label }}</option>
                </select>
                <p v-if="modal.errors.image" class="text-error text-xs mt-1">{{ modal.errors.image }}</p>
              </div>

              <div>
                <label class="label label-text text-xs" for="cloud-ssh-user">SSH user</label>
                <input id="cloud-ssh-user" type="text" class="input input-bordered input-sm w-full font-mono"
                       :value="form.ssh_user" @input="onField('ssh_user', $event)" />
                <p class="text-[11px] opacity-50 mt-1">
                  Login user of the image (<code class="font-mono">ubuntu</code>, <code class="font-mono">azureuser</code>…).
                </p>
              </div>

              <div>
                <label class="label label-text text-xs" for="cloud-ports">Open ports</label>
                <input id="cloud-ports" type="text" class="input input-bordered input-sm w-full font-mono"
                       placeholder="22, 2376"
                       :value="form.open_ports" @input="onField('open_ports', $event)" />
                <p class="text-[11px] opacity-50 mt-1">Comma separated. 22 (SSH) is always opened.</p>
              </div>
            </div>

            <!-- the same key manager as the host dialog -->
            <SshKeyField />
            <p v-if="modal.errors.ssh_key_id" class="text-error text-xs -mt-2">{{ modal.errors.ssh_key_id }}</p>

            <label class="label cursor-pointer justify-start gap-2 py-0">
              <input type="checkbox" class="toggle toggle-sm toggle-primary"
                     :checked="form.install_docker !== false"
                     @change="onField('install_docker', $event, 'checked')" />
              <span class="label-text text-xs">Install Docker Engine during the bootstrap</span>
            </label>

            <div class="rounded-lg bg-base-200 border border-base-300 p-3 text-xs space-y-1">
              <p class="font-semibold">Summary</p>
              <p class="opacity-70">
                {{ provider.name }} · {{ optionLabel(provider.regions, form.region) }} ·
                {{ optionLabel(provider.sizes, form.size) }}
              </p>
              <p class="opacity-70">
                {{ optionLabel(provider.images, form.image) }} · user
                <code class="font-mono">{{ form.ssh_user || provider.ssh_user }}</code>
              </p>
              <p class="opacity-50">
                The public key of the selected pair is injected during the first boot, so no password
                ever leaves the browser. The server is registered as a host when provisioning ends.
              </p>
            </div>

            <div v-if="modal.errors.submit" class="alert alert-error py-2" role="alert">
              <i class="fas fa-circle-xmark" aria-hidden="true"></i>
              <span class="text-xs">{{ modal.errors.submit }}</span>
            </div>
          </div>

          <!-- 4 · provisioning -->
          <div v-else class="space-y-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="badge" :class="jobTone">{{ job.status }}</span>
              <span class="text-sm opacity-70">{{ job.message || 'Provisioning…' }}</span>
              <div class="flex-1"></div>
              <span class="text-xs opacity-50">{{ job.progress }}%</span>
            </div>

            <progress class="progress w-full"
                      :class="job.status === 'error'
                        ? 'progress-error'
                        : (job.status === 'ready' ? 'progress-success' : 'progress-primary')"
                      :value="job.progress" max="100"></progress>

            <ol class="space-y-1">
              <li v-for="(s, ix) in CLOUD_JOB_STEPS" :key="s.id" class="flex items-center gap-2 text-xs">
                <i class="fas w-4 text-center" :class="jobStepIcon(ix)" aria-hidden="true"></i>
                <span :class="ix <= jobIndex ? '' : 'opacity-50'">{{ s.label }}</span>
              </li>
            </ol>

            <div class="grid gap-2 sm:grid-cols-3 text-xs">
              <div class="rounded-lg bg-base-200 p-2">
                <div class="opacity-50">Server</div>
                <div class="font-mono truncate">{{ job.hostname || job.id || '—' }}</div>
              </div>
              <div class="rounded-lg bg-base-200 p-2">
                <div class="opacity-50">IP</div>
                <div class="font-mono">{{ job.ip || '—' }}</div>
              </div>
              <div class="rounded-lg bg-base-200 p-2">
                <div class="opacity-50">Host</div>
                <div class="font-mono truncate">{{ job.host_id || '—' }}</div>
              </div>
            </div>

            <div v-if="job.status === 'error'" class="alert alert-error py-2" role="alert">
              <i class="fas fa-circle-xmark" aria-hidden="true"></i>
              <span class="text-xs">{{ job.message || 'Provisioning failed' }}</span>
            </div>

            <div v-if="job.logs.length" class="rounded-lg bg-base-300/60 p-2 max-h-48 overflow-auto">
              <p v-for="(line, i) in job.logs" :key="i" class="font-mono text-[11px]">
                <span class="opacity-40">{{ fmtTime(line.ts) }}</span> {{ line.msg }}
              </p>
            </div>

            <p v-if="modal.credentialsCleared" class="text-[11px] opacity-50">
              <i class="fas fa-lock" aria-hidden="true"></i>
              The credentials were discarded once the provider accepted the request.
            </p>

            <p class="text-[11px] opacity-40">
              Closing this dialog does not cancel the server creation — the job keeps running on the
              codx-junior server and the host appears in the selector when it is ready.
            </p>
          </div>
        </div>

        <!-- ── Footer ─────────────────────────────────────────────────────── -->
        <footer class="shrink-0 px-4 py-3 border-t border-base-300 bg-base-200 flex flex-wrap items-center gap-2">
          <button v-if="modal.step === 'progress' && job.id"
                  class="btn btn-sm btn-ghost text-error"
                  title="Destroy the server at the provider" @click="askDestroy">
            <i class="fas fa-trash-can"></i> Delete server
          </button>
          <div class="flex-1"></div>

          <button v-if="modal.step !== 'progress'" class="btn btn-sm btn-ghost" @click="close">Cancel</button>

          <button v-if="stepIndex > 0 && modal.step !== 'progress'" class="btn btn-sm" @click="back">
            <i class="fas fa-arrow-left"></i> Back
          </button>

          <button v-if="modal.step === 'credentials'" class="btn btn-sm"
                  :disabled="modal.testing || modal.submitting" @click="testCredentials">
            <span v-if="modal.testing" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fas fa-plug"></i> Test
          </button>

          <button v-if="modal.step === 'provider' || modal.step === 'credentials'"
                  class="btn btn-sm btn-primary" @click="next">
            Next <i class="fas fa-arrow-right"></i>
          </button>

          <button v-if="modal.step === 'server'" class="btn btn-sm btn-primary"
                  :disabled="modal.submitting || modal.keyBusy" @click="create">
            <span v-if="modal.submitting" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fas fa-cloud-arrow-up"></i>
            Create server
          </button>

          <button v-if="modal.step === 'progress'" class="btn btn-sm"
                  :class="job.status === 'ready' ? 'btn-primary' : ''" @click="close">
            <i class="fas" :class="job.status === 'ready' ? 'fa-check' : 'fa-xmark'"></i>
            {{ job.status === 'ready' ? 'Done' : 'Close' }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  state, fmtTime,
  CLOUD_FLOW, CLOUD_JOB_STEPS, EMPTY_CLOUD_JOB,
  cloudProviderById, cloudJobIndex,
  setCloudProvider, cloudNext, cloudBack,
  updateCloudField, updateCloudCredential,
  testCloudCredentials, createCloudServer,
  askDestroyCloudServer, stopCloudPolling, closeModal
} from './useInfra'
import SshKeyField from './SshKeyField.vue'

const revealSecrets = ref(false)

const modal = computed(() => (state.modal?.type === 'cloud' ? state.modal : null))
const form = computed(() => modal.value?.form || {})
const providers = computed(() => state.cloudProviders)
const provider = computed(() => cloudProviderById(modal.value?.providerId))

const job = computed(() => modal.value?.job || EMPTY_CLOUD_JOB)

/**
 * Index of the milestone currently shown.
 *
 * `cloudJobIndex()` answers -2 for a failed job, which would render every step
 * as "not started". On failure the index is derived from the last reported
 * progress instead, so the checklist stops where the provisioning stopped.
 */
const jobIndex = computed(() => {
  const current = job.value
  if (current.status === 'error') {
    const p = Math.min(100, Math.max(0, Number(current.progress) || 0))
    return Math.min(CLOUD_JOB_STEPS.length - 1, Math.floor((p / 100) * CLOUD_JOB_STEPS.length))
  }
  return cloudJobIndex(current.status)
})

const jobTone = computed(() => ({
  ready: 'badge-success',
  error: 'badge-error',
  queued: 'badge-ghost',
  creating: 'badge-info',
  booting: 'badge-info',
  installing_docker: 'badge-info',
  registering: 'badge-info'
}[job.value.status] || 'badge-ghost'))

const stepIndex = computed(() => {
  const ix = CLOUD_FLOW.findIndex(s => s.id === modal.value?.step)
  return ix < 0 ? 0 : ix
})

/** Password fields stay masked unless the operator asks to see them. */
function inputType(field) {
  return field.secret && !revealSecrets.value ? 'password' : 'text'
}

function optionLabel(list, value) {
  const found = (list || []).find(o => o.value === value)
  return found?.label || value || '—'
}

function jobStepIcon(ix) {
  const current = job.value
  if (ix < jobIndex.value) return 'fa-circle-check text-success'
  if (ix > jobIndex.value) return 'fa-circle opacity-30'
  if (current.status === 'error') return 'fa-circle-xmark text-error'
  if (current.status === 'ready') return 'fa-circle-check text-success'
  return 'fa-circle-notch fa-spin text-primary'
}

/* ── wiring ───────────────────────────────────────────────────────────────── */
function chooseProvider(id) {
  setCloudProvider(id)
}

function onField(field, event, prop = 'value') {
  updateCloudField(field, event.target[prop])
}

function onCredential(field, event) {
  updateCloudCredential(field, event.target.value)
}

function next() {
  cloudNext()
}

function back() {
  cloudBack()
}

function testCredentials() {
  testCloudCredentials()
}

function create() {
  createCloudServer()
}

function askDestroy() {
  askDestroyCloudServer(job.value)
}

function close() {
  closeModal()
}

function onKeydown(event) {
  if (event.key !== 'Escape' || !modal.value) return
  // Consume the key: the wizard is the topmost layer while open.
  event.stopPropagation()
  close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  // The dialog can be unmounted with the view while a job is still polling.
  stopCloudPolling()
})
</script>