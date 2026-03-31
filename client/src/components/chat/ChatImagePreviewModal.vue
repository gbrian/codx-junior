<script setup>
</script>

<template>
  <modal class="w-10/12 lg:w-3/4 h-10/12 lg:h-3/4" v-if="imagePreview">
    <div class="h-full flex flex-col gap-2 justify-between">
      <div class="text-2xl">Upload image</div>

      <div class="grow">
        <div
          class="bg-contain bg-no-repeat bg-base-300/20 bg-center h-full w-full"
          :style="`background-image: url(${imagePreview.src})`"
        ></div>
      </div>

      <div>
        Image alt:
        <span class="text-xs" v-if="imagePreview.alt?.length">{{ imagePreview.alt?.length }} chars.</span>
      </div>

      <!-- Readonly alt text -->
      <pre class="alert alert-xs h-20 overflow-auto" v-if="imagePreview.readonly">{{ imagePreview.alt }}</pre>

      <!-- Editable alt text -->
      <div class="textarea input-bordered" v-else>
        <textarea
          class="w-full bg-transparent"
          v-model="imagePreview.alt"
          placeholder="Image content"
        ></textarea>
        <div class="flex justify-end">
          <button
            class="btn btn-sm bg-purple-600 text-white tooltip"
            data-tip="Extract text"
            @click="$emit('extract-text', imagePreview)"
          >
            <i class="fa-regular fa-closed-captioning"></i>
          </button>
        </div>
      </div>

      <div class="flex justify-end gap-2">
        <button class="btn" @click="$emit('cancel')">Cancel</button>
        <button class="btn btn-primary" @click="$emit('confirm')">Ok</button>
      </div>
    </div>
  </modal>
</template>

<script>
export default {
  props: {
    imagePreview: { type: Object, default: null }
  },
  emits: ['cancel', 'confirm', 'extract-text']
}
</script>