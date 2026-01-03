<template>
    <div class="btn flex-gap-2" @click="openLink">
        Vote for us <img class="w-8 rounded-full" src="https://www.producthunt.com/favicon.ico" />
    </div>
</template>
<script>
export default {
    methods: {
        openLink() {
            window.open('https://www.producthunt.com/products/codx-junior', '_blank')
        }
    }
}
</script>