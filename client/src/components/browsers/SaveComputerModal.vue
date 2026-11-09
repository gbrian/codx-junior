<script>
/**
 * Save a running desktop to the project computer library.
 *
 * The backend commits the container filesystem, optionally archives the
 * bind-mounted desktop home/profile, and captures a preview screenshot.  Other
 * users of the project can then start a new session from the saved entry.
 */
export default {
  name: 'SaveComputerModal',
  props: {
    session: { type: Object, required: true }
  },
  emits: ['close', 'saved'],
  data() {
    return {
      name: this.session?.name || 'Saved computer',
      description: '',
      includeProfile: false,
      saving: false,
      error: null
    }
  },
  computed: {
    isKasm() {
      return this.session?.live_view === 'kasmvnc'
    },
    canSave() {
      return this.name.trim().length > 0 && !this.saving
    }
  },
  methods: {
    async save() {
      if (!this.canSave) return
      this.saving = true
      this.error = null
      try {
        const saved = await this.$storex.api.computers.saveComputer(this.session.id, {
          name: this.name.trim(),
          description: this.description.trim() || null,
          include_profile: !!this.includeProfile
        })
        this.$storex.ui.addNotification({
          text: `Saved "${saved?.name || this.name.trim()}" to the computer library`,
          type: 'success'
        })
        this.$emit('saved', saved)
        this.$emit('close')
      } catch (error) {
        this.error = error?.response?.data?.detail || error?.message || 'Could not save the computer'
      } finally {
        this.saving = false
      }
    }
  }
}
</script>

<template>
  <modal close title="Save computer to library" @close="$emit('close')">
    <div class="flex flex-col gap-3 md:w-[30rem]">
      <div class="rounded-lg bg-base-200/60 p-2.5 text-[11px] leading-snug text-base-content/60">
        <p>
          The container is committed to a Docker image and added to this
          project's saved-computer library. Project users can start a new
          session from it.
        </p>
        <p class="mt-1 text-warning">
          <i class="fa-solid fa-triangle-exclamation mr-1"></i>
          <span v-if="isKasm">
            Kasmweb's container home is included in the image, so browser
            profiles, cookies and credentials in it are shared with project
            users.
          </span>
          <span v-else>
            Only changes outside the bind-mounted home are in the image. Tick
            the profile option to share desktop settings too; profiles can
            contain logins, cookies and SSH keys.
          </span>
        </p>
      </div>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold">Name <span class="text-error">*</span></span>
        <input
          v-model="name"
          type="text"
          class="input input-sm input-bordered w-full"
          placeholder="e.g. Android SDK desktop"
          @keyup.enter="save"
        />
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-xs font-semibold">Description</span>
        <textarea
          v-model="description"
          class="textarea textarea-bordered textarea-sm w-full"
          rows="2"
          placeholder="What is installed or configured in this computer?"
        ></textarea>
      </label>

      <label v-if="!isKasm" class="flex items-start gap-2 rounded-lg border border-base-content/10 p-2.5">
        <input v-model="includeProfile" type="checkbox" class="checkbox checkbox-sm mt-0.5" />
        <span class="min-w-0 text-[11px] leading-snug">
          <span class="font-semibold">Include home/profile data</span>
          <span class="block text-base-content/50">
            Archives the desktop profile (excluding caches) and restores it in
            new sessions. May contain credentials, cookies and keys.
          </span>
        </span>
      </label>

      <p v-if="error" class="rounded-lg bg-error/10 px-2.5 py-2 text-[11px] text-error">
        <i class="fa-solid fa-circle-exclamation mr-1"></i>{{ error }}
      </p>

      <div class="flex justify-end gap-2">
        <button class="btn btn-sm btn-ghost" :disabled="saving" @click="$emit('close')">Cancel</button>
        <button class="btn btn-sm btn-primary" :disabled="!canSave" @click="save">
          <span v-if="saving" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-solid fa-floppy-disk"></i>
          {{ saving ? 'Committing…' : 'Save computer' }}
        </button>
      </div>
    </div>
  </modal>
</template>
