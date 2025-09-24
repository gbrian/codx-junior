<template>
    <div class="h-16 sm:w-full shrink-0 flex flex-col gap-1 items-center items-center hover:bg-base-300 hover:shadow opacity-80 hover:opacity-100 rounded-md click"
      :title="theProject?.project_name"
    >
      <a class="h-6 w-6 mt-4 tooltip z-50">
          
          <div class="avatar indicator" :data-tip="online !== false ? '' : 'offline'">
              <span class="indicator-item badge badge-xs badge-error" v-if="online === false">!</span>
              <div class="w-6 rounded-full" :class="online === false && 'grayscale animate-pulse'">
                  <img :src="theProject?.project_icon || '/only_icon.png'" />
              </div>
          </div>
      </a>
      <div class="text-xs w-16 text-center overflow-hidden text-nowrap px-1 font-bold">
          {{ theProject?.project_name }}
      </div>
    </div>
</template>
<script>
export default {
    props: ['project', 'right', 'online'],
    computed: {
      theProject() {
        return this.$projects.allProjects.find(p => p.project_id === this.project.project_id) ||
                this.project
      }
    }

}
</script>