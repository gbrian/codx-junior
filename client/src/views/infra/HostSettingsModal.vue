<template>
  <!-- ── Host definition dialog ──────────────────────────────────────────────
       Creates / edits a Docker host: identity, SSH connection (host, port,
       user and the managed key pair), the Docker endpoint + TLS certificates
       and free-form notes.
       Teleported to <body> so it is sized by the viewport, not by the
       dockview panel that hosts InfraView. -->
  <Teleport to="body">
    <div v-if="modal" class="fixed inset-0 z-[85] flex items-center justify-center p-2 sm:p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close"></div>

      <div role="dialog" aria-modal="true" aria-labelledby="host-modal-title"
           class="relative z-10 flex flex-col w-full max-w-2xl max-h-[92vh] bg-base-100 border border-base-300 rounded-xl shadow-2xl overflow-hidden">

        <!-- ── Header ─────────────────────────────────────────────────────── -->
        <header class="shrink-0 flex items-start gap-2 px-4 py-3 border-b border-base-300 bg-base-200">
          <i class="fas fa-server text-primary mt-1"></i>
          <div class="min-w-0 grow">
            <h3 id="host-modal-title" class="font-bold leading-tight">
              {{ isEdit ? 'Host settings' : 'New Docker host' }}
            </h3>
            <p class="text-xs opacity-60">
              {{ isEdit
                ? `Connection details for ${form.name || 'this host'}`
                : 'Add a machine running a Docker daemon — the local socket or a remote over SSH.' }}
            </p>
          </div>
          <span class="badge badge-sm shrink-0" :class="form.kind === 'local' ? 'badge-ghost' : 'badge-outline'">
            {{ form.kind === 'local' ? 'local' : 'ssh' }}
          </span>
          <button class="btn btn-sm btn-ghost btn-square shrink-0"
                  aria-label="Close host settings" title="Close (Esc)" @click="close">
            <i class="fas fa-xmark"></i>
          </button>
        </header>

        <!-- ── Form ───────────────────────────────────────────────────────── -->
        <div class="grow min-h-0 overflow-auto px-4 py-4 space-y-5">

          <!-- identity -->
          <fieldset class="space-y-3">
            <legend class="text-xs font-semibold uppercase tracking-wide opacity-50 mb-1">Identity</legend>

            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="label label-text text-xs" for="host-name">Name *</label>
                <input id="host-name" type="text" class="input input-bordered input-sm w-full"
                       :class="{ 'input-error': errors.name }"
                       placeholder="e.g. build-server"
                       :value="form.name"
                       @input="onField('name', $event)" />
                <p v-if="errors.name" class="text-error text-xs mt-1">{{ errors.name }}</p>
              </div>

              <div>
                <label class="label label-text text-xs" for="host-kind">Connection</label>
                <select id="host-kind" class="select select-bordered select-sm w-full"
                        :value="form.kind" @change="onKind($event)">
                  <option value="local">Local socket (this machine)</option>
                  <option value="ssh">Remote over SSH</option>
                </select>
              </div>
            </div>

            <label class="label cursor-pointer justify-start gap-2 py-0">
              <input type="checkbox" class="toggle toggle-sm toggle-primary"
                     :checked="form.enabled"
                     @change="onField('enabled', $event, 'checked')" />
              <span class="label-text text-xs">Enabled — list this host in the selector</span>
            </label>
          </fieldset>

          <!-- ssh connection -->
          <fieldset v-if="form.kind === 'ssh'" class="space-y-3">
            <legend class="text-xs font-semibold uppercase tracking-wide opacity-50 mb-1">SSH connection</legend>

            <div class="grid gap-3 sm:grid-cols-4">
              <div class="sm:col-span-2">
                <label class="label label-text text-xs" for="host-hostname">Host (name or IP) *</label>
                <input id="host-hostname" type="text" class="input input-bordered input-sm w-full"
                       :class="{ 'input-error': errors.hostname }"
                       placeholder="10.0.0.12"
                       :value="form.hostname"
                       @input="onField('hostname', $event)" />
                <p v-if="errors.hostname" class="text-error text-xs mt-1">{{ errors.hostname }}</p>
              </div>

              <div>
                <label class="label label-text text-xs" for="host-ssh-port">SSH port</label>
                <input id="host-ssh-port" type="number" min="1" max="65535"
                       class="input input-bordered input-sm w-full"
                       :class="{ 'input-error': errors.ssh_port }"
                       :value="form.ssh_port"
                       @input="onField('ssh_port', $event)" />
                <p v-if="errors.ssh_port" class="text-error text-xs mt-1">{{ errors.ssh_port }}</p>
              </div>

              <div>
                <label class="label label-text text-xs" for="host-ssh-user">SSH user</label>
                <input id="host-ssh-user" type="text" class="input input-bordered input-sm w-full"
                       placeholder="root"
                       :value="form.ssh_user"
                       @input="onField('ssh_user', $event)" />
              </div>
            </div>

            <!-- key pair: generate / upload / reuse, show the public half,
                 replace it at any time (the old pair is left untouched). -->
            <SshKeyField />
            <p v-if="errors.ssh_key_id" class="text-error text-xs -mt-1">{{ errors.ssh_key_id }}</p>

            <!-- advanced: a key file that already lives on the codx-junior host -->
            <details class="text-xs">
              <summary class="cursor-pointer opacity-60 select-none">
                Advanced: use a key file already present on the server
              </summary>
              <div class="mt-2">
                <label class="label label-text text-xs" for="host-ssh-key">Private key path</label>
                <input id="host-ssh-key" type="text" class="input input-bordered input-sm w-full font-mono text-xs"
                       placeholder="/home/codx/.ssh/id_ed25519"
                       :value="form.ssh_key_file"
                       @input="onField('ssh_key_file', $event)" />
                <p class="text-xs opacity-50 mt-1">
                  Only used when no managed key pair is selected above. Leave empty to let codx-junior
                  use the default <code class="font-mono">~/.ssh/id_*</code> of its own user.
                </p>
              </div>
            </details>
          </fieldset>

          <!-- docker endpoint -->
          <fieldset class="space-y-3">
            <legend class="text-xs font-semibold uppercase tracking-wide opacity-50 mb-1">Docker endpoint</legend>

            <div>
              <label class="label label-text text-xs" for="host-endpoint">Endpoint *</label>
              <input id="host-endpoint" type="text" class="input input-bordered input-sm w-full font-mono text-xs"
                     :class="{ 'input-error': errors.endpoint }"
                     placeholder="unix:///var/run/docker.sock"
                     :value="form.endpoint"
                     @input="onField('endpoint', $event)" />
              <p v-if="errors.endpoint" class="text-error text-xs mt-1">{{ errors.endpoint }}</p>
              <p class="text-xs opacity-50 mt-1">
                <code class="font-mono">unix:///var/run/docker.sock</code> ·
                <code class="font-mono">ssh://user@host:22</code> ·
                <code class="font-mono">tcp://host:2376</code>
              </p>
            </div>

            <label class="label cursor-pointer justify-start gap-2 py-0">
              <input type="checkbox" class="toggle toggle-sm toggle-primary"
                     :checked="form.tls_verify"
                     @change="onField('tls_verify', $event, 'checked')" />
              <span class="label-text text-xs">Verify TLS certificates (required for <code class="font-mono">tcp://</code>)</span>
            </label>

            <div v-if="form.tls_verify" class="grid gap-3 sm:grid-cols-3">
              <div>
                <label class="label label-text text-xs" for="host-tls-ca">CA cert</label>
                <input id="host-tls-ca" type="text" class="input input-bordered input-xs w-full font-mono"
                       placeholder="/etc/docker/ca.pem"
                       :value="form.tls_ca_file" @input="onField('tls_ca_file', $event)" />
              </div>
              <div>
                <label class="label label-text text-xs" for="host-tls-cert">Client cert</label>
                <input id="host-tls-cert" type="text" class="input input-bordered input-xs w-full font-mono"
                       placeholder="/etc/docker/cert.pem"
                       :value="form.tls_cert_file" @input="onField('tls_cert_file', $event)" />
              </div>
              <div>
                <label class="label label-text text-xs" for="host-tls-key">Client key</label>
                <input id="host-tls-key" type="text" class="input input-bordered input-xs w-full font-mono"
                       placeholder="/etc/docker/key.pem"
                       :value="form.tls_key_file" @input="onField('tls_key_file', $event)" />
              </div>
            </div>
          </fieldset>

          <!-- notes -->
          <fieldset>
            <label class="label label-text text-xs" for="host-notes">Notes</label>
            <textarea id="host-notes" class="textarea textarea-bordered textarea-sm w-full"
                      rows="2" placeholder="Where this host lives, who owns it…"
                      :value="form.notes" @input="onField('notes', $event)"></textarea>
          </fieldset>

          <!-- test result -->
          <div v-if="modal.testResult" class="alert py-2" role="status"
               :class="modal.testResult.ok ? 'alert-success' : 'alert-error'">
            <i class="fas" :class="modal.testResult.ok ? 'fa-circle-check' : 'fa-circle-xmark'"></i>
            <div class="text-xs">
              <p class="font-semibold">{{ modal.testResult.text }}</p>
              <p v-if="testDetails" class="opacity-70 font-mono">{{ testDetails }}</p>
            </div>
          </div>
        </div>

        <!-- ── Footer ─────────────────────────────────────────────────────── -->
        <footer class="shrink-0 px-4 py-3 border-t border-base-300 bg-base-200 flex flex-wrap items-center gap-2">
          <button v-if="isEdit && !form.is_local" class="btn btn-sm btn-ghost text-error"
                  title="Remove this host" @click="askRemove">
            <i class="fas fa-trash-can"></i> Remove
          </button>
          <div class="flex-1"></div>

          <button class="btn btn-sm btn-ghost" @click="close">Cancel</button>
          <button class="btn btn-sm" :disabled="busy" @click="testConnection">
            <span v-if="modal.testing" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fas fa-plug"></i>
            Test
          </button>
          <button class="btn btn-sm btn-primary" :disabled="busy" @click="save">
            <span v-if="modal.submitting" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fas fa-floppy-disk"></i>
            {{ isEdit ? 'Save host' : 'Add host' }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue'
import {
  state, closeModal, updateHostField, setHostKind,
  submitHost, testHostConnection, askRemoveHost
} from './useInfra'
import SshKeyField from './SshKeyField.vue'

/* The dialog lives in the shared store (`state.modal.type === 'host'`) so any
   component can open it without prop plumbing. */
const modal = computed(() => (state.modal?.type === 'host' ? state.modal : null))
const form = computed(() => modal.value?.form || {})
const errors = computed(() => modal.value?.errors || {})
const isEdit = computed(() => modal.value?.mode === 'edit')
const busy = computed(() => !!(modal.value?.submitting || modal.value?.testing || modal.value?.keyBusy))

const testDetails = computed(() => {
  const result = modal.value?.testResult
  if (!result?.ok) return ''
  return [result.engine ? `engine ${result.engine}` : '', result.os || ''].filter(Boolean).join(' · ')
})

/** Reads either `event.target.value` or a checkbox-style property. */
function onField(field, event, prop = 'value') {
  updateHostField(field, event.target[prop])
}

function onKind(event) {
  setHostKind(event.target.value)
}

function close() {
  closeModal()
}

function save() {
  submitHost()
}

function testConnection() {
  testHostConnection()
}

function askRemove() {
  askRemoveHost(state.hosts.find(h => h.id === form.value.id))
}

function onKeydown(event) {
  if (event.key !== 'Escape' || !modal.value) return
  // The host dialog is the topmost layer while open: consume the key.
  event.stopPropagation()
  close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>