<script>
/**
 * Desktop image library.
 *
 * Lets the user pick a LinuxServer.io webtop flavour or a Kasmweb desktop/app
 * without remembering Docker tags.  The catalog comes from
 * `GET /api/computers/images`; tags for the selected repository come from
 * `GET /api/computers/images/tags` (Docker Hub / LinuxServer API, cached).
 *
 * A custom image reference is still possible for advanced users; the backend
 * then falls back to screenshot-only viewing.
 */
export default {
  name: 'ComputerImageLibrary',
  props: {
    kind: { type: String, default: 'linux' },
    modelValue: { type: String, default: '' }
  },
  emits: ['close', 'select'],
  data() {
    return {
      provider: String(this.modelValue || '').trim().toLowerCase().startsWith('codx-saved/')
        ? 'saved'
        : (String(this.modelValue || '').trim().toLowerCase().startsWith('kasmweb/')
          ? 'kasmweb'
          : 'linuxserver'),
      query: '',
      category: '',
      images: [],
      loading: false,
      error: null,
      selected: null,
      tags: [],
      tagsLoading: false,
      selectedTag: '',
      customImage: '',
      refresh: false,
      searchTimer: null,
      savedPreviewUrls: {},
      // Guards against a slow provider response overwriting a newer tab.
      loadToken: 0,
      providerCounts: { linuxserver: 0, kasmweb: 0, saved: 0 }
    }
  },
  computed: {
    categories() {
      return [...new Set(this.images.map(image => image.category).filter(Boolean))].sort()
    },
    visibleImages() {
      const term = this.query.trim().toLowerCase()
      const category = this.category
      return this.images.filter(image => {
        if (category && image.category !== category) return false
        if (!term) return true
        return [image.name, image.repository, image.description, image.category, ...(image.tags || [])]
          .some(value => String(value || '').toLowerCase().includes(term))
      })
    },
    selectedImage() {
      if (!this.selected) return ''
      if (this.selected.provider === 'saved') return this.selected.image
      return this.selectedTag
        ? `${this.selected.repository}:${this.selectedTag}`
        : this.selected.image
    },
    providerOptions() {
      return [
        {
          value: 'linuxserver',
          label: 'LinuxServer.io',
          icon: 'fa-server',
          description: 'webtop · Selkies · port 3000'
        },
        {
          value: 'kasmweb',
          label: 'Kasmweb',
          icon: 'fa-cubes',
          description: 'KasmVNC · port 6901 · desktops & apps'
        },
        {
          value: 'saved',
          label: 'Saved',
          icon: 'fa-bookmark',
          description: 'Project snapshots · committed containers'
        }
      ]
    }
  },
  watch: {
    provider: {
      immediate: true,
      handler() {
        this.selected = null
        this.selectedTag = ''
        this.tags = []
        this.category = ''
        this.loadImages()
      }
    },
    query() {
      // The API supports search, but filtering locally keeps typing instant
      // and avoids a request per keystroke.
      this.category = ''
    }
  },
  beforeUnmount() {
    if (this.searchTimer) window.clearTimeout(this.searchTimer)
    this.revokeSavedPreviews()
  },
  methods: {
    async loadImages() {
      const token = ++this.loadToken
      this.loading = true
      this.error = null
      try {
        if (this.provider === 'saved') {
          await this.loadSavedComputers(token)
        } else {
          this.revokeSavedPreviews()
          const response = await this.$storex.api.computers.images({
            provider: this.provider,
            kind: this.kind,
            refresh: this.refresh
          })
          if (token !== this.loadToken) return
          this.images = response?.images || []
        }
        if (token !== this.loadToken) return
        this.providerCounts = {
          linuxserver: this.provider === 'linuxserver'
            ? this.images.length
            : this.providerCounts.linuxserver,
          kasmweb: this.provider === 'kasmweb'
            ? this.images.length
            : this.providerCounts.kasmweb,
          saved: this.provider === 'saved'
            ? this.images.length
            : this.providerCounts.saved
        }
        if (this.selected) {
          const current = this.images.find(image => image.id === this.selected.id)
          if (current) this.selected = current
        } else if (this.modelValue) {
          const current = this.images.find(image =>
            image.image === this.modelValue ||
            `${image.repository}:${image.tag}` === this.modelValue
          )
          if (current) {
            this.selected = current
            this.selectedTag = current.tag || current.default_tag || ''
            this.loadTags()
          }
        }
      } catch (error) {
        if (token !== this.loadToken) return
        this.error = error?.response?.data?.detail || error.message || 'Could not load the image library'
        this.images = []
      } finally {
        if (token === this.loadToken) {
          this.loading = false
          this.refresh = false
        }
      }
    },
    async loadSavedComputers(token) {
      this.revokeSavedPreviews()
      const response = await this.$storex.api.computers.savedComputers()
      if (token !== this.loadToken) return
      const computers = response?.computers || []
      this.images = computers.map(item => ({
        id: `saved:${item.id}`,
        library_item_id: item.id,
        provider: 'saved',
        image_provider: item.provider,
        repository: item.image,
        image: item.image,
        tag: 'saved',
        default_tag: 'saved',
        name: item.name,
        description: item.description || `Saved${item.created_by ? ` by ${item.created_by}` : ''} from ${item.source_session_name || 'a desktop'}`,
        category: 'Saved computers',
        icon_url: null,
        screenshot_url: null,
        docs_url: null,
        live_view: item.live_view,
        live_port: item.live_port,
        live_scheme: item.live_scheme,
        strip_prefix: item.strip_prefix,
        control: item.control,
        viewer_user: item.viewer_user,
        tags: [item.provider, item.created_by, item.source_session_name].filter(Boolean),
        has_preview: item.has_preview,
        created_by: item.created_by,
        created_at: item.created_at,
        image_size_bytes: item.image_size_bytes,
        profile_size_bytes: item.profile_size_bytes,
        include_profile: item.include_profile,
        source_image: item.base_image,
        saved: item
      }))
      // Fetch previews in the background so the saved list paints immediately.
      this.loadSavedPreviews(token)
    },
    async loadSavedPreviews(token) {
      const cards = this.images.filter(image => image.provider === 'saved' && image.has_preview)
      await Promise.allSettled(cards.map(async (image) => {
        try {
          const blob = await this.$storex.api.computers.savedComputerPreview(image.library_item_id)
          if (token !== this.loadToken || this.provider !== 'saved' || !this.images.some(entry => entry.id === image.id)) return
          const url = URL.createObjectURL(blob)
          this.savedPreviewUrls[image.id] = url
          image.screenshot_url = url
        } catch (error) {
          // No preview is fine; the card keeps the generic desktop icon.
        }
      }))
    },
    revokeSavedPreviews() {
      Object.values(this.savedPreviewUrls).forEach(url => URL.revokeObjectURL(url))
      this.savedPreviewUrls = {}
    },
    async deleteSelectedSaved() {
      if (!this.selected?.library_item_id) return
      const name = this.selected.name
      if (!window.confirm(`Delete the saved computer "${name}" and its Docker image?`)) return
      try {
        await this.$storex.api.computers.deleteSavedComputer(this.selected.library_item_id)
        const preview = this.savedPreviewUrls[this.selected.id]
        if (preview) URL.revokeObjectURL(preview)
        delete this.savedPreviewUrls[this.selected.id]
        this.images = this.images.filter(image => image.id !== this.selected.id)
        this.selected = null
        this.providerCounts.saved = this.images.length
        this.$storex.ui.addNotification({ text: `Deleted saved computer "${name}"`, type: 'success' })
      } catch (error) {
        this.$storex.ui.addNotification({
          text: error?.response?.data?.detail || 'Could not delete the saved computer',
          type: 'error'
        })
      }
    },
    async selectImage(image) {
      this.selected = image
      this.selectedTag = image.default_tag || image.tag || ''
      await this.loadTags()
    },
    async loadTags(force = false) {
      if (!this.selected) return
      if (this.selected.provider === 'saved') {
        this.tags = []
        this.tagsLoading = false
        return
      }
      if (this.selected.provider === 'linuxserver') {
        // LinuxServer webtop tags are desktop flavours, not versions; the grid
        // already lists one card per flavour, so there is no extra tag choice.
        this.tags = []
        this.tagsLoading = false
        return
      }
      this.tagsLoading = true
      this.tags = []
      try {
        const response = await this.$storex.api.computers.imageTags(
          this.selected.provider,
          this.selected.repository,
          force
        )
        this.tags = response?.tags || []
        if (this.tags.length && !this.tags.some(tag => tag.name === this.selectedTag)) {
          this.selectedTag = this.tags[0].name
        }
      } catch (error) {
        // Keep the catalog default tag; the image is still selectable.
        this.tags = []
      } finally {
        this.tagsLoading = false
      }
    },
    useSelected() {
      if (!this.selected) return
      const payload = {
        ...this.selected,
        tag: this.selectedTag || this.selected.default_tag,
        image: this.selectedImage
      }
      if (payload.provider === 'saved') {
        // The preview object URL is revoked when this modal unmounts; the
        // create dialog falls back to the generic desktop icon.
        payload.screenshot_url = null
      }
      this.$emit('select', payload)
      this.$emit('close')
    },
    useCustom() {
      const image = this.customImage.trim()
      if (!image) return
      this.$emit('select', {
        id: `custom:${image}`,
        provider: 'custom',
        repository: image.split(':')[0],
        image,
        tag: image.split(':')[1] || '',
        name: image,
        description: 'Custom image (screenshot viewing; the X11 agent still works)',
        category: 'Custom',
        live_view: 'screenshot',
        live_port: null,
        live_scheme: 'http',
        strip_prefix: false,
        control: 'docker',
        viewer_user: null
      })
      this.$emit('close')
    },
    refreshCatalog() {
      this.refresh = true
      this.loadImages()
    },
    providerIcon(provider) {
      if (provider === 'saved') return 'fa-bookmark'
      return provider === 'kasmweb' ? 'fa-cubes' : 'fa-server'
    },
    providerLabel(provider) {
      if (provider === 'saved') return 'Saved'
      return provider === 'kasmweb' ? 'Kasmweb' : 'LinuxServer.io'
    },
    imagePreview(image) {
      return image.screenshot_url || image.icon_url || ''
    },
    formatBytes(value) {
      if (!value) return ''
      if (value >= 1024 ** 3) return `${(value / (1024 ** 3)).toFixed(1)} GB`
      if (value >= 1024 ** 2) return `${(value / (1024 ** 2)).toFixed(0)} MB`
      return `${(value / 1024).toFixed(0)} KB`
    },
    formatCount(value) {
      if (!value) return ''
      if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
      if (value >= 1000) return `${(value / 1000).toFixed(0)}k`
      return String(value)
    }
  }
}
</script>

