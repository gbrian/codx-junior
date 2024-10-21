<script setup>
import RFB from '@novnc/novnc'
</script>
<template>
  <div ref="vncContainer" class="vnc-container w-full h-full"
    @copy="onVNCCopy"
  ></div>
</template>
<script>
export default {
  name: 'NoVNCViewer',
  data() {
    return {
      rfb: null,
    };
  },
  mounted() {
    window.$noVNC = this
    this.connect()

    this.rfb.addEventListener('clipboard', (event) => {
      navigator.clipboard.writeText(event.detail.text)
        .then(() => console.log('Clipboard synced from NoVNC'))
        .catch(err => console.error('Could not sync clipboard:', err));
    });
  },
  beforeDestroy() {
    if (this.rfb) {
      this.rfb.disconnect();
    }
  },
  methods: {
    connect () {
      const url = `wss://${window.location.host}/novnc`
      const options = {
        credentials: {
          password: "password"
        },
        scaleViewport: true
      };

      this.rfb = new RFB(this.$refs.vncContainer, url, options);

      this.rfb.addEventListener('connect', () => {
        console.log('Connected to the NoVNC server');
      });

      this.rfb.addEventListener('disconnect', () => {
        console.log('Disconnected from the NoVNC server');
      });

    },
    onVNCCopy() {
      navigator.clipboard.readText().then(text => {
        this.rfb.clipboardPasteFrom(text);
      });
    }
  }
};
</script>