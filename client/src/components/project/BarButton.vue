<template>
    <div class="btn btn-sm border click text-xl h-10" 
        :class="isActive ? 'text-primary border-primary/20': ''">
        <slot></slot>
    </div>
</template>
<script>
    export default {
        props: ['tab'],
        computed: {
          isActive() {
            return Object.values(this.$ui.openApps || {}).find(({ component }) => component === this.tab)
          }
        }
    }
</script>
