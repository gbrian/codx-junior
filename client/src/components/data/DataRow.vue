<script setup>
import moment from 'moment';
import Markdown from '../Markdown.vue';
import DataDetails from './DataDetails.vue';
</script>
<template>
  <tr v-if="item.details">
    <td colspan="12" class="w-full">
      <DataDetails :item="item"></DataDetails>
    </td>
  </tr>
  <tr v-else
    class="click">
    <td class="underline click" @click="$ui.openFile(item.metadata.source)">
      <div class="flex gap-2 items-center">
        <input type="checkbox" class="checkbox" v-model="item.selected" />
        <span class="text-error" :title="item.metadata.error"
          v-if="item.metadata.error">
          <i class="fa-solid fa-circle-exclamation"></i>
        </span>
        {{ source }}
      </div>
    </td>
    <td><div class="w-20 overflow-auto text-nowrap">{{ item.metadata.category }}</div></td>
    <td> <div class="w-20 overflow-auto text-nowrap">{{ item.metadata.keywords?.split(",").join(" ") }}</div></td>
    <td>{{ item.metadata.length }}</td>
    <td>{{ moment(item.metadata.last_update * 1000).fromNow() }}</td>
    <td>
      <pre v-if="item.metadata.training?.length">
        {{ item.metadata.training?.length }} entries
      </pre>
    </td>
  </tr>
</template>
<script>
export default {
  props: ['item'],
  computed: {
    source() {
      return this.item.metadata.source.replace(this.$project.project_path, '')
    }
  }
}
</script>