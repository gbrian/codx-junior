<script setup>
import { TreeItem, TreeRoot } from 'radix-vue'
</script>

<template>
  <div class="w-full flex gap-2">
    <TreeRoot
      v-slot="{ flattenItems }"
      class="shrink-0 list-none select-none w-56 text-blackA11 rounded-lg p-2 text-sm font-medium"
      :items="wikiTree"
      :get-key="(item) => item.title"
      :default-expanded="['components']"
    >
      <h2 class="font-semibold !text-base text-blackA11 px-2 pt-1">
        Directory Structure
      </h2>
      <TreeItem
        v-for="item in flattenItems"
        v-slot="{ isExpanded }"
        :key="item._id"
        :style="{ 'padding-left': `${item.level - 0.5}rem` }"
        v-bind="item.bind"
        class="click flex items-center py-1 px-2 my-0.5 rounded outline-none focus:ring-grass8 focus:ring-2 data-[selected]:bg-grass4"
      >
        <template v-if="item.value.children?.length">
          <span v-if="isExpanded">-</span>
          <span v-else>+</span>
        </template>
        <div class="pl-2 hover:underline" @click.stop="editItem(item.value)">
          {{ item.value.title }}
        </div>
      </TreeItem>
    </TreeRoot>
    <div class="grow flex flex-col gap-2" v-if="selectedItem" >
      <div class="form-control">
        <label class="label">
          <span class="label-text">Title</span>
        </label>
        <input type="text" v-model="selectedItem.title" placeholder="Title" class="input input-bordered">
      </div>
      <div class="form-control">
        <label class="label">
          <span class="label-text">Description</span>
        </label>
        <textarea v-model="selectedItem.description" placeholder="Description" class="textarea textarea-bordered"></textarea>
      </div>
      <div class="form-control">
        <label class="label">
          <span class="label-text">Keywords</span>
        </label>
        <input type="text" v-model="selectedItem.keywords" placeholder="Keywords" class="input input-bordered">
      </div>
      <div class="flex gap-2">
        <button type="submit" class="btn btn-sm btn-primary">Save</button>
        <button type="button" class="btn btn-sm btn-secondary" @click="discardChanges">Discard</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedItem: null,
      wikiTree: [
        {
          id: "home",
          title: "Home",
          keywords: [],
          description: "Wiki home page. Add all basic information about the project and welcome the user",
          children: [
            {
              id: "get_started",
              title: "Get started",
              keywords: ["npm", "python", "install", "start", "run"],
              description: "Instructions for running the project",
              children: [],
            },    
          ],
        },
        {
          id: "fastapi_documentation",
          title: "FastAPI Documentation",
          keywords: ["FastAPI", "Python", "RESTful API", "Documentation"],
          description: "How to document a FastAPI Python project using Swagger UI and other tools",
          children: [
            {
              id: "swagger_ui",
              title: "Swagger UI",
              keywords: ["Swagger", "UI", "API documentation"],
              description: "Using Swagger UI to generate interactive API documentation for your FastAPI project",
              children: [],
            },
            {
              id: "other_tools",
              title: "Other Tools",
              keywords: ["ReDoc", "Sphinx", "API Blueprint"],
              description: "Alternative tools for documenting your FastAPI project",
              children: [],
            }]
          },
      ]
    }
  },
  methods: {
    editItem(item) {
      this.selectedItem = { ...item }
    }
  }
}
</script>