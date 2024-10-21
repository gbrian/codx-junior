<template>
  <iframe src="/codx-junior"
      ref="codxJunior" 
      class="h-full w-full border-0 bg-base-300"
      title="codx-junior"
      allow="camera *;microphone *;clipboard-read; clipboard-write;"
      key="codx-junior"
      @load="onCodxJuniorLoad"
      >
  </iframe>

</template>
<script>
export default {
  data () {
    return {
    }
  },
  mounted () {
    this.setStorex()
  },
  methods: {
    setStorex() {
      this.$refs.codxJunior.contentWindow.$parentStorex = this.$storex
    },
    onCodxJuniorLoad () {
      const { $storex: clidStorex } = this.$refs.codxJunior.contentWindow
      this.$storex.session.set$childCodxJuior(clidStorex)
      window.$childStorex = clidStorex
    }
  }
}
</script>