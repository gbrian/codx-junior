<script setup>
</script>
<template>
            <div :class="['dropdown dropdown-bottom click dropdown-top dropdown-left']">
            <a tabindex="0" class="px-2 flex justify-center items-center w-full focus:text-orange-500 tooltip tooltip-bottom"
                :data-tip="$users.user.username"
              @click="$ui.readScreenResolutions()">
              <div class="avatar">
                <div class="w-6 md:w-8 ring rounded-full">
                  <img :src="$storex.api.user.avatar" />
                </div>
              </div>
            </a>
            <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box z-[150] w-72 p-2 shadow-xl">
              <li>
                <a class="flex gap-1" @click.stop="setActiveTab('account')">
                  <i class="fa-regular fa-circle-user"></i>
                  Account settings
                </a>
              </li>
              <li v-if="$project && $storex.api.permissions.isProjectAdmin">
                <a class="flex gap-1"  @click.stop="setProjectTab('settings')">
                  <i class="fa-solid fa-sliders"></i>
                  Project settings
                </a>
              </li>
              <li v-if="$project">
                <a @click.stop="setProjectTab('knowledge_settings')">
                  <i class="fa-solid fa-book"></i>
                  Knowledge settings
                </a>
              </li>
              <li v-if="$storex.api.permissions.isAdmin">
                <a class="flex gap-1"  @click.stop="setActiveTab('global-settings')">
                  <i class="fa-solid fa-gear"></i>
                  Global settings
                </a>
              </li>
              <li v-if="$storex.api.permissions.isAdmin">
                <a class="flex gap-1"  @click="$ui.toggleLogs()">
                  <i class="fa-solid fa-chart-line"></i> Logs
                </a>
              </li>
              <li class="border"></li>
              <li>
                <a class="flex gap-1"> 
                  <i class="fa-solid fa-microphone-lines"></i>
                  <select class="select select-sm" @change="$ui.setVoiceLanguage($event.target.value)">
                    <option v-for="key, lang in $ui.voiceLanguages"
                      :key="lang"
                      :selected="$ui.voiceLanguage === lang" :value="lang">{{ key }}</option>
                  </select>
                </a>
              </li>
              <li class="hidden">
                <a>
                  <i class="fa-solid fa-table-columns"></i>
                  <select class="select select-sm overflow-auto" @change="$ui.setAppDivided($event.target.value)">
                    <option v-for="divider in ['none', 'horizontal', 'vertical']" :key="divider" :value="divider">
                      {{ divider }}
                    </option>
                  </select>
                </a>
              </li>
              <li class="hidden">
                <a>
                  <span class="click" @click="$storex.api.screen.getScreenResolution()"><i class="fa-solid fa-display"></i></span>
                  <select class="select select-sm overflow-auto"
                    @change="$ui.setScreenResolution($event.target.value)">
                    <option disabled selected>Select Resolution</option>
                    <option v-for="resolution in $ui.resolutions" :key="resolution" :value="resolution"
                      :selected="$ui.resolution === resolution">
                      {{ resolution }}
                    </option>
                  </select>
                  <div class="dropdown dropdown-end group">
                    <div tabindex="2" role="button" class="btn btn-xs m-1">
                      <i class="fa-solid fa-up-right-and-down-left-from-center" v-if="$ui.noVNCSettings.resize === 'scale'"></i>
                      <i class="fa-solid fa-down-left-and-up-right-to-center" v-else></i>
                    </div>
                    <ul tabindex="2" class="hidden group-hover:flex dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li @click="$ui.setNoVNCSettings({ resize: 'scale' })">
                        <a><i class="fa-solid fa-up-right-and-down-left-from-center"></i> Local</a>
                      </li>
                      <li @click="$ui.setNoVNCSettings({ resize: 'remote' })">
                        <a><i class="fa-solid fa-down-left-and-up-right-to-center"></i> Remote</a>
                      </li>
                    </ul>
                  </div>
                </a>
              </li>
              <li class="border"></li>
              <li>
                <a class="flex gap-1" @click.stop="$users.logout()">
                  <i class="fa-solid fa-right-from-bracket"></i>
                  Log out
                </a>
              </li>
            </ul>
          </div>

</template>
<script>
export default {
  methods: {
    setActiveTab(tab) {
      this.$ui.setActiveTab(tab)
    },
    setProjectTab(tab) {
      if (this.$project) { 
        this.setActiveTab(tab)
      } else {
        this.$session.onError("No project selected")
      }
    },
  }
}
</script>