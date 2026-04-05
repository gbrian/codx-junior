<script setup>
import {
  MenubarItem,
} from 'reka-ui'
</script>
<template>
  <MenubarItem
      class="click leading-none rounded flex items-center gap-2 h-6 px-2 py-1 my-3 relative select-none outline-none hover:bg-base-300">
      <slot></slot>
  </MenubarItem>
</template>