<template>
  <div class="youtube-viewer">
    <iframe
      v-if="videoId"
      :src="`https://www.youtube.com/embed/${videoId}`"
      frameborder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
    ></iframe>
    <p v-else>Invalid YouTube URL</p>
  </div>
</template>

<script>
export default {
  name: 'YoutubeViewer',
  props: {
    youtubeUrl: {
      type: String,
      required: true,
    },
  },
  computed: {
    videoId() {
      const url = this.youtubeUrl;
      const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
      const match = url.match(regExp);
      return match && match[2].length === 11 ? match[2] : null;
    },
  },
};
</script>

<style scoped>
.youtube-viewer {
  width: 100%;
  height: 0;
  padding-bottom: 56.25%; /* 16:9 Aspect Ratio */
  position: relative;
}

.youtube-viewer iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
</style>