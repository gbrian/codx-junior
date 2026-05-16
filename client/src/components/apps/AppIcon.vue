<script setup>
 import { 
  MenubarRoot,
  MenubarMenu,
  MenubarTrigger,
  MenubarPortal,
  MenubarContent,

  } from 'reka-ui'; 
  import MenubarItem from '../main-menu/MenubarItem.vue';
  import MenuDivider from '../main-menu/MenuDivider.vue';
  import ProjectDetailt from '../ProjectDetailt.vue';
</script>
<template>

  <MenubarRoot>
    <MenubarMenu>
      <MenubarTrigger
        class="MenubarTrigger click "
      >
        <div class="flex items-center gap-2">
          <img class="w-5 rounded-full" :src="project.project_icon"  v-if="project !== $project" />
          <i class="fa-solid fa-bars mx-1" v-else></i>
          <!--
          <i :class="awesomeIcon" v-if="awesomeIcon"></i>
          
          <img class="w-6 h-6 rounded-full" 
            :class="!imageOk && 'hidden'"
            @error="imageError = true" @load="imageOk = true" :src="imageUrl" v-if="imageUrl" />
          -->
        </div>
      </MenubarTrigger>
      <MenubarPortal>
        <MenubarContent
          class="outline-none bg-base-100 rounded-lg p-[5px] border border-white/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
        >
          <MenubarItem>
            <ProjectDetailt @click.stop="" v-model="project" @change="" />
          </MenubarItem>
          <MenuDivider/>
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
  props: ['app', 'iconClass'],
  data() {
    return {
      imageOk: false,
      imageError: false,
      project: null
    }
  },
  created() {
    this.project = this.$projects.allProjectsById[this.app.params?.project_id] || this.$project
  },
  watch: {
    project() {
      if (this.app.params.project_id != this.project.project_id) {
        this.$ui.showApp({
          ...this.app,
          params: {
            ...this.app.params,
            project_id: this.project.project_id
          }
        })
      }
    }
  },
  computed: {
    visible() {
      return this.app.path
    },
    awesomeIcon() {
      if (this.app.icon?.includes("fa"))
        return this.app.icon + " fa-sm"
      return null
    },
    imageUrl() {
      if (this.imageError) {
        return null;
      }
      if (this.app.icon?.startsWith('http')) {
        return this.app.icon
      }
      const path = this.app.path?.split("#")[0]
      if (path) {
        const sep = this.app.path?.endsWith("/") ? "": "/"
        return `${path}${sep}favicon.ico`
      }
      return null;
    }
  }
}
</script>