<template>
  <modal close title="Desktop image library" @close="$emit('close')">
    <div class="flex flex-col gap-3 md:w-[42rem] max-h-[78vh]">
      <!-- Provider tabs + search -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="join">
          <button
            v-for="option in providerOptions"
            :key="option.value"
            type="button"
            class="btn btn-sm join-item"
            :class="provider === option.value ? 'btn-primary' : 'btn-ghost'"
            @click="provider = option.value"
          >
            <i class="fa-solid" :class="option.icon"></i>
            {{ option.label }}
            <span v-if="providerCounts[option.value]" class="badge badge-xs">
              {{ providerCounts[option.value] }}
            </span>
          </button>
        </div>
        <label class="input input-sm input-bordered flex items-center gap-2 flex-1 min-w-[12rem]">
          <i class="fa-solid fa-magnifying-glass text-base-content/40"></i>
          <input
            v-model="query"
            type="search"
            class="grow"
            :placeholder="provider === 'saved'
              ? 'Search saved computers…'
              : 'Search Ubuntu, Kali, VS Code, Firefox…'"
          />
        </label>
        <button
          class="btn btn-sm btn-ghost btn-square"
          :title="provider === 'saved' ? 'Reload saved computers' : 'Reload from upstream'"
          :disabled="loading"
          @click="refreshCatalog"
        >
          <i class="fa-solid fa-arrows-rotate" :class="loading ? 'animate-spin' : ''"></i>
        </button>
      </div>

      <div class="flex items-center gap-1.5 flex-wrap">
        <button
          type="button"
          class="btn btn-xs"
          :class="!category ? 'btn-primary' : 'btn-ghost'"
          @click="category = ''"
        >All</button>
        <button
          v-for="item in categories"
          :key="item"
          type="button"
          class="btn btn-xs"
          :class="category === item ? 'btn-primary' : 'btn-ghost'"
          @click="category = category === item ? '' : item"
        >{{ item }}</button>
        <span class="flex-1"></span>
        <span class="text-[11px] text-base-content/40">
          {{ providerOptions.find(option => option.value === provider)?.description }}
        </span>
      </div>

      <p v-if="error" class="rounded-lg bg-error/10 px-2.5 py-2 text-[11px] text-error">
        <i class="fa-solid fa-circle-exclamation mr-1"></i>{{ error }}
      </p>

      <!-- Catalog grid -->
      <div class="flex-1 min-h-[16rem] overflow-y-auto pr-1">
        <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          <div v-for="n in 6" :key="n" class="h-36 rounded-xl bg-base-200 animate-pulse"></div>
        </div>
        <div v-else-if="!visibleImages.length" class="flex flex-col items-center justify-center py-14 text-base-content/40">
          <i
            class="fa-regular text-3xl mb-2"
            :class="provider === 'saved' ? 'fa-bookmark' : 'fa-images'"
          ></i>
          <p class="text-sm">{{ provider === 'saved' ? 'No saved computers yet.' : 'No image matches this search.' }}</p>
          <p v-if="provider === 'saved'" class="mt-1 text-[11px]">
            Start a Linux desktop, customize it, then use Save to library.
          </p>
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          <button
            v-for="image in visibleImages"
            :key="image.id"
            type="button"
            class="group relative flex flex-col text-left rounded-xl border overflow-hidden transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            :class="selected?.id === image.id
              ? 'border-primary bg-primary/5 ring-1 ring-primary'
              : 'border-base-content/10 bg-base-100 hover:border-primary/40 hover:bg-base-200/50'"
            @click="selectImage(image)"
          >
            <div class="relative h-24 w-full overflow-hidden bg-base-300/40">
              <img
                v-if="imagePreview(image)"
                :src="imagePreview(image)"
                :alt="image.name"
                loading="lazy"
                class="h-full w-full transition-transform duration-300 group-hover:scale-105"
                :class="image.provider === 'kasmweb' || image.provider === 'saved' ? 'object-cover' : 'object-contain p-4'"
                @error="$event.target.style.display = 'none'"
              />
              <div v-else class="flex h-full items-center justify-center text-2xl text-base-content/25">
                <i class="fa-solid fa-desktop"></i>
              </div>
              <span class="absolute left-1.5 top-1.5 badge badge-xs gap-1 bg-base-100/90 border-base-content/10">
                <i class="fa-solid" :class="providerIcon(image.provider)"></i>
                {{ providerLabel(image.provider) }}
              </span>
              <span
                class="absolute right-1.5 top-1.5 badge badge-xs"
                :class="image.provider === 'saved' ? 'badge-success' : (image.live_view === 'kasmvnc' ? 'badge-secondary' : 'badge-info')"
              >
                {{ image.provider === 'saved' ? 'Snapshot' : (image.live_view === 'kasmvnc' ? 'KasmVNC' : 'Selkies') }}
              </span>
            </div>
            <div class="flex flex-1 flex-col gap-0.5 p-2">
              <span class="flex items-center gap-1.5">
                <span class="text-xs font-semibold truncate">{{ image.name }}</span>
                <span class="badge badge-xs badge-ghost ml-auto">{{ image.category }}</span>
              </span>
              <span class="line-clamp-2 text-[11px] leading-snug text-base-content/55">
                {{ image.description }}
              </span>
              <span class="mt-auto flex items-center gap-2 pt-1 font-mono text-[10px] text-base-content/35">
                <span class="truncate">
                  {{ image.provider === 'saved' && image.image_size_bytes
                    ? formatBytes(image.image_size_bytes)
                    : image.tag }}
                </span>
                <span v-if="image.pull_count" class="ml-auto whitespace-nowrap">
                  <i class="fa-solid fa-download mr-0.5"></i>{{ formatCount(image.pull_count) }}
                </span>
              </span>
            </div>
            <span
              v-if="selected?.id === image.id"
              class="absolute right-1.5 bottom-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-content"
            ><i class="fa-solid fa-check text-[10px]"></i></span>
          </button>
        </div>
      </div>

      <!-- Selected image / tag -->
      <div v-if="selected" class="rounded-xl border border-primary/30 bg-primary/5 p-2.5 flex flex-wrap items-center gap-2">
        <i class="fa-solid fa-circle-check text-primary"></i>
        <span class="text-xs font-semibold">{{ selected.name }}</span>
        <code class="text-[10px] text-base-content/50">{{ selectedImage }}</code>
        <label v-if="selected.provider === 'kasmweb'" class="ml-auto flex items-center gap-1 text-[11px]">
          <span class="text-base-content/60">Tag</span>
          <select v-model="selectedTag" class="select select-xs select-bordered font-mono" :disabled="tagsLoading">
            <option v-if="!tags.length" :value="selected.default_tag">{{ selected.default_tag }}</option>
            <option v-for="tag in tags" :key="tag.name" :value="tag.name">{{ tag.name }}</option>
          </select>
          <span v-if="tagsLoading" class="loading loading-spinner loading-xs"></span>
        </label>
        <span v-else-if="selected.provider === 'saved'" class="ml-auto flex items-center gap-2">
          <span class="badge badge-sm badge-success badge-outline">
            <i class="fa-solid fa-bookmark mr-1"></i>Saved snapshot
          </span>
          <span v-if="selected.image_size_bytes" class="text-[11px] text-base-content/50">
            {{ formatBytes(selected.image_size_bytes) }}
          </span>
          <span v-if="selected.created_by" class="text-[11px] text-base-content/50">
            by {{ selected.created_by }}
          </span>
          <button class="btn btn-xs btn-ghost text-error" title="Delete this saved computer" @click="deleteSelectedSaved">
            <i class="fa-regular fa-trash-can"></i>
          </button>
        </span>
        <span v-else class="ml-auto badge badge-sm badge-outline font-mono">
          {{ selectedTag }}
        </span>
        <a v-if="selected.docs_url" :href="selected.docs_url" target="_blank" rel="noopener" class="btn btn-xs btn-ghost">
          Docs <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
        </a>
        <button class="btn btn-xs btn-primary" :disabled="!selectedImage" @click="useSelected">
          {{ selected.provider === 'saved' ? 'Start from snapshot' : 'Use image' }}
        </button>
      </div>

      <!-- Custom image -->
      <div class="flex flex-wrap items-center gap-2 border-t border-base-content/10 pt-2">
        <span class="text-[11px] font-semibold text-base-content/50">Custom image</span>
        <input
          v-model="customImage"
          type="text"
          class="input input-xs input-bordered flex-1 min-w-[16rem] font-mono"
          placeholder="registry.example.com/my-desktop:latest"
          @keyup.enter="useCustom"
        />
        <button class="btn btn-xs btn-outline" :disabled="!customImage.trim()" @click="useCustom">Use custom</button>
      </div>
      <p class="text-[10px] leading-snug text-base-content/40">
        LinuxServer webtop uses Selkies (HTTP 3000, path prefix). Kasmweb uses KasmVNC
        (HTTPS 6901, stripped prefix, per-session login) and is driven by the same
        X11 agent. Saved computers are committed Docker images shared with this
        project on this host. Images are pulled on first use.
      </p>
    </div>
  </modal>
</template>
