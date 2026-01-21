<template>
    <div class="btn btn-sm border click text-xl h-10 w-10" 
        :class="$ui.activeTab === tab ? 'text-primary border-primary/20': ''">
        <slot></slot>
    </div>
</template>
<script>
    export default {
        props: ['tab']
    }
</script>
