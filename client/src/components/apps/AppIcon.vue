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
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <MenubarRoot>
    <MenubarMenu>
      <MenubarTrigger class="MenubarTrigger click">
        <div class="flex items-center gap-2">
          <!-- Show loading ring when loading prop is true -->
          <div class="" v-if="loading" >
            <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
          </div>
          <template v-else>
            <img
              class="w-5 rounded-full"
              :src="currentProject?.project_icon"
              v-if="currentProject && currentProject !== $project"
            />
            <i class="fa-solid fa-bars mx-1" v-else></i>
          </template>
        </div>
      </MenubarTrigger>
      <MenubarPortal>
        <MenubarContent
          class="outline-none bg-base-100 rounded-lg p-[5px] border border-white/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
        >
          <MenubarItem>
            <!-- Stop click propagation so menu doesn't close on project change -->
            <ProjectDetailt @click.stop="" v-model="currentProject" @change="" />
          </MenubarItem>
          <MenuDivider />
          <MenubarItem @click.stop="$ui.cloneApp(app)">
            Duplicate
          </MenubarItem>
          <MenubarItem @click.stop="$ui.openNewWindowAppPanel(app)" v-if="app.path">
            New window <i class="fa-solid fa-arrow-up-right-from-square"></i>
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
      imageOk: false,
      imageError: false,
    }
  },
  computed: {
    // Read project_id from the live store app, not from the prop
    liveApp() {
      return this.$ui.openApps[this.app?.tabId] || this.app
    },
    currentProjectId() {
      return this.liveApp?.params?.project_id
    },
    currentProject: {
      get() {
        return this.$projects.allProjectsById[this.currentProjectId] || this.$project
      },
      set(project) {
        if (!project || project.project_id === this.currentProjectId) return
        this.$ui.updateAppParams({
          tabId: this.app.tabId,
          params: { project_id: project.project_id }
        })
      }
    },
    awesomeIcon() {
      if (this.app.icon?.includes("fa"))
        return this.app.icon + " fa-sm"
      return null
    },
    imageUrl() {
      if (this.imageError) return null
      if (this.app.icon?.startsWith('http')) return this.app.icon
      const path = this.app.path?.split("#")[0]
      if (path) {
        const sep = this.app.path?.endsWith("/") ? "" : "/"
        return `${path}${sep}favicon.ico`
      }
      return null
    }
  }
}
</script>