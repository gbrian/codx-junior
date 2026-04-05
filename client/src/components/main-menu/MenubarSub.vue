<script setup>
import { Icon } from '@iconify/vue'
import {
  MenubarPortal,
  MenubarSub,
  MenubarSubContent,
  MenubarSubTrigger
} from 'reka-ui'
</script>
<template>
  <MenubarSub @click.stop="">
    <MenubarSubTrigger
      class="hover:bg-base-300 group leading-none rounded flex items-center h-6 px-2 my-1 relative select-none outline-none data-[state=open]:bg-green4 data-[state=open]:text-grass11 data-[highlighted]:bg-gradient-to-br data-[highlighted]:from-green9 data-[highlighted]:to-green10 data-[highlighted]:text-green1 data-[highlighted]:data-[state=open]:text-green1 data-[disabled]:text-mauve8 data-[disabled]:pointer-events-none"
    >
      <div class="grow">
        <slot name="menubaritem">
          {{ title }}
        </slot>
      </div>
      <div class="ml-auto pl-5">
        <Icon icon="radix-icons:chevron-right" />
      </div>
    </MenubarSubTrigger>
    <MenubarPortal>
      <MenubarSubContent
        class="min-w-[220px] outline-none bg-base-100 border-white/30 rounded-md p-2 border shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
        :align-offset="-5"
      >
        <slot></slot>
      </MenubarSubContent>
    </MenubarPortal>
  </MenubarSub>
</template>
<script>
export default {
  props: ['title']
}
</script>