<template>
  <TreeRoot
    v-slot="{ flattenItems }"
    class="list-none select-none w-56 bg-white text-blackA11 rounded-lg p-2 text-sm font-medium"
    :items="items"
    :get-key="item => item.title"
    :default-expanded="['* main']"
  >
    <h2 class="font-semibold !text-base text-blackA11 px-2 pt-1">
      Repository Structure
    </h2>
    <TreeItem
      v-for="item in flattenItems"
      v-slot="{ isExpanded }"
      :key="item._id"
      :style="{ 'padding-left': `${item.level - 0.5}rem` }"
      v-bind="item.bind"
      class="flex items-center py-1 px-2 my-0.5 rounded outline-none focus:ring-grass8 focus:ring-2 data-[selected]:bg-grass4"
      @click="selectCommit(item.value)"
    >
      <template v-if="item.hasChildren">
        <i v-if="!isExpanded" class="fa-solid fa-folder"></i>
        <i v-else class="fa-solid fa-folder-open"></i>
      </template>
      <i v-else :class="`fa-solid ${item.value.icon}`"></i>
      <div class="pl-2">
        {{ item.value.title }}
      </div>
    </TreeItem>
  </TreeRoot>
</template>

<script>
import { TreeItem, TreeRoot } from 'radix-vue';
import moment from 'moment';

export default {
  props: ['modelValue'],
  data() {
    return {
      repoTree: [
        {
          branch_name: "* main",
          commits: []
        },
        {
          branch_name: "codx-junior-dind",
          commits: [
            {
              commit_id: "bc9287b4dae25f22bb1a39ef0a5ba79304dc07f9",
              author: "gbrian",
              date: "2025-10-05T10:42:53+00:00",
              comment: "init"
            },
            {
              commit_id: "5952c0b15786ebbb4dd3a87946e36814ebb9e196",
              author: "gbrian",
              date: "2025-10-04T10:04:46+00:00",
              comment: "PR Merge fixes"
            }
          ]
        }
      ],
      selectedCommit: this.modelValue
    };
  },
  computed: {
    items() {
      return this.repoTree.map(branch => ({
        title: branch.branch_name,
        icon: 'fa-folder',
        children: branch.commits.map(commit => ({
          title: `[${commit.author}]: ${commit.comment} ${this.formatDate(commit.date)}`,
          icon: 'fa-file',
          commit_id: commit.commit_id
        }))
      }));
    }
  },
  methods: {
    formatDate(dateString) {
      return `[${moment(dateString).fromNow()}]`;
    },
    selectCommit(commit) {
      this.selectedCommit = commit.commit_id;
      this.$emit('update:modelValue', this.selectedCommit);
    }
  }
};
</script>