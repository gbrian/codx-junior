<script setup>
import { TreeItem, TreeRoot } from 'radix-vue'
</script>

<template>
  <div class="wiki-tree">
    <TreeRoot
      v-slot="{ flattenItems }"
      class="shrink-0 list-none select-none w-56 text-blackA11 rounded-lg p-2 text-sm font-medium"
      :items="wikiTree.categories"
      :get-key="(item) => item.title"
      :default-expanded="['components']"
    >
      <TreeItem
        v-for="item in flattenItems"
        v-slot="{ isExpanded }"
        :key="item._id"
        :style="{ 'padding-left': `${item.level - 0.5}rem` }"
        v-bind="item.bind"
        class="click flex group items-start py-1 px-2 my-0.5 rounded outline-none focus:ring-grass8 focus:ring-2 data-[selected]:bg-grass4"
      >
        <template v-if="item.value.children?.length">
          <span v-if="isExpanded"><i class="fa-solid fa-caret-down"></i></span>
          <span v-else><i class="fa-solid fa-caret-right"></i></span>
        </template>
        
        <div 
          class="grow ml-2 hover:underline justify-between flex gap-1 items-end"
          :class="item.value.title === selectedItem?.title && 'text-warning underline'"
          @click.stop="handleSelect(item.value)">
          {{ item.value.title }} 
          <div v-if="!viewOnly" class="grow justify-end flex items-center gap-1">
            <div>{{ item.value.files?.length || 0 }}</div>
            <div class="ml-2 relative">
              <i class="fa-regular fa-file-lines"></i>
              <span class="absolute bottom-1 right-2 bg-base-100"
                v-if="!item.value.single_file"
              ><i class="fa-regular fa-file-lines"></i></span>
            </div>
          </div>
        </div>

        <template v-if="!viewOnly">
          <div class="ml-2 text-error opacity-0 group-hover:opacity-100 tooltip"
            data-tip="Delete"
            @click.stop="$emit('delete-item', item.value)">
            <i class="fa-solid fa-trash-can"></i>
          </div>          
          <div class="ml-2 text-warning opacity-0 group-hover:opacity-100 tooltip"
            data-tip="Add child" @click.stop="$emit('add-child', item.value)">
            <i class="fa-solid fa-plus"></i>
          </div>
        </template>
        
      </TreeItem>
    </TreeRoot>
  </div>
</template>

<script>
export default {
  props: ['wikiTree', 'viewOnly'],
  data() {
    return {
      selectedItem: null
    }
  },
  methods: {
    handleSelect(item) {
      this.selectedItem = item
      this.$emit('select-item', item)
    }
  }
}
</script>