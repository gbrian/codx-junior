<script setup>
import { TreeItem, TreeRoot } from 'radix-vue'
</script>

<template>
  <TreeRoot
    v-slot="{ flattenItems }"
    class="list-none select-none text-blackA11 rounded-lg p-2 text-sm font-medium"
    :items="groupedItems"
    :get-key="(item) => item.title"
    :default-expanded="defaultExpanded"
  >
    <slot name="header"> 
      <h2 class="font-semibold !text-base text-blackA11 px-2 pt-1">
        Directory Structure
      </h2>
    </slot>
    <TreeItem
      v-for="item in flattenItems"
      v-slot="{ isExpanded }"
      :key="item._id"
      :style="{ 'padding-left': `${item.level - 0.5}rem` }"
      v-bind="item.bind"
      class="flex items-center py-1 px-2 my-0.5 rounded outline-none focus:ring-grass8 focus:ring-2 data-[selected]:bg-grass4"
    >
      <template v-if="item.hasChildren">
        <i class="fa-solid fa-angle-up"
          v-if="!isExpanded"
        ></i>
        <i class="fa-solid fa-angle-down" v-else></i>
      </template>
      <div class="pl-2 clilck" @click="onClickItem(item)">
        <slot :item="item" name="item">{{ item.value.title }}</slot>
      </div>
    </TreeItem>
  </TreeRoot>
</template>

<script>
function groupItemsBy(items, key) {
  const grouped = {};
  items.forEach((item) => {
    const groupKey = item[key] || 'Ungrouped';
    if (!grouped[groupKey]) {
      grouped[groupKey] = {
        title: groupKey,
        icon: 'lucide:folder',
        children: []
      };
    }
    grouped[groupKey].children.push(item);
  });
  console.log("CodxMenu grouped items", grouped)
  return Object.values(grouped);
}

export default {
  props: ['items', 'item-key', 'default-expanded'],
  computed: {
    groupedItems() {
      return groupItemsBy(this.items, this.itemKey);
    }
  },
  methods: {
    onClickItem(item) {
      if (!item.hasChildren) {
        this.$emit('select', item.value)
      }
    }
  }
}
</script>