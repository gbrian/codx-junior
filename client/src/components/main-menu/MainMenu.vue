<script setup>
import {
  MenubarContent,
  MenubarMenu,
  MenubarPortal,
  MenubarRoot,
  MenubarTrigger,
} from 'reka-ui'
import MainMenuItems from './MainMenuItems.vue'
</script>

<template>
  <div class="flex gap-2 items-center">
    <MenubarRoot
      class="flex"
    >
      <MenubarMenu class="MenubarMenu">
        <MenubarTrigger
          class="click text-xl select-none font-bold leading-none flex items-center justify-between gap-2 tooltip"
          :data-tip="$storex.session.connected ? '' : 'API is not connected!'"
        >
          <slot>
            <div class="p-2 relative click select-none font-bold leading-none border border-base-content/30 rounded flex items-center justify-between gap-2 indicator">
              <span class="absolute left-6 -top-2 text-error animate-pulse tooltip" 
                title="API disconnected!"
                v-if="!$storex.session.connected">
                <i class="fa-solid fa-circle-exclamation"></i>
              </span>
              <div class="avatar">
                <img class="w-6 rpounded-full" src="/only_icon.png" />
              </div>
            </div>
          </slot>
        </MenubarTrigger>
        <MenubarPortal>
          <MenubarContent
            class="py-4 min-w-60 max-h-[80vh] overflow-y-auto outline-none bg-base-100 rounded-lg px-2 pb-4 border border-base-content/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
            :side-offset="5"
            :align-offset="-3"
          >
            <MainMenuItems />
          </MenubarContent>
        </MenubarPortal>
      </MenubarMenu>
    </MenubarRoot>
  </div>
</template>

<script>
export default {
}
</script>