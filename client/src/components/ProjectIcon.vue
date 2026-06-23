<script setup>
import BarButton from './project/BarButton.vue';
</script>
<template>
    <BarButton :title="theProject?.project_name">
      <div>
          <div class="avatar indicator" :data-tip="online !== false ? '' : 'offline'">
              <span class="indicator-item badge badge-xs badge-error" v-if="online === false">!</span>
              <div class="rounded-full" 
                  :class="[
                    `w-${width || 10} h-${width || 10}`,
                    online === false && 'grayscale animate-pulse',
                  ]">
                  <img :src="theProject?.project_icon || '/only_icon.png'" />
              </div>
          </div>
        </div>
        <div class="text-center overflow-hidden text-nowrap font-bold truncate" v-if="!iconOnly">
            {{ theProject?.project_name }}
        </div>
    </BarButton>
</template>
<script>
export default {
    props: ['project', 'right', 'online', 'inline', 'width', 'icon-only'],
    computed: {
      theProject() {
        return this.project ? this.$projects.allProjects.find(p => p.project_id === this.project?.project_id) ||
                this.project : null
      }
    }

}
</script>