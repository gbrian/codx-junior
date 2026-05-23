<script setup>
import VueFileToolbarMenu from 'vue-file-toolbar-menu'
import VueDocumentEditor from 'vue-document-editor'
</script>

<template>
  <div class="w-full min-h-full">
    <!-- Top toolbar -->
    <vue-file-toolbar-menu
      :content="menu"
      class="sticky left-0 top-0 z-50 w-screen border-b border-gray-200 bg-white/80 backdrop-blur-sm
             [--bar-button-active-color:#188038] [--bar-button-open-color:#188038]
             [--bar-button-active-bkg:#e6f4ea] [--bar-button-open-bkg:#e6f4ea]"
    />

    <!-- Document editor -->
    <vue-document-editor
      ref="editor"
      class="w-full"
      v-model:content="content"
      :overlay="overlay"
      :zoom="zoom"
      :page_format_mm="page_format_mm"
      :page_margins="page_margins"
      :display="display"
    />
  </div>
</template>

<script>
import { markRaw } from 'vue'

export default {
  props: ['modelValue'],
  emits: ['update:modelValue'],

  data() {
    return {
      content: this.modelValue
        ? (typeof this.modelValue === 'string' ? this.modelValue.split('\n') : this.modelValue)
        : ['<p>Start typing...</p>'],
      zoom: 0.8,
      zoom_min: 0.10,
      zoom_max: 5.0,
      page_format_mm: [210, 297],
      page_margins: '10mm 15mm',
      display: 'grid',
      mounted: false,
      undo_count: -1,
      content_history: [],
      _mute_next_content_watcher: false
    }
  },

  created() {
    // Zoom via ctrl+scroll or trackpad pinch
    let start_zoom_gesture = false
    let start_dist_touch = false
    let start_zoom_touch = false

    window.addEventListener('wheel', (e) => {
      if (e.ctrlKey) {
        e.preventDefault()
        this.zoom = Math.min(Math.max(this.zoom - e.deltaY * 0.01, this.zoom_min), this.zoom_max)
      }
    }, { passive: false })

    window.addEventListener('gesturestart', (e) => {
      e.preventDefault()
      start_zoom_gesture = this.zoom
    })
    window.addEventListener('gesturechange', (e) => {
      e.preventDefault()
      if (!start_zoom_touch) {
        this.zoom = Math.min(Math.max(start_zoom_gesture * e.scale, this.zoom_min), this.zoom_max)
      }
    })
    window.addEventListener('gestureend', () => { start_zoom_gesture = false })

    window.addEventListener('touchstart', (e) => {
      if (e.touches.length == 2) {
        e.preventDefault()
        start_dist_touch = Math.hypot(
          e.touches[0].pageX - e.touches[1].pageX,
          e.touches[0].pageY - e.touches[1].pageY
        )
        start_zoom_touch = this.zoom
      }
    }, { passive: false })

    window.addEventListener('touchmove', (e) => {
      if (start_dist_touch && start_zoom_touch) {
        e.preventDefault()
        const zoom = start_zoom_touch * Math.hypot(
          e.touches[0].pageX - e.touches[1].pageX,
          e.touches[0].pageY - e.touches[1].pageY
        ) / start_dist_touch
        this.zoom = Math.min(Math.max(zoom, this.zoom_min), this.zoom_max)
      }
    }, { passive: false })

    window.addEventListener('touchend', () => {
      start_dist_touch = false
      start_zoom_touch = false
    }, { passive: false })

    // Intercept native undo/redo browser events
    const manage_undo_redo = (e) => {
      switch (e && e.inputType) {
        case 'historyUndo': e.preventDefault(); e.stopPropagation(); this.undo(); break
        case 'historyRedo': e.preventDefault(); e.stopPropagation(); this.redo(); break
      }
    }
    window.addEventListener('beforeinput', manage_undo_redo)
    window.addEventListener('input', manage_undo_redo)
  },

  mounted() {
    this.mounted = true
  },

  computed: {
    menu() {
      return [
        { text: 'New', title: 'New', icon: 'description', click: () => { if (confirm('Create an empty document?')) { this.content = [''] ; this.resetContentHistory() } } },
        { text: 'Print', title: 'Print', icon: 'print', click: () => window.print() },
        { is: 'spacer' },

        // Undo / redo
        { title: 'Undo', icon: 'undo', disabled: !this.can_undo, hotkey: this.isMacLike ? 'command+z' : 'ctrl+z', click: () => this.undo() },
        { title: 'Redo', icon: 'redo', disabled: !this.can_redo, hotkey: this.isMacLike ? 'shift+command+z' : 'ctrl+y', click: () => this.redo() },
        { is: 'spacer' },

        // Text alignment
        { icon: 'format_align_left', title: 'Align left', active: this.isLeftAligned, disabled: !this.current_text_style, hotkey: this.isMacLike ? 'shift+command+l' : 'ctrl+shift+l', click: () => document.execCommand('justifyLeft') },
        { icon: 'format_align_center', title: 'Align center', active: this.isCentered, disabled: !this.current_text_style, hotkey: this.isMacLike ? 'shift+command+e' : 'ctrl+shift+e', click: () => document.execCommand('justifyCenter') },
        { icon: 'format_align_right', title: 'Align right', active: this.isRightAligned, disabled: !this.current_text_style, hotkey: this.isMacLike ? 'shift+command+r' : 'ctrl+shift+r', click: () => document.execCommand('justifyRight') },
        { icon: 'format_align_justify', title: 'Justify', active: this.isJustified, disabled: !this.current_text_style, hotkey: this.isMacLike ? 'shift+command+j' : 'ctrl+shift+j', click: () => document.execCommand('justifyFull') },
        { is: 'separator' },

        // Text formatting
        { icon: 'format_bold', title: 'Bold', active: this.isBold, disabled: !this.current_text_style, hotkey: this.isMacLike ? 'command+b' : 'ctrl+b', click: () => document.execCommand('bold') },
        { icon: 'format_italic', title: 'Italic', active: this.isItalic, disabled: !this.current_text_style, hotkey: this.isMacLike ? 'command+i' : 'ctrl+i', click: () => document.execCommand('italic') },
        { icon: 'format_underline', title: 'Underline', active: this.isUnderline, disabled: !this.current_text_style, hotkey: this.isMacLike ? 'command+u' : 'ctrl+u', click: () => document.execCommand('underline') },
        { icon: 'format_strikethrough', title: 'Strike through', active: this.isStrikeThrough, disabled: !this.current_text_style, click: () => document.execCommand('strikethrough') },
        { is: 'button-color', type: 'compact', menu_class: 'align-center', disabled: !this.current_text_style, color: this.curColor, update_color: (c) => document.execCommand('foreColor', false, c.hex8) },
        { is: 'separator' },

        // Lists and headings
        { icon: 'format_list_numbered', title: 'Numbered list', active: this.isNumberedList, disabled: !this.current_text_style, click: () => document.execCommand('insertOrderedList') },
        { icon: 'format_list_bulleted', title: 'Bulleted list', active: this.isBulletedList, disabled: !this.current_text_style, click: () => document.execCommand('insertUnorderedList') },
        { html: '<b>H1</b>', title: 'Header 1', active: this.isH1, disabled: !this.current_text_style, click: () => document.execCommand('formatBlock', false, '<h1>') },
        { html: '<b>H2</b>', title: 'Header 2', active: this.isH2, disabled: !this.current_text_style, click: () => document.execCommand('formatBlock', false, '<h2>') },
        { html: '<b>H3</b>', title: 'Header 3', active: this.isH3, disabled: !this.current_text_style, click: () => document.execCommand('formatBlock', false, '<h3>') },
        { icon: 'format_clear', title: 'Clear format', disabled: !this.current_text_style, click() { document.execCommand('removeFormat'); document.execCommand('formatBlock', false, '<div>') } },
        { icon: 'splitscreen', title: 'Page break', disabled: !this.current_text_style, click: () => this.insertPageBreak() },
        { is: 'spacer' },

        // Page format menu
        {
          text: this.current_format_name, title: 'Format', icon: 'crop_free', chevron: true,
          menu: this.formats.map(([text, w, h]) => ({
            text,
            active: this.page_format_mm[0] == w && this.page_format_mm[1] == h,
            click: () => { this.page_format_mm = [w, h] }
          })),
          menu_width: 80, menu_height: 280
        },

        // Margins menu
        {
          text: this.current_margins_name, title: 'Margins', icon: 'select_all', chevron: true,
          menu: this.margins.map(([text, value]) => ({
            text: `${text} (${value})`,
            active: this.page_margins == value,
            click: () => { this.page_margins = value }
          })),
          menu_width: 200, menu_class: 'align-center'
        },

        // Zoom menu
        {
          text: Math.floor(this.zoom * 100) + '%', title: 'Zoom', icon: 'zoom_in', chevron: true,
          menu: [['200%', 2.0], ['150%', 1.5], ['125%', 1.25], ['100%', 1.0], ['75%', 0.75], ['50%', 0.5], ['25%', 0.25]].map(([text, zoom]) => ({
            text,
            active: this.zoom == zoom,
            click: () => { this.zoom = zoom }
          })),
          menu_width: 80, menu_height: 280, menu_class: 'align-center'
        },

        // Display mode menu
        {
          title: 'Display',
          icon: this.display == 'horizontal' ? 'view_column' : (this.display == 'vertical' ? 'view_stream' : 'view_module'),
          chevron: true,
          menu: [
            { icon: 'view_module', active: this.display == 'grid', click: () => { this.display = 'grid' } },
            { icon: 'view_column', active: this.display == 'horizontal', click: () => { this.display = 'horizontal' } },
            { icon: 'view_stream', active: this.display == 'vertical', click: () => { this.display = 'vertical' } }
          ],
          menu_width: 55, menu_class: 'align-right'
        }
      ]
    },

    // Page formats
    current_format_name() {
      const f = this.formats.find(([, w, h]) => this.page_format_mm[0] == w && this.page_format_mm[1] == h)
      return f ? f[0] : `${this.page_format_mm[0]}mm x ${this.page_format_mm[1]}mm`
    },
    formats: () => [
      ['A0', 841, 1189], ['A0L', 1189, 841],
      ['A1', 594, 841], ['A1L', 841, 594],
      ['A2', 420, 594], ['A2L', 594, 420],
      ['A3', 297, 420], ['A3L', 420, 297],
      ['A4', 210, 297], ['A4L', 297, 210],
      ['A5', 148, 210], ['A5L', 210, 148],
      ['A6', 105, 148], ['A6L', 148, 105]
    ],

    // Page margins
    current_margins_name() {
      const m = this.margins.find(([, v]) => this.page_margins == v)
      return m ? m[0] : this.page_margins
    },
    margins: () => [
      ['Medium', '20mm'],
      ['Small', '15mm'],
      ['Slim', '10mm 15mm'],
      ['Tiny', '5mm']
    ],

    // Text style helpers
    current_text_style() { return this.mounted ? this.$refs.editor.current_text_style : false },
    isLeftAligned() { return ['start', 'left', '-moz-left'].includes(this.current_text_style?.textAlign) },
    isRightAligned() { return ['end', 'right', '-moz-right'].includes(this.current_text_style?.textAlign) },
    isCentered() { return ['center', '-moz-center'].includes(this.current_text_style?.textAlign) },
    isJustified() { return ['justify', 'justify-all'].includes(this.current_text_style?.textAlign) },
    isBold() {
      const fw = this.current_text_style?.fontWeight
      return fw && (parseInt(fw) > 400 || fw.indexOf('bold') == 0)
    },
    isItalic() { return this.current_text_style?.fontStyle == 'italic' },
    isUnderline() {
      const stack = this.current_text_style?.textDecorationStack
      return stack && stack.some(d => d.indexOf('underline') == 0)
    },
    isStrikeThrough() {
      const stack = this.current_text_style?.textDecorationStack
      return stack && stack.some(d => d.indexOf('line-through') == 0)
    },
    isNumberedList() { return this.current_text_style?.isList && this.current_text_style?.listStyleType == 'decimal' },
    isBulletedList() { return this.current_text_style?.isList && ['disc', 'circle'].includes(this.current_text_style?.listStyleType) },
    isH1() { return this.current_text_style?.headerLevel == 1 },
    isH2() { return this.current_text_style?.headerLevel == 2 },
    isH3() { return this.current_text_style?.headerLevel == 3 },
    curColor() { return this.current_text_style?.color || 'transparent' },

    isMacLike: () => /(Mac|iPhone|iPod|iPad)/i.test(navigator.platform),
    can_undo() { return this.undo_count > 0 },
    can_redo() { return this.content_history.length - this.undo_count - 1 > 0 }
  },

  methods: {
    // Page overlay: page numbers + optional header/footer from page 3
    overlay(page, total) {
      let html = `<div style="position:absolute;bottom:8mm;${page % 2 ? 'right' : 'left'}:10mm">Page ${page} of ${total}</div>`
      if (page >= 3) {
        html += '<div style="position:absolute;left:0;top:0;right:0;padding:3mm 5mm;background:rgba(200,220,240,0.5)"><strong>HEADER</strong> - Custom header overlay</div>'
        html += '<div style="position:absolute;left:10mm;right:10mm;bottom:5mm;text-align:center;font-size:10pt">Custom footer overlay</div>'
      }
      return html
    },

    undo() { if (this.can_undo) { this._mute_next_content_watcher = true; this.content = this.content_history[--this.undo_count] } },
    redo() { if (this.can_redo) { this._mute_next_content_watcher = true; this.content = this.content_history[++this.undo_count] } },
    resetContentHistory() { this.content_history = []; this.undo_count = -1 },

    // Insert a page break at the current caret position
    async insertPageBreak() {
      document.execCommand('insertParagraph')
      const marker = '###PB###'
      document.execCommand('insertText', false, marker)

      await this.$nextTick()
      await this.$nextTick()

      const regexp = new RegExp(`<(p|div|h\\d)( [^/>]+)*>(<[^/>]+>)*${marker}`)
      for (let i = 0; i < this.content.length; i++) {
        const item = this.content[i]
        if (typeof item != 'string') continue
        const match = regexp.exec(item)
        if (match) {
          const tags_open = match[0].slice(0, -marker.length)
          let rest = item.substr(match.index + match[0].length)
          if (rest.indexOf('</') == 0) rest = '<br>' + rest
          this.content.splice(i, 1, item.substr(0, match.index), tags_open + rest)
          return
        }
      }

      // Fallback: just remove the marker if split didn't work
      for (let i = 0; i < this.content.length; i++) {
        const item = this.content[i]
        if (typeof item != 'string' || item.indexOf(marker) < 0) continue
        this.content.splice(i, 1, item.replace(marker, ''))
        break
      }
    }
  },

  watch: {
    content: {
      immediate: true,
      handler(new_content) {
        // Track history unless triggered by undo/redo
        if (!this._mute_next_content_watcher) {
          this.content_history[++this.undo_count] = new_content
          this.content_history.length = this.undo_count + 1
        }
        this._mute_next_content_watcher = false
        this.$emit('update:modelValue', Array.isArray(new_content) ? new_content.join('\n') : new_content)
      }
    },
    modelValue(val) {
      if (val !== (Array.isArray(this.content) ? this.content.join('\n') : this.content)) {
        this.content = typeof val === 'string' ? val.split('\n') : val
      }
    }
  }
}
</script>