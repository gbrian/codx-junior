<script setup>
</script>

<template>
  <div class="carousel rounded-box" v-if="images.length">
    <div
      class="carousel-item relative click flex flex-col"
      v-for="(image, ix) in images"
      :key="image"
    >
      <div
        class="bg-contain bg-no-repeat bg-center w-10 h-10 lg:h-20 lg:w-20 mr-4"
        :style="`background-image: url(${image})`"
        @click="$emit('preview', { url: image })"
      ></div>
      <button class="btn btn-xs btn-circle btn-error absolute right-0 top-0" @click="$emit('remove', ix)">
        X
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    images: { type: Array, default: () => [] }
  },
  emits: ['remove', 'preview']
}
</script>