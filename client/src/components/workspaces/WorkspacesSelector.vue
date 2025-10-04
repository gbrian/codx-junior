<script setup>
import { TreeItem, TreeRoot } from 'radix-vue'
</script>

<template>
  <TreeRoot
    v-slot="{ flattenItems }"
    class="list-none select-none w-56 bg-base-300 text-blackA11 rounded-lg p-2 text-sm font-medium"
    :items="items"
    :get-key="(item) => item.title"
    :default-expanded="[]"
  >
    <TreeItem
      v-for="item in flattenItems"
      v-slot="{ isExpanded }"
      :key="item._id"
      :style="{ 'padding-left': `${item.level - 0.5}rem` }"
      v-bind="item.bind"
      class="flex items-center py-1 px-2 my-0.5 rounded outline-none focus:ring-grass8 focus:ring-2 data-[selected]:bg-grass4"
      @click="item.value.app && $emit('select', { workspace: item.value.workspace, app: item.value.app })"
    >
      <template v-if="item.hasChildren">
        <i
          v-if="!isExpanded"
          class="fa-solid fa-folder h-4 w-4"
        ></i>
        <i
          v-else
          class="fa-solid fa-folder-open h-4 w-4"
        ></i>
      </template>
      <i
        v-else
        :class="`${item.value.icon} ${item.value.is_open ? 'text-warning' : ''} h-4 w-4`"
      ></i>
      <div class="pl-2">
        {{ item.value.title }}
      </div>
    </TreeItem>
  </TreeRoot>
</template>

<script>
export default {
  props: ['workspaces'],
  computed: {
    items() {
      return this.workspaces.map(workspace => ({
        title: workspace.name,
        icon: 'fa-solid fa-folder',
        children: workspace.apps.map(app => ({
          title: app.name,
          icon: app.is_open ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-window-maximize',
          is_open: app.is_open,
          app,
          workspace
        }))
      }))
    }
  }
}
</script>
