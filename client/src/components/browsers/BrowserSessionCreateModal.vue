<script setup>
import BrowserFolderPicker from './BrowserFolderPicker.vue'
</script>

<template>
  <!--
    New browser session settings.

    A browser session runs inside its own container, so the folders it may see
    are decided at creation time (they become bind mounts). This dialog makes
    that mapping explicit instead of relying on the backend default:

      Session            name + start URL
      Project folders    whole project | selected folders | no access
      Downloads          session folder (default) | project folder

    The "Mounts inside the browser" block is the confirmation of the mapping:
    it shows the container paths (file:///home/<project>/...) exactly as the
    backend resolves them, including where the downloads will land.
  -->
  <modal close title="New browser session" @close="close">
    <div class="flex flex-col gap-5 md:w-[34rem]">

      <!-- ── Session ──────────────────────────────────────────────────── -->
      <section class="flex flex-col gap-3">
        <h3 class="text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
          Session
        </h3>

        <label class="flex flex-col gap-1">
          <span class="text-xs font-semibold">
            Name
            <span class="text-error" aria-hidden="true">*</span>
          </span>
          <input
            ref="nameInput"
            v-model="form.name"
            type="text"
            class="input input-sm input-bordered w-full"
            placeholder="Invoice hunt"
            aria-required="true"
            @keyup.enter="create"
          />
        </label>

        <label class="flex flex-col gap-1">
          <span class="text-xs font-semibold">Start URL</span>
          <input
            v-model="form.url"
            type="url"
            class="input input-sm input-bordered w-full"
            placeholder="https://example.com"
            @keyup.enter="create"
          />
        </label>
      </section>

      <!-- ── Project folders ─────────────────────────────────────────── -->
      <section class="flex flex-col gap-2">
        <div class="flex items-center gap-2">
          <h3 class="flex-1 text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
            Project folders
          </h3>
          <span
            class="badge badge-sm"
            :class="mounts.length ? 'badge-primary badge-outline' : 'badge-ghost'"
          >
            {{ mounts.length }} mounted
          </span>
        </div>

        <fieldset class="flex flex-col gap-1.5">
          <legend class="sr-only">What can the browser see of this project?</legend>

          <label
            v-for="option in modeOptions"
            :key="option.value"
            class="flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 transition-colors duration-150"
            :class="form.mode === option.value
              ? 'border-primary/50 bg-primary/5'
              : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-200/50'"
          >
            <input
              v-model="form.mode"
              type="radio"
              name="browser-share-mode"
              :value="option.value"
              class="radio radio-xs radio-primary mt-0.5"
            />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold">{{ option.label }}</span>
              <span class="block text-[11px] leading-snug text-base-content/50">
                {{ option.description }}
              </span>
              <span
                v-if="option.path"
                class="mt-0.5 block truncate font-mono text-[10px] text-base-content/40"
                :title="option.path"
              >{{ option.path }}</span>
            </span>
          </label>
        </fieldset>

        <!-- Read-only: applies to every mounted folder -->
        <label
          v-if="form.mode !== 'none'"
          class="flex cursor-pointer items-start gap-2.5 rounded-lg border border-base-content/10 p-2.5 transition-colors duration-150 hover:bg-base-200/50"
        >
          <input v-model="form.readonly" type="checkbox" class="toggle toggle-sm toggle-primary mt-0.5" />
          <span class="min-w-0 flex-1">
            <span class="block text-xs font-semibold">Read-only mounts</span>
            <span class="block text-[11px] leading-snug text-base-content/50">
              The browser can open the folders but cannot change them. Downloads then
              get their own folder instead of being written inside them.
            </span>
          </span>
        </label>

        <!-- Selected folders -->
        <div
          v-if="form.mode === 'selected'"
          class="flex flex-col gap-2 rounded-lg border border-base-content/10 p-2"
        >
          <p
            v-if="!form.folders.length"
            class="flex items-start gap-1.5 rounded-md bg-warning/10 px-2 py-1.5 text-[11px] text-warning"
          >
            <i class="fa-solid fa-triangle-exclamation mt-0.5" aria-hidden="true"></i>
            <span>No folder selected: the browser will not see any project file.</span>
          </p>

          <ul v-else class="flex flex-col gap-1">
            <li
              v-for="folder in form.folders"
              :key="folder"
              class="flex items-center gap-2 rounded-md bg-base-200/70 px-2 py-1"
            >
              <i class="fa-solid fa-folder text-warning text-[11px]" aria-hidden="true"></i>
              <span class="min-w-0 flex-1 truncate font-mono text-[11px]" :title="folder">
                {{ folder }}
              </span>
              <button
                type="button"
                class="btn btn-ghost btn-xs btn-circle text-base-content/40 hover:text-error"
                :aria-label="`Remove folder ${folder}`"
                @click="removeFolder(folder)"
              >
                <i class="fa-solid fa-xmark text-[10px]"></i>
              </button>
            </li>
          </ul>

          <button
            type="button"
            class="btn btn-outline btn-sm justify-start gap-2"
            @click="picker = 'folders'"
          >
            <i class="fa-solid fa-folder-plus"></i>
            Add folders
          </button>
        </div>

        <!-- Resolved mapping: what the browser will actually see -->
        <div
          v-if="mounts.length"
          class="flex flex-col gap-0.5 rounded-lg border border-base-content/10 bg-base-200/40 p-2"
        >
          <span class="text-[10px] font-semibold uppercase tracking-wide text-base-content/40">
            Mounts inside the browser
          </span>
          <code
            v-for="mount in mounts"
            :key="mount.mount"
            class="truncate font-mono text-[10px] text-base-content/60"
            :title="`file://${mount.mount}`"
          >file://{{ mount.mount }}</code>
        </div>
      </section>

      <!-- ── Downloads ───────────────────────────────────────────────── -->
      <section class="flex flex-col gap-2">
        <h3 class="text-[11px] font-semibold uppercase tracking-wide text-base-content/40">
          Downloads
        </h3>

        <fieldset class="flex flex-col gap-1.5">
          <legend class="sr-only">Where are the browser downloads saved?</legend>

          <label
            class="flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 transition-colors duration-150"
            :class="form.downloads === 'default'
              ? 'border-primary/50 bg-primary/5'
              : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-200/50'"
          >
            <input
              v-model="form.downloads"
              type="radio"
              name="browser-downloads-mode"
              value="default"
              class="radio radio-xs radio-primary mt-0.5"
            />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold">Session folder</span>
              <span class="block font-mono text-[10px] text-base-content/50">
                .codx/browser_downloads/&lt;session id&gt;
              </span>
            </span>
          </label>

          <label
            class="flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 transition-colors duration-150"
            :class="[
              form.downloads === 'custom'
                ? 'border-primary/50 bg-primary/5'
                : 'border-base-content/10 hover:border-base-content/20 hover:bg-base-200/50',
              form.mode === 'none' ? 'cursor-not-allowed opacity-50' : ''
            ]"
          >
            <input
              v-model="form.downloads"
              type="radio"
              name="browser-downloads-mode"
              value="custom"
              class="radio radio-xs radio-primary mt-0.5"
              :disabled="form.mode === 'none'"
            />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-semibold">Project folder</span>
              <span class="block text-[11px] leading-snug text-base-content/50">
                {{ form.mode === 'none'
                  ? 'Needs a project folder to be mounted first.'
                  : 'Pick any project folder: downloads become project files.' }}
              </span>
            </span>
          </label>
        </fieldset>

        <div v-if="form.downloads === 'custom'" class="flex items-center gap-2">
          <button
            type="button"
            class="btn btn-sm flex-1 justify-start gap-2 overflow-hidden"
            :aria-label="form.downloadsFolder
              ? `Change downloads folder (${form.downloadsFolder})`
              : 'Choose downloads folder'"
            @click="picker = 'downloads'"
          >
            <i class="fa-solid fa-folder-open flex-shrink-0"></i>
            <span class="truncate font-mono text-[11px]">
              {{ form.downloadsFolder || 'Choose a folder…' }}
            </span>
          </button>
          <button
            v-if="form.downloadsFolder"
            type="button"
            class="btn btn-ghost btn-sm btn-circle text-base-content/50"
            aria-label="Clear downloads folder"
            @click="form.downloadsFolder = ''"
          >
            <i class="fa-solid fa-eraser"></i>
          </button>
        </div>

        <!-- Resolved downloads location -->
        <p
          class="flex items-start gap-1.5 rounded-lg bg-base-200/60 px-2 py-1.5 text-[10px] text-base-content/60"
        >
          <i class="fa-solid fa-hard-drive mt-0.5 flex-shrink-0" aria-hidden="true"></i>
          <span class="min-w-0 break-all">
            <span class="font-mono">{{ downloads.path }}</span>
            <span class="block text-base-content/40">{{ downloads.note }}</span>
          </span>
        </p>
      </section>

      <!-- Error -->
      <p
        v-if="error"
        role="alert"
        class="flex items-start gap-1.5 rounded-lg bg-error/10 px-2.5 py-2 text-[11px] text-error"
      >
        <i class="fa-solid fa-circle-exclamation mt-0.5 flex-shrink-0" aria-hidden="true"></i>
        <span class="min-w-0 break-words">{{ error }}</span>
      </p>
    </div>

    <!-- ── Actions ──────────────────────────────────────────────────── -->
    <template #footer>
      <button type="button" class="btn btn-sm btn-ghost" :disabled="creating" @click="close">
        Cancel
      </button>
      <button
        type="button"
        class="btn btn-sm btn-primary gap-1"
        :disabled="!canCreate"
        @click="create"
      >
        <i
          class="fa-solid"
          :class="creating ? 'fa-spinner animate-spin' : 'fa-plus'"
          aria-hidden="true"
        ></i>
        {{ creating ? 'Creating…' : 'Create session' }}
      </button>
    </template>

    <!--
      The folder browser is teleported to <body>: the dialog box carries an
      `animate-in` transform, which would otherwise become the containing block
      of the picker's `position: fixed` overlay and clip it inside the dialog.
    -->
    <Teleport to="body">
      <BrowserFolderPicker
        v-if="picker"
        :mode="picker === 'downloads' ? 'single' : 'multiple'"
        :model-value="picker === 'downloads'
          ? (form.downloadsFolder ? [form.downloadsFolder] : [])
          : form.folders"
        :title="picker === 'downloads' ? 'Downloads folder' : 'Project folders'"
        @select="onPickerSelect"
        @close="picker = null"
      />
    </Teleport>
  </modal>
