<script setup>
import { ComboboxAnchor, ComboboxContent, ComboboxEmpty, ComboboxGroup, ComboboxInput, ComboboxItem, ComboboxItemIndicator, ComboboxLabel, ComboboxRoot, ComboboxSeparator, ComboboxTrigger, ComboboxViewport } from 'radix-vue'
</script>

<template>
  <ComboboxRoot
    v-model="value"
    class="
    "
  >
    <div class="mt-1 ml-1 flex items-center input input-sm input-bordered">
      <ComboboxAnchor class="grow">
        <ComboboxInput
          class="h-full"
          placeholder="Search..."
          ref="input"
          @input="onInput"
        />
      </ComboboxAnchor>
      <ComboboxTrigger>
        <button class="btn btn-error btn-xs btn-outline"
          @click="$emit('close')"
        >
          X
        </button>
      </ComboboxTrigger>
    </div>

    <ComboboxContent class="absolute top-12 z-10 w-fit h-fit max-h-40 overflow-auto mt-2 bg-base-300 overflow-hidden rounded input input-bordered">
      <ComboboxViewport class="">
        <ComboboxEmpty class="text-mauve8 text-xs font-medium text-center py-2" />

        <ComboboxGroup>
          <ComboboxItem
            v-for="(option, index) in results"
            :key="index"
            class="p-1 rouunded-md hover:bg-base-100 click"
            :value="option"
            @click="$emit('select', option)"
          >
            <ComboboxItemIndicator
              class="absolute left-0 w-[25px] inline-flex items-center justify-center">
              <i class="fa-solid fa-check"></i>
            </ComboboxItemIndicator>
            <span>
              {{ option.name }}
            </span>
          </ComboboxItem>
          <ComboboxSeparator class="h-[1px] bg-grass6 m-[5px]" />
        </ComboboxGroup>
      </ComboboxViewport>
    </ComboboxContent>
  </ComboboxRoot>
</template>

<script>
export default {
  props: ['results'],
  data () {
    return {
      value: '',
      timer: null
    }
  },
  mounted() {
    // this.$refs.input?.focus()
  },
  methods: {
    onInput(event) {
      clearTimeout(this.timer)
      if (event.target.value.length >= 3) {
        this.timer = setTimeout(() => {
          try {
            this.$emit('search', event.target.value)
          } catch {}
        }, 500)
      }
    }
  }
}
</script>