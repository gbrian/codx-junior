<template>
  <div class="settings-and-customization flex flex-col gap-5">
    <Profiles />
    <ProjectSettings />
    <GlobalSettings />
  </div>
</template>

<script>
import Profiles from './Profiles.vue';
import ProjectSettings from './ProjectSettings.vue';
import GlobalSettings from './GlobalSettings.vue';

export default {
  components: {
    Profiles,
    ProjectSettings,
    GlobalSettings
  }
}
</script>