<script setup>
import IFrame from '../Iframe.vue'
</script>
<template>
    <IFrame :url="url" />
</template>
<script>
export default  {
    props: ['app'],
    computed: {
        url() {
            const origin = window.location.origin
            return `${origin}${this.app.path}`
        }
    }
}
</script>