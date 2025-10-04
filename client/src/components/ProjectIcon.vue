<template>
    <div class="flex gap-1 items-center"
      :class="inline ? 'flex-row': 'flex-col'"
      :title="theProject?.project_name"
    >
    <div>
        <div class="avatar indicator pt-2" :data-tip="online !== false ? '' : 'offline'">
            <span class="indicator-item badge badge-xs badge-error" v-if="online === false">!</span>
            <div class="w-6 rounded-full" :class="online === false && 'grayscale animate-pulse'">
                <img :src="theProject?.project_icon || '/only_icon.png'" />
            </div>
        </div>
      </div>
      <div class="text-center overflow-hidden text-nowrap font-bold">
          {{ theProject?.project_name }}
      </div>
    </div>
</template>
<script>
export default {
    props: ['project', 'right', 'online', 'inline'],
    computed: {
      theProject() {
        return this.$projects.allProjects.find(p => p.project_id === this.project.project_id) ||
                this.project
      }
    }

}
</script>