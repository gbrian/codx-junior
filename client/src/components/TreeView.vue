<script setup>
import { TreeItem, TreeRoot } from 'radix-vue'
</script>

<template>
  <TreeRoot
    v-slot="{ flattenItems }"
    class="list-none select-none w-56 rounded p-2 text-sm font-medium"
    :items="items"
    :get-key="(item) => item.name"
    :default-expanded="['components']"
  >
    <TreeItem
      v-for="item in flattenItems"
      v-slot="{ isExpanded }"
      :key="item._id"
      :style="{ 'padding-left': `${item.level - 0.5}rem` }"
      v-bind="item.bind"
      class="flex items-center py-1 px-2 my-0.5 rounded outline-none focus:ring-grass8 focus:ring-2 data-[selected]:bg-grass4"
    >
      <template v-if="item.value.is_dir">
        <span
          v-if="isExpanded"
          class="h-4 w-4"
        ><i class="fa-regular fa-folder-open"></i></span>
        <span
          v-else
          class="h-4 w-4"
        ><i class="fa-regular fa-folder"></i></span>
      </template>
      <div class="pl-2" :class="!item.value.is_dir && 'ml-4'" @click="onItemClick($event, item)">
        {{ item.value.name }}
      </div>
    </TreeItem>
  </TreeRoot>
</template>
<script>
export default {
  props: ['items'],
  methods: {
    async onItemClick(ev, item) {
      this.$emit('open', item.value)
      return true
    }
  }
}
</script>