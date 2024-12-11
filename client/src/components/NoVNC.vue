<script setup>
import RFB from '@novnc/novnc'
</script>
<template>
  <div ref="vncContainer" class="vnc-container w-full h-full"></div>
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
    }
  },
  beforeDestroy() {
    if (this.rfb) {
      this.rfb.disconnect();
    }
  },
  methods: {
    connect () {
      const protocol = window.location.protocol.includes("https") ? "wss": "ws"
      const url = `${protocol}://${window.location.host}/novnc?token=${this.token}`
      const options = {
        credentials: {
          password: "password"
        },
      };

      this.rfb = new RFB(this.$refs.vncContainer, url, options);
      this.rfb.scaleViewport = true

      this.rfb.addEventListener('connect', () => {
        console.log('Connected to the NoVNC server');
      });

      this.rfb.addEventListener('disconnect', () => {
        console.log('Disconnected from the NoVNC server');
      });

      this.rfb.addEventListener('clipboard', (event) => {
        this.noVNClipboard = event.detail.text
      });

      this.canvas.onfocus = this.syncHostClipboardToNoVNC.bind(this)
      this.canvas.onkeyup = e => {
        if (['c', 'x'].includes(e.key) && e.ctrlKey) {
            this.syncNoVNCToHostClipboard()
        }
      }
    },
    syncHostClipboardToNoVNC () {
      navigator.clipboard.readText().then(text => {
        this.rfb.clipboardPasteFrom(text);
        console.log('Clipboard synced HOST->NoVNC')
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