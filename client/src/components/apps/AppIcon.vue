<script setup>
import { 
  MenubarRoot,
  MenubarMenu,
  MenubarTrigger,
  MenubarPortal,
  MenubarContent,
} from 'reka-ui'
import MenubarItem from '../main-menu/MenubarItem.vue'
import MenuDivider from '../main-menu/MenuDivider.vue'
</script>

<template>
  <MenubarRoot>
    <MenubarMenu>
      <MenubarTrigger class="MenubarTrigger click">
        <div class="flex items-center gap-2 mx-1">
          <!-- Show loading ring when loading prop is true -->
          <div class="" v-if="loading" >
            <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
          </div>
          <template v-else>
            <img class="w-3 h-3 bg-contain" 
              :src="imageUrl" @error="imageError = true"
                v-if="imageUrl && !imageError"
              />
            <i class="fa-solid fa-file-lines" v-else-if="isFileViewer"></i>
            <i class="fa-solid fa-bars" v-else></i>
          </template>
        </div>
      </MenubarTrigger>
      <MenubarPortal>
        <MenubarContent
          class="text-xs outline-none bg-base-100 rounded-lg p-[5px] border border-base-content/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
        >
          <!-- URL navigator: only rendered for apps that expose a URL. Keydown is
               stopped so menu typeahead/navigation doesn't hijack typing. -->
          <div
            v-if="hasUrl"
            class="w-64 px-1 pt-1 pb-2"
            @click.stop
            @keydown.stop
          >
            <div class="flex items-center gap-1">
              <!-- Return to the app base URL (its configured path) -->
              <button
                class="btn btn-xs btn-ghost px-1.5"
                title="App home"
                aria-label="Go to app home"
                @click.stop="openBaseUrl"
              >
                <i class="fa-solid fa-house text-[10px]"></i>
              </button>
              <label class="relative grow">
                <i class="fa-solid fa-globe absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-base-content/40 pointer-events-none"></i>
                <input
                  ref="urlInput"
                  v-model="urlValue"
                  type="text"
                  inputmode="url"
                  spellcheck="false"
                  autocomplete="off"
                  placeholder="https://example.com"
                  aria-label="App URL"
                  class="input input-xs input-bordered w-full pl-6 pr-2 font-mono"
                  @keydown.enter.prevent="openUrl"
                  @keydown.esc.prevent="syncUrl"
                />
              </label>
              <button
                class="btn btn-xs btn-primary px-2"
                :disabled="!urlValue"
                title="Go to URL"
                aria-label="Go to URL"
                @click.stop="openUrl"
              >
                <i class="fa-solid fa-arrow-right text-[10px]"></i>
              </button>
            </div>
          </div>
          <MenuDivider v-if="hasUrl" />
          <MenubarItem @click.stop="$ui.cloneApp(app)">
            Duplicate
          </MenubarItem>
          <MenubarItem @click.stop="$ui.openNewWindowAppPanel(app)" v-if="app.path">
            New window <i class="fa-solid fa-arrow-up-right-from-square"></i>
          </MenubarItem>
          <MenuDivider />
          <MenubarItem @click.stop="closeApp" class="text-error">
            <i class="fa-solid fa-xmark"></i> Close
          </MenubarItem>
        </MenubarContent>
      </MenubarPortal>
    </MenubarMenu>
  </MenubarRoot>
</template>

<script>
export default {
  props: ['app', 'iconClass', 'loading'],
  data() {
    return {
      imageError: false,
      urlValue: '',
    }
  },
  computed: {
    liveApp() {
      return this.$ui.openApps[this.app?.tabId] || this.app
    },
    // Id of the app inside the store. `updateAppParams` needs it to find the
    // app, and `showApp` sets `tabId = app.key` for workspace apps, so `key`
    // is a safe fallback when the prop is a plain snapshot.
    tabId() {
      return this.liveApp?.tabId || this.app?.tabId || this.app?.key || null
    },
    currentProjectId() {
      return this.liveApp?.params?.project_id
    },
    isFileViewer() {
      return !!this.app?.params?.filePath
    },
    // Workspace panels don't carry the URL on the app object itself: the
    // workspace payload (which holds the ORIGINAL `path` it was opened with)
    // travels under `params.workspace`. Read it from the live app first (the
    // prop is often a static snapshot), then the prop.
    workspaceApp() {
      return this.liveApp?.params?.workspace ||
        this.app?.params?.workspace ||
        null
    },
    // Base URL the app was opened with: the ORIGINAL `app.path`. It must stay
    // stable while the user browses (navigation only writes `lastUrl`), so the
    // "home" action can always return to where the app was started. Prefer the
    // live store app, then the workspace payload, then the mirrored `params.path`.
    baseUrl() {
      return this.liveApp?.path ||
        this.workspaceApp?.path ||
        this.liveApp?.params?.path ||
        this.app?.path ||
        this.app?.params?.path ||
        null
    },
    // Current URL of the app: the last visited URL if any, otherwise its base
    // path. Apps without an URL (chat, kanban, …) get no navigator control.
    appUrl() {
      return this.liveApp?.params?.lastUrl || this.baseUrl || null
    },
    hasUrl() {
      return !!this.appUrl
    },
    awesomeIcon() {
      if (this.app.icon?.includes("fa"))
        return this.app.icon + " fa-sm"
      return null
    },
    imageUrl() {
      if (this.imageError) return null
      if (this.app.icon?.startsWith('http')) return this.app.icon
      return null
    }
  },
  watch: {
    // Keep the address input in sync with the app URL: initial value and any
    // navigation performed inside the iframe (AppWindow persists lastUrl).
    appUrl: {
      immediate: true,
      handler(url) {
        this.urlValue = url || ''
      }
    }
  },
  methods: {
    closeApp() {
      this.$ui.closeApp(this.app)
    },
    // Reset the input back to the app's current URL (Esc).
    syncUrl() {
      this.urlValue = this.appUrl || ''
    },
    // Turn a bare host ("example.com") into an absolute URL while keeping
    // app-relative paths ("/app") and explicit schemes untouched.
    normalizeUrl(raw) {
      const url = (raw || '').trim()
      if (!url) return null
      if (url.startsWith('/') || /^[a-z][a-z0-9+.-]*:\/\//i.test(url)) return url
      return `https://${url}`
    },
    // Push a URL into the app params so the iframe (AppWindow) navigates.
    // A fresh `navToken` travels with it: it keeps the store from discarding
    // the write as a no-op when the URL is unchanged, and lets AppWindow force
    // a reload (the iframe key includes the token).
    navigate(url) {
      if (!this.tabId || !url) return
      this.$ui.updateAppParams({
        tabId: this.tabId,
        params: { lastUrl: url, navToken: Date.now() }
      })
    },
    // Navigate to the URL typed in the address input.
    openUrl() {
      const url = this.normalizeUrl(this.urlValue)
      if (!url) return
      this.urlValue = url
      this.navigate(url)
    },
    // Return to the original app base URL (its configured path). This is the
    // path the workspace/app was opened with — never the last navigated URL.
    openBaseUrl() {
      const url = this.baseUrl
      if (!url) return
      this.urlValue = url
      this.navigate(url)
    }
  }
}
</script>