<script setup>
import moment from 'moment'
</script>

<template>
  <div class="w-full flex flex-col gap-4">
    <div class="card w-full p-4">
      <div class="text-xs text-info">
        Last build: {{ moment(lastBuild).fromNow() }}
      </div>
      <div class="form-control w-full my-4">
        <label class="label" for="projectWikiPath">
          <span class="label-text">Project Wiki (Path to wiki folder)</span>
        </label>
        <input id="projectWikiPath" type="text" v-model="projectWikiPath" placeholder="Enter path relative to project_path or absolute" class="input input-bordered w-full"/>
      </div>
      <div class="flex gap-2 justify-end mt-4">
        <button @click.stop="loadCategories" class="btn btn-sm">
          <i class="fas fa-sync-alt"></i>
          Load categories
        </button>
        <button class="btn btn-sm btn-secondary" @click="resetProjectWikiPath">Reset</button>
        <button class="btn btn-sm btn-accent" @click="saveWikiPath" v-if="projectWikiPath !== $project.project_wiki">Save</button>
        <div class="dropdown">
          <button tabindex="0" class="btn btn-sm btn-accent" aria-haspopup="true" aria-expanded="false">
            Recreate Wiki
          </button>
          <ul tabindex="0" class="dropdown-content menu bg-base-200 rounded-box z-[50] w-72 p-2 shadow-xl">
            <li><a class="dropdown-item" @click="buildWiki('create_config')">Create Configuration</a></li>
            <li><a class="dropdown-item" @click="buildWiki('create_wiki_tree')">Create Wiki Tree</a></li>
            <li><a class="dropdown-item" @click="buildWiki('build_config_sidebar')">Build Config Sidebar</a></li>
            <li><a class="dropdown-item" @click="buildWiki('build_home')">Build Home</a></li>
            <li><a class="dropdown-item" @click="buildWiki('compile_wiki')">Compile Wiki</a></li>
            <hr/>
            <li><a class="dropdown-item" @click="recreateWiki('rebuild')">Rebuild All</a></li>
          </ul>
        </div>
      </div>
    </div>
    <Markdown :text="configJson"/>
  </div>
</template>

<script>
export default {
  data() {
    return {
      projectWikiPath: null,
      configJson: null,
      lastBuild: null
    }
  },
  created() {
    this.projectWikiPath = this.$project.project_wiki
    this.loadCategories()
  },
  methods: {
    async loadCategories() {
      try {
        const [config, categories] = await Promise.all([
          this.$service.wiki.getConfig(),
          this.$service.wiki.getCategories()
        ])
        this.lastBuild = config.last_update
        const toJsonBlock = json => [
                                      "```json", 
                                      JSON.stringify(json, null, 2),
                                      "```"
                                    ].join("\n")

        this.configJson = [
          "# Configuration",
          "## Config",
          toJsonBlock(config),
          "## Categories",
          toJsonBlock(categories.categories)
        ].join("\n")
      } catch (error) {
        console.error('Failed to load categories:', error)
      }
    },
    resetProjectWikiPath() {
      this.projectWikiPath = this.$project.project_wiki
    },
    recreateWiki() {
      this.$service.wiki.rebuild()
    },
    buildWiki(step) {
      this.$service.wiki.buildStep(step)
    },
    saveWikiPath() {
      // Save the new wiki path
    }
  }
}
</script>