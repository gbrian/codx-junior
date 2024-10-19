<template>
  <div class="bg-base-100 shadow rounded border border-base-300 flex flex-col gap-2 click">
    <div class="bg-auto bg-no-repeat bg-center h-28 bg-base-300"
      :style="`background-image: url(${image.src})`"
      v-if="image"
    >
    </div>
    <div class="p-2 flex flex-col gap-2">
      <div class="flex justify-between">
        <div class="font-semibold font-sans tracking-wide text-sm flex gap-2">
          <div class="rounded-full border-1 bg-base-300">
            <span class="text-info" v-if="task.mode === 'live'">
              <i class="fa-brands fa-chromecast"></i>
            </span>
            <span v-if="task.mode === 'chat' || !task.mode">
              <i class="fa-regular fa-comments"></i>
            </span>
            <span v-if="task.mode === 'task'">
              <i class="fa-regular fa-file-code"></i>
            </span>
          </div>
          <div class="overflow-hidden">{{task.name}}</div>
        </div>
        <div class="flex gap-1 items-center">
          <div :class="`badge badge-${badgeColor[task.mode]}`">
            {{ task.mode }}
          </div>
          <span class="badge badge-secondary text-xs tooltip"
            :data-tip="`${task.file_list?.length} files`"
            v-if="task.file_list?.length">
            <i class="fa-solid fa-paperclip"></i>
          </span>
        </div>
      </div>
      <div class="flex justify-between items-center">
        <span class="text-sm text-gray-600">{{ formattedDate }}</span>
        <div class="flex gap-1 justify-end">
          <div class="badge badge-sm badge-info flex gap-2" v-for="tag in task.tags" :key="tag">
            {{ tag }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import moment from 'moment';
import Badge from "./Badge.vue";

export default {
  components: {
    Badge
  },
  props: ['task'],
  data () {
    return {
      badgeColor: {
        task: "primary",
        chat: "success"
      }
    }
  },
  computed: {
    image() {
      let image = this.task.messages?.find(m => m.images.length)?.images[0]
      return image ? JSON.parse(image): null
    },
    formattedDate() {
      const updatedAt = this.task.updated_at;
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD');
    }
  }
};
</script>