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
          class="text-xs outline-none bg-base-100 rounded-lg p-[5px] border border-white/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
        >
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
    }
  },
  computed: {
    liveApp() {
      return this.$ui.openApps[this.app?.tabId] || this.app
    },
    currentProjectId() {
      return this.liveApp?.params?.project_id
    },
    isFileViewer() {
      return !!this.app?.params?.filePath
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
  methods: {
    closeApp() {
      this.$ui.closeApp(this.app)
    }
  }
}
</script>