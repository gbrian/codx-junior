<script setup>
import moment from 'moment';
import Badge from "./Badge.vue";
import ChatIcon from '../chat/ChatIcon.vue';
</script>
<template>
  <div class="p-2 shadow rounded flex flex-col gap-2 click"
    :class="parentChat ? 'bg-base-100':'bg-base-300'"
  >
    <div class="bg-contain bg-no-repeat bg-center h-28 bg-base-300"
      :style="`background-image: url(${image.src})`"
      v-if="image"
    >
    </div>
    <div class="flex flex-col gap-2">
      <div>
        <div class="text-xs text-primary/40 hover:text-primary text-nowrap text-ellipsis overflow-hidden"
          @click.stop="$projects.setActiveChat(parentChat)"
          v-if="parentChat">{{ parentChat.name }}</div>
        <div class="flex justify-between">
          <div class="font-semibold font-sans tracking-wide text-sm flex gap-2">
            <div class="rounded-full border-1">
              <ChatIcon :chat="task" />
            </div>
            <div class="overflow-hidden">{{task.name}}</div>
          </div>
          <div class="flex gap-2 items-center">
            <div :class="`badge badge-outline badge-${badgeColor[task.mode]}`">
              {{ task.mode }}
            </div>
          </div>
        </div>
      </div>
      <div class="flex justify-between items-center">
        <span class="text-xs" :class="isToday ? 'font-bold' : 'text-gray-600'">{{ formattedDate }}</span>
        <div class="flex gap-1 justify-end">
          <div class="font-bold text-xs text-info flex gap-2" v-for="tag in task.tags" :key="tag">
            #{{ tag }}
          </div>
          <span class="text-xs tooltip"
            :data-tip="`${task.file_list?.length} files`"
            v-if="task.file_list?.length">
            <i class="fa-solid fa-paperclip"></i>
          </span>
        </div>
      </div>
      <div class="flex justify-between items-center">
        <div class="text-xs font-bold tooltip tooltip-left"
          :data-tip="`${subTasks.length} sub tasks`"
          v-if="subTasks.length">
          {{ subTasks.length }}
          <i class="fa-regular fa-file-lines"></i>
        </div>
        <div class="badge badge-xs badge-warning" v-if="chatProject">
          {{ chatProject.project_name }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  components: {
    Badge,
    ChatIcon
  },
  props: ['task'],
  data () {
    return {
      badgeColor: {
        task: "primary",
        chat: "accent"
      }
    }
  },
  computed: {
    image() {
      let image = this.task.messages?.find(m => m.images.length)?.images[0]
      return image ? JSON.parse(image): null
    },
    isToday() {
      const updatedAt = this.task.updated_at;
      return moment(0, "HH").diff(updatedAt, "days") == 0
    },
    formattedDate() {
      const updatedAt = this.task.updated_at;
      return this.isToday
        ? moment(updatedAt).format('hh:mm:ss')
        : moment(updatedAt).format('YYYY-MM-DD hh:mm:ss');
    },
    subTasks() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.task.id)
                .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.task.project_id && 
                  p.project_id !== this.$project.project_id)
    },
    parentChat() {
      return this.$projects.chats[this.task.parent_id]
    }
  }
};
</script>