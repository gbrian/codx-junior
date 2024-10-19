<script setup>
import RFB from '@novnc/novnc'
</script>
<template>
  <div ref="vncContainer" class="vnc-container w-full h-full"></div>
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
        }
      };

      this.rfb = new RFB(this.$refs.vncContainer, url, options);

      this.rfb.addEventListener('connect', () => {
        console.log('Connected to the NoVNC server');
      });

      this.rfb.addEventListener('disconnect', () => {
        console.log('Disconnected from the NoVNC server');
      });

    }
  }
};
</script>