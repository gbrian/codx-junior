<script setup>
import RFB from '@novnc/novnc'
</script>
<template>
  <div ref="vncContainer" class="vnc-container w-full h-full"
    @focus="syncHostClipboardToNoVNC"
  ></div>
</template>
<script>
export default {
  name: 'NoVNCViewer',
  props: ['token'],
  data() {
    return {
      rfb: null,
      noVNClipboard: null
    };
  },
  mounted() {
    window.$noVNC = this
    this.connect()
  },
  computed: {
    canvas () {
      return this.$el.querySelector('canvas')
    },
    resizeType () {
      return this.$ui.noVNCSettings.resize
    }
  },
  watch: {
    resizeType () {
      this.connect()
    }
  },
  beforeDestroy() {
    if (this.rfb) {
      this.rfb.disconnect();
    }
  },
  methods: {
    connect () {
      this.rfb?.disconnect()

      const protocol = window.location.protocol.includes("https") ? "wss": "ws"
      const url = `${protocol}://${window.location.host}/novnc?token=${this.token}`
      const options = {
        credentials: {
          password: "password"
        },
      };

      this.rfb = new RFB(this.$refs.vncContainer, url, options);

      if (this.resizeType === 'scale') {
        this.rfb.scaleViewport = true
      }
      if (this.resizeType === 'remote') {
        this.rfb.clipViewport = true
        this.rfb.resizeSession = true
      }
      
      this.rfb.addEventListener('connect', () => {
        console.log('Connected to the NoVNC server');
      });

      this.rfb.addEventListener('disconnect', () => {
        console.log('Disconnected from the NoVNC server');
      });

      this.rfb.addEventListener('clipboard', (event) => {
        this.noVNClipboard = event.detail.text
        this.syncNoVNCToHostClipboard()
      });

      this.canvas.onfocus = this.syncHostClipboardToNoVNC.bind(this)
    },
    syncHostClipboardToNoVNC () {
      navigator.clipboard.readText().then(text => {
        if (this.noVNClipboard != text) {
          this.rfb.clipboardPasteFrom(text);
          console.log('Clipboard synced HOST->NoVNC')
        }
        this.noVNClipboard = text
      })
    },
    syncNoVNCToHostClipboard() {
      navigator.clipboard.writeText(this.noVNClipboard)
        .then(() => console.log('Clipboard synced NoVNC->HOST', this.noVNClipboard))
        .catch(err => console.error('Could not sync NoVNC->HOST clipboard:', err));

    }
  }
};
</script>