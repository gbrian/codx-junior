<script>
import {
  AUTO_DESKTOP_SIZE,
  CUSTOM_DESKTOP_SIZE,
  MAX_DESKTOP_HEIGHT,
  MAX_DESKTOP_WIDTH,
  MIN_DESKTOP_HEIGHT,
  MIN_DESKTOP_WIDTH,
  desktopSizeId,
  desktopSizeOptions
} from '../../utils/desktopSizes'

/**
 * Desktop size of a computer session.
 *
 * `Auto (fit to window)` is the first and default option: the remote desktop
 * resizes to the viewer, so it never shows black bars. The fixed presets keep a
 * resolution and let the client scale the image, and `Custom…` reveals the
 * manual width/height inputs. The select is a pure presentation of the
 * `auto`/`width`/`height` values owned by the caller, which keeps the create
 * dialog and the settings panel in sync with the same payload
 * (`desktop_auto_resize`, `desktop_width`, `desktop_height`).
 */
export default {
  name: 'DesktopSizeSelect',
  props: {
    /** Let the desktop follow the viewer size (session `desktop_auto_resize`). */
    auto: {
      type: Boolean,
      default: true
    },
    /** Fixed width in pixels (ignored while `auto` is on, kept as fallback). */
    width: {
      type: [Number, String],
      default: ''
    },
    /** Fixed height in pixels (ignored while `auto` is on, kept as fallback). */
    height: {
      type: [Number, String],
      default: ''
    },
    /** Options from `GET /api/computers/desktop-sizes` (built-in presets by default). */
    options: {
      type: Array,
      default: null
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:auto', 'update:width', 'update:height'],
  computed: {
    availableOptions() {
      return desktopSizeOptions(this.options)
    },
    selected() {
      // The stored size may come from a saved computer that used a size which
      // is not in the selector: it shows as `Custom…` instead of losing it.
      const id = desktopSizeId({ auto: this.auto, width: this.width, height: this.height }, this.availableOptions)
      const known = this.availableOptions.some(option => option.id === id)
      return known ? id : CUSTOM_DESKTOP_SIZE.id
    },
    selectedOption() {
      return this.availableOptions.find(option => option.id === this.selected) || AUTO_DESKTOP_SIZE
    },
    isCustom() {
      return this.selected === CUSTOM_DESKTOP_SIZE.id
    },
    hint() {
      if (this.auto) {
        return 'The desktop resizes to this window, so it always fills the panel (default).'
      }
      if (this.isCustom) {
        return `Width ${MIN_DESKTOP_WIDTH}–${MAX_DESKTOP_WIDTH}, height ${MIN_DESKTOP_HEIGHT}–${MAX_DESKTOP_HEIGHT}. A fixed size is applied when the session restarts.`
      }
      return 'The desktop keeps this resolution; the viewer scales it to fit the panel. Applied when the session restarts.'
    }
  },
  methods: {
    /**
     * Apply a selector choice.
     *
     * Switching to a preset writes its width/height; switching to `custom`
     * keeps whatever is typed (or the usual Full HD start) and only turns auto
     * off; `auto` keeps the last size as the startup fallback.
     */
    select(value) {
      if (value === AUTO_DESKTOP_SIZE.id) {
        this.$emit('update:auto', true)
        return
      }
      this.$emit('update:auto', false)
      const option = this.availableOptions.find(item => item.id === value)
      if (!option || option.custom) return
      this.$emit('update:width', option.width)
      this.$emit('update:height', option.height)
    },
    setWidth(value) {
      this.$emit('update:width', value === '' ? '' : Number(value))
    },
    setHeight(value) {
      this.$emit('update:height', value === '' ? '' : Number(value))
    }
  }
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <label class="flex flex-col gap-1">
      <span class="text-xs font-semibold">Desktop size</span>
      <select
        class="select select-bordered select-sm"
        :value="selected"
        :disabled="disabled"
        @change="select($event.target.value)"
      >
        <option v-for="option in availableOptions" :key="option.id" :value="option.id">
          {{ option.label }}
        </option>
      </select>
    </label>
    <p class="text-[11px] opacity-60">{{ hint }}</p>
    <div v-if="isCustom" class="grid grid-cols-2 gap-2">
      <label class="flex flex-col gap-1">
        <span class="text-[11px] font-semibold opacity-70">Width</span>
        <input
          class="input input-bordered input-sm"
          type="number"
          :min="MIN_DESKTOP_WIDTH"
          :max="MAX_DESKTOP_WIDTH"
          :value="width"
          :disabled="disabled"
          @input="setWidth($event.target.value)"
        >
      </label>
      <label class="flex flex-col gap-1">
        <span class="text-[11px] font-semibold opacity-70">Height</span>
        <input
          class="input input-bordered input-sm"
          type="number"
          :min="MIN_DESKTOP_HEIGHT"
          :max="MAX_DESKTOP_HEIGHT"
          :value="height"
          :disabled="disabled"
          @input="setHeight($event.target.value)"
        >
      </label>
    </div>
  </div>
</template>