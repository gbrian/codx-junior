<script setup>
 import { 
  MenubarRoot,
  MenubarMenu,
  MenubarTrigger,
  MenubarPortal,
  MenubarContent,

  } from 'reka-ui'; 
  import MenubarItem from '../main-menu/MenubarItem.vue';
  import BarButton from '../project/BarButton.vue'
</script>
<template>

  <MenubarRoot>
    <MenubarMenu>
      <MenubarTrigger
        class="MenubarTrigger click "
      >
        <BarButton>
          <i :class="app.icon" v-if="isAwesome"></i>
          <img class="-mt-1 w-6 h-6 rounded-full" :src="imageUrl" v-else />
        </BarButton>
      </MenubarTrigger>
      <MenubarPortal>
        <MenubarContent
          class="outline-none bg-base-100 rounded-lg p-[5px] border border-white/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
        >
          <MenubarItem @click.stop="$ui.showApp({ ...app, left: !app.left })">
            Move {{ app.left ? 'right' : 'left' }}
          </MenubarItem>
          <MenubarItem @click.stop="$ui.cloneApp(app)">
            Duplicate
          </MenubarItem>
          <MenubarItem @click.stop="$ui.openNewWindowAppPanel(app)">
            New window <i class="fa-solid fa-arrow-up-right-from-square"></i>
          </MenubarItem>
          <div class="divider"></div>
          <MenubarItem @click.stop="$ui.closeApp(app)">
            Close
          </MenubarItem>
        </MenubarContent>
      </MenubarPortal>
    </MenubarMenu>
  </MenubarRoot>
</template>
<script>
export default {
  props: ['app', 'iconClass'],
  computed: {
    isAwesome() {
      return this.app.icon?.includes("fa")
    },
    imageUrl() {
      const path = this.app.path?.split("#")[0]
      const sep = this.app.path?.endsWith("/") ? "": "/"
      return this.app.icon || `${path}${sep}favicon.ico`
    }
  }
}
</script>