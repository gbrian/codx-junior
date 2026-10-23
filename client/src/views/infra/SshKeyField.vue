<template>
  <!-- ── SSH key pair manager ────────────────────────────────────────────────
       Shared by the host dialog and the cloud wizard: both need a key pair
       BEFORE the machine exists, so the field reads the form of whichever
       dialog is open (`state.modal.form`) instead of taking props.

       The private key never reaches the browser — the API only returns the
       public half plus the server-side path, which is exactly what an operator
       needs to paste into `authorized_keys` or into a provider key store. -->
  <div class="rounded-lg border border-base-300 bg-base-200/60 p-3 space-y-2">
    <!-- header: state + actions -->
    <div class="flex flex-wrap items-center gap-2">
      <i class="fas fa-key text-primary" aria-hidden="true"></i>
      <span class="text-xs font-semibold uppercase tracking-wide opacity-60">SSH key pair</span>

      <span v-if="key" class="badge badge-xs badge-outline font-mono">{{ keyLabel }}</span>
      <span v-if="key" class="badge badge-xs"
            :class="key.source === 'uploaded' ? 'badge-info badge-outline' : 'badge-success badge-outline'">
        {{ key.source }}
      </span>
      <span v-else class="badge badge-xs badge-ghost">none</span>

      <div class="flex-1"></div>

      <label class="sr-only" for="ssh-key-algorithm">Key algorithm</label>
      <select id="ssh-key-algorithm" class="select select-bordered select-xs w-28"
              :value="algorithm" :disabled="busy"
              @change="algorithm = $event.target.value">
        <option v-for="a in SSH_KEY_ALGORITHMS" :key="a.id" :value="a.id">{{ a.label }}</option>
      </select>

      <button class="btn btn-xs" :class="key ? '' : 'btn-primary'"
              :disabled="busy" :title="algorithmHint" @click="generate">
        <span v-if="busy" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fas" :class="key ? 'fa-rotate' : 'fa-wand-magic-sparkles'" aria-hidden="true"></i>
        {{ key ? 'Regenerate' : 'Generate' }}
      </button>

      <button class="btn btn-xs btn-ghost" :disabled="busy" @click="pickFile">
        <i class="fas fa-upload" aria-hidden="true"></i> Upload
      </button>
      <!-- Accepts a private key (PEM / OpenSSH) or the optional .pub companion. -->
      <input ref="fileEl" type="file" class="hidden"
             accept=".pem,.key,.pub,text/plain,application/x-pem-file,application/octet-stream"
             @change="onFile" />
    </div>

    <!-- reuse an existing pair (keys are global, not host scoped) -->
    <div v-if="state.sshKeys.length" class="flex items-center gap-2">
      <label class="text-[11px] opacity-60 shrink-0" for="ssh-key-select">Use existing</label>
      <select id="ssh-key-select" class="select select-bordered select-xs grow max-w-72 font-mono"
              :value="form.ssh_key_id || ''" :disabled="busy"
              @change="selectKey($event.target.value)">
        <option value="">— none —</option>
        <option v-for="k in state.sshKeys" :key="k.id" :value="k.id">
          {{ k.name }} · {{ k.algorithm }}
        </option>
      </select>
    </div>

    <!-- detail of the selected pair -->
    <template v-if="key">
      <p class="text-[11px] opacity-60 font-mono break-all">
        {{ key.fingerprint || 'fingerprint not reported by the API' }}
      </p>
      <p class="text-[11px] opacity-50">
        Private key:
        <code class="font-mono">{{ key.private_key_file || 'stored server-side by codx-junior' }}</code>
      </p>

      <div class="flex flex-wrap items-center gap-2">
        <button class="btn btn-xs btn-ghost" @click="showPublic = !showPublic">
          <i class="fas" :class="showPublic ? 'fa-eye-slash' : 'fa-eye'" aria-hidden="true"></i>
          {{ showPublic ? 'Hide' : 'Show' }} public key
        </button>
        <button class="btn btn-xs btn-ghost" @click="copy">
          <i class="fas fa-copy" aria-hidden="true"></i> Copy
        </button>
        <button class="btn btn-xs btn-ghost" :disabled="busy" @click="download">
          <i class="fas fa-download" aria-hidden="true"></i> {{ publicFileName }}
        </button>

        <div class="flex-1"></div>

        <!-- Two-step confirm on purpose: `confirm()` would replace
             `state.modal` and destroy the form being edited. -->
        <template v-if="!confirmingDelete">
          <button class="btn btn-xs btn-ghost text-error" :disabled="busy" @click="confirmingDelete = true">
            <i class="fas fa-trash-can" aria-hidden="true"></i> Delete key
          </button>
        </template>
        <template v-else>
          <span class="text-[11px] text-error">Delete this key pair?</span>
          <button class="btn btn-xs btn-error" :disabled="busy" @click="remove">Yes, delete</button>
          <button class="btn btn-xs btn-ghost" @click="confirmingDelete = false">Cancel</button>
        </template>
      </div>

      <pre v-if="showPublic && key.public_key"
           class="p-2 rounded-lg bg-base-300 text-[11px] font-mono whitespace-pre-wrap break-all">{{ key.public_key }}</pre>
      <p v-else-if="!key.public_key" class="text-[11px] opacity-50">
        The API did not return the public key text. Download it with the button above, or read it on the
        server:
        <code class="font-mono">{{ key.public_key_file || (key.private_key_file ? key.private_key_file + '.pub' : '~/.ssh/id_*.pub') }}</code>
      </p>

      <p class="text-[11px] opacity-50">
        Append this line to <code class="font-mono">~/.ssh/authorized_keys</code> on the target
        machine — cloud servers get it injected automatically during provisioning.
      </p>
      <p class="text-[11px] opacity-40">
        Replacing the pair (<b>Regenerate</b> / <b>Upload</b>) points this host at the new key; the
        previous pair stays on disk for any other host still using it.
      </p>
    </template>

    <p v-else class="text-[11px] opacity-50">
      Generate a new pair or upload an existing <b>private</b> key. The private half stays on the
      codx-junior server; only the public key is ever shown here.
    </p>

    <div v-if="modal.keyError" class="alert alert-error py-1.5" role="alert">
      <i class="fas fa-circle-xmark" aria-hidden="true"></i>
      <span class="text-xs">{{ modal.keyError }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  state, SSH_KEY_ALGORITHMS, sshKeyById, generateSshKey, uploadSshKey,
  setSshKey, deleteSshKey, copyPublicKey, downloadPublicKey
} from './useInfra'