</template>

<script>
// Fresh form state. A function (not an object) so every open starts clean even
// when the component instance is reused.
const emptyForm = () => ({
  name: '',
  url: 'http://example.com',
  // `whole` | `selected` | `none` — mirrors share_project + share_folders
  mode: 'whole',
  folders: [],
  readonly: false,
  // `default` | `custom` — mirrors downloads_folder
  downloads: 'default',
  downloadsFolder: ''
})

//: Project folder holding the downloads when no specific folder is chosen.
const DOWNLOADS_FOLDER = '.codx/browser_downloads'

export default {
  name: 'BrowserSessionCreateModal',
  components: { BrowserFolderPicker },
  data() {
    return {
      form: emptyForm(),
      creating: false,
      error: null,
      // Open folder picker: null | 'folders' | 'downloads'
      picker: null
    }
  },
  computed: {
    projectName() {
      return this.$project?.project_name ||
        this.$storex.projects.activeProject?.project_name ||
        'project'
    },
    /** Mirror of the backend rule that builds `/home/<project_name>`. */
    projectFolderName() {
      const name = String(this.projectName || '')
        .replace(/[^A-Za-z0-9._-]+/g, '-')
        .replace(/^[-._]+|[-._]+$/g, '')
      return name || 'project'
    },
    homePath() {
      return `/home/${this.projectFolderName}`
    },
    /** Container mounts the backend will create for the current selection. */
    mounts() {
      if (this.form.mode === 'none') return []
      if (this.form.mode === 'whole') {
        return [{ folder: '', mount: this.homePath }]
      }
      return this.form.folders.map(folder => ({
        folder,
        mount: `${this.homePath}/${folder}`
      }))
    },
    modeOptions() {
      return [
        {
          value: 'whole',
          label: 'Whole project',
          description: 'Every file of the project is visible to the browser.',
          path: this.homePath
        },
        {
          value: 'selected',
          label: 'Selected folders',
          description: 'Mount only the folders the browser needs.',
          path: ''
        },
        {
          value: 'none',
          label: 'No project access',
          description: 'Isolated browser: no project file can be read or written.',
          path: ''
        }
      ]
    },
    /** Project-relative folder receiving the downloads ('' = default). */
    downloadsFolderPath() {
      if (this.form.downloads !== 'custom') return ''
      return this.normalizeFolder(this.form.downloadsFolder)
    },
    /**
     * Where the downloads end up inside the container.
     *
     * Same rule as the backend: the folder is used through an existing mount
     * when it is inside a *writable* one, otherwise it gets its own bind and
     * is exposed at `/downloads`.
     */
    downloads() {
      if (this.form.mode === 'none') {
        return {
          path: '/downloads',
          note: 'Stored in the session folder on the server: no project file is created.'
        }
      }

      const folder = this.downloadsFolderPath || `${DOWNLOADS_FOLDER}/<session id>`
      if (this.form.readonly) {
        return {
          path: '/downloads',
          note: `Saved at ${folder}: the mounted folders are read-only.`
        }
      }

      const covering = this.coveringMount(this.downloadsFolderPath)
      if (!covering) {
        return {
          path: '/downloads',
          note: `Saved at ${folder}: outside the mounted folders.`
        }
      }
      const rest = this.downloadsFolderPath.slice(this.normalizeFolder(covering.folder).length)
      const suffix = rest.replace(/^\/+/, '')
      return {
        path: suffix ? `${covering.mount}/${suffix}` : covering.mount,
        note: 'Saved inside a mounted folder: the files are project files.'
      }
    },
    canCreate() {
      return !!this.form.name.trim() && !this.creating
    }
  },
  methods: {
    normalizeFolder(value) {
      return String(value || '')
        .replace(/\\/g, '/')
        .replace(/\/{2,}/g, '/')
        .replace(/^\/+|\/+$/g, '')
    },
    /** True when *folder* is *parent* or lives inside it. */
    isInside(folder, parent) {
      const path = this.normalizeFolder(folder)
      const base = this.normalizeFolder(parent)
      if (!base) return true
      return path === base || path.startsWith(`${base}/`)
    },
    /** Innermost mount holding *folder* (null when nothing covers it). */
    coveringMount(folder) {
      const path = this.normalizeFolder(folder)
      let best = null
      this.mounts.forEach((mount) => {
        if (!this.isInside(path, mount.folder)) return
        if (!best || this.normalizeFolder(mount.folder).length > this.normalizeFolder(best.folder).length) {
          best = mount
        }
      })
      return best
    },
    removeFolder(folder) {
      this.form.folders = this.form.folders.filter(item => item !== folder)
    },
    /** Merge a picker selection, dropping folders already covered by a parent. */
    mergeFolders(selection) {
      const merged = [...new Set([...this.form.folders, ...selection])]
        .map(folder => this.normalizeFolder(folder))
        .filter(Boolean)
      const kept = merged.filter(folder =>
        !merged.some(other => other !== folder && this.isInside(folder, other))
      )
      this.form.folders = kept.sort((a, b) => a.localeCompare(b))
    },
    onPickerSelect(selection) {
      if (this.picker === 'downloads') {
        const chosen = (selection || [])[0] || ''
        this.form.downloadsFolder = this.normalizeFolder(chosen)
        this.form.downloads = 'custom'
      } else if ((selection || []).includes('')) {
        // Picking the project root is the "whole project" mode
        this.form.mode = 'whole'
        this.form.folders = []
      } else {
        this.mergeFolders(selection || [])
      }
      this.picker = null
    },
    errorMessage(error) {
      return error?.response?.data?.detail ||
        error?.message ||
        'Could not create the browser session'
    },
    async create() {
      if (!this.canCreate) return
      this.creating = true
      this.error = null
      try {
        const session = await this.$storex.browsers.createSession({
          name: this.form.name.trim(),
          initial_url: this.form.url.trim() || null,
          share_project: this.form.mode === 'whole',
          share_folders: this.form.mode === 'selected' ? [...this.form.folders] : [],
          readonly: !!this.form.readonly,
          downloads_folder: this.form.downloads === 'custom'
            ? (this.form.downloadsFolder || null)
            : null
        })
        this.close()
        return session
      } catch (error) {
        console.error('[BrowserSessionCreateModal] Create failed:', error)
        this.error = this.errorMessage(error)
      } finally {
        this.creating = false
      }
    },
    /** ESC / backdrop: an open folder picker closes first, never both. */
    close() {
      if (this.picker) {
        this.picker = null
        return
      }
      this.$storex.browsers.toggleNewSessionForm(false)
    }
  },
  mounted() {
    this.$nextTick(() => this.$refs.nameInput?.focus())
  }
}
</script>