const fileEl = ref(null)
const algorithm = ref('ed25519')
const showPublic = ref(false)
const confirmingDelete = ref(false)

/** The dialog (host or cloud) that currently owns the key. */
const modal = computed(() => (
  ['host', 'cloud'].includes(state.modal?.type) ? state.modal : null
))
const form = computed(() => modal.value?.form || {})
const key = computed(() => sshKeyById(form.value.ssh_key_id))
const busy = computed(() => !!modal.value?.keyBusy)

const keyLabel = computed(() => {
  const k = key.value
  if (!k) return ''
  return [k.algorithm, k.bits].filter(Boolean).join(' ')
})

const algorithmHint = computed(
  () => SSH_KEY_ALGORITHMS.find(a => a.id === algorithm.value)?.desc || ''
)

const publicFileName = computed(() => {
  const base = key.value?.name || `id_${key.value?.algorithm || 'ed25519'}`
  return `${String(base).replace(/[^\w.-]+/g, '_')}.pub`
})

function generate() {
  showPublic.value = false
  confirmingDelete.value = false
  generateSshKey({ algorithm: algorithm.value })
}

function pickFile() {
  fileEl.value?.click()
}

async function onFile(event) {
  const file = event.target.files?.[0]
  // Reset so picking the same file twice still fires `change`.
  event.target.value = ''
  if (!file) return
  confirmingDelete.value = false
  const created = await uploadSshKey({ privateFile: file })
  if (created?.public_key) showPublic.value = true
}

function selectKey(keyId) {
  confirmingDelete.value = false
  showPublic.value = false
  setSshKey(keyId)
}

function copy() {
  copyPublicKey(key.value)
}

function download() {
  downloadPublicKey(key.value)
}

async function remove() {
  const id = key.value?.id
  confirmingDelete.value = false
  await deleteSshKey(id)
}
</script>