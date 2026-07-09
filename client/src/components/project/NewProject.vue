<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4 overflow-y-auto">

    <!-- Project Name -->
    <div class="form-control">
      <label class="label py-1">
        <span class="label-text font-bold text-base flex items-center gap-2">
          <i class="fa-solid fa-folder-plus text-primary"></i> Project name
        </span>
        <span class="label-text-alt text-error">*</span>
      </label>
      <input
        v-model="formData.projectName"
        type="text"
        placeholder="my-awesome-project"
        class="input input-bordered w-full"
        autofocus
      />
    </div>

    <!-- Git URL — always visible, optional -->
    <div class="form-control">
      <label class="label py-1">
        <span class="label-text font-semibold text-sm flex items-center gap-2">
          <i class="fa-brands fa-github"></i> Repository URL
          <span class="text-base-content/40 font-normal">(optional)</span>
        </span>
      </label>
      <input
        v-model="formData.gitUrl"
        type="text"
        placeholder="https://github.com/user/repo.git"
        class="input input-bordered input-sm w-full font-mono text-xs"
      />
      <div class="flex flex-wrap gap-2 mt-2">
        <button
          v-for="provider in gitProviders"
          :key="provider.label"
          @click="setGitPrefix(provider.prefix)"
          class="btn btn-xs btn-ghost border border-base-300 gap-1"
        >
          <i :class="provider.icon"></i> {{ provider.label }}
        </button>
      </div>
    </div>

    <!-- Prompt textarea -->
    <div class="form-control">
      <label class="label py-1">
        <span class="label-text text-sm font-semibold flex items-center gap-1">
          <i class="fa-solid fa-wand-magic-sparkles text-secondary"></i>
          Project prompt
          <span class="text-base-content/40 font-normal text-xs">(personalise before creating)</span>
        </span>
        <span class="label-text-alt text-base-content/40 text-xs" v-if="selectedTemplateObj">
          {{ selectedTemplateObj.icon }} {{ selectedTemplateObj.name }}
        </span>
      </label>
      <textarea
        v-model="formData.projectPrompt"
        class="textarea textarea-bordered w-full resize-none text-xs font-mono"
        rows="7"
        :placeholder="formData.selectedTemplate === 'blank' ? 'Describe your project...' : ''"
      />
    </div>

    <!-- Template carousel -->
    <div class="flex flex-col gap-2">
      <span class="text-xs font-semibold text-base-content/50 uppercase tracking-wide">
        <i class="fa-solid fa-layer-group mr-1"></i> Templates
      </span>
      <div class="carousel carousel-center gap-3 pb-2 w-full">
        <div
          v-for="template in templates"
          :key="template.id"
          class="carousel-item"
        >
          <button
            @click="selectTemplate(template)"
            class="group flex flex-col items-center gap-1.5 px-4 py-3 rounded-xl border-2 transition-all w-28 h-28 justify-center"
            :class="formData.selectedTemplate === template.id
              ? 'border-primary bg-primary/10 shadow shadow-primary/20'
              : 'border-base-300 hover:border-base-content/30 hover:bg-base-200'"
          >
            <span class="text-3xl group-hover:scale-110 transition-transform">{{ template.icon }}</span>
            <span class="font-bold text-xs text-center leading-tight">{{ template.name }}</span>
            <span class="text-xs text-base-content/50 text-center leading-tight">{{ template.description }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Advanced section (collapsible) -->
    <div class="collapse collapse-arrow border border-base-300 rounded-xl">
      <input type="checkbox" />
      <div class="collapse-title text-sm font-semibold flex items-center gap-2 py-2 min-h-0">
        <i class="fa-solid fa-sliders text-warning"></i> Advanced settings
      </div>
      <div class="collapse-content flex flex-col gap-3 pt-1">

        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-sm font-semibold flex items-center gap-1">
              <i class="fa-solid fa-folder text-warning"></i> Project location path
            </span>
            <span class="label-text-alt text-base-content/40 text-xs">new or existing directory</span>
          </label>
          <input
            v-model="formData.projectPath"
            type="text"
            placeholder="/home/projects/my-project"
            class="input input-bordered input-sm w-full font-mono text-xs"
          />
          <label class="label py-0.5">
            <span class="label-text-alt text-base-content/40 text-xs">Leave empty to use the default workspace folder</span>
          </label>
        </div>

        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-sm font-semibold flex items-center gap-1">
              <i class="fa-solid fa-gear text-warning"></i> .codx folder path
            </span>
            <span class="label-text-alt text-base-content/40 text-xs">optional — defaults to project root</span>
          </label>
          <input
            v-model="formData.codxPath"
            type="text"
            placeholder="/home/.codx-settings/my-project"
            class="input input-bordered input-sm w-full font-mono text-xs"
          />
          <label class="label py-0.5">
            <span class="label-text-alt text-base-content/40 text-xs">
              Allows storing .codx outside the project directory (useful for read-only or shared codebases)
            </span>
          </label>
        </div>

        <div class="form-control">
          <label class="label py-1">
            <span class="label-text font-bold text-sm">
              Description <span class="text-base-content/40 font-normal">(optional)</span>
            </span>
          </label>
          <textarea
            v-model="formData.projectDescription"
            placeholder="What is this project about?"
            class="textarea textarea-bordered w-full resize-none text-sm"
            rows="3"
          />
        </div>

      </div>
    </div>

    <!-- Actions -->
    <div class="flex justify-end items-center gap-2 pt-2 pb-1 mt-auto">
      <button @click="$emit('close')" class="btn btn-ghost btn-sm">
        Cancel
      </button>
      <button
        @click="createProject"
        :disabled="!isFormValid"
        class="btn btn-primary btn-sm gap-2"
      >
        <i class="fa-solid fa-sparkles"></i> Create Project
      </button>
    </div>

  </div>
</template>

<script>
export default {
  data() {
    return {
      formData: {
        selectedTemplate: 'blank',
        projectName: '',
        gitUrl: '',
        projectPrompt: '',
        projectDescription: '',
        projectPath: '',
        codxPath: ''
      },
      gitProviders: [
        { label: 'GitHub',       icon: 'fa-brands fa-github',    prefix: 'https://github.com/' },
        { label: 'GitLab',       icon: 'fa-brands fa-gitlab',    prefix: 'https://gitlab.com/' },
        { label: 'Azure DevOps', icon: 'fa-brands fa-microsoft', prefix: 'https://dev.azure.com/' },
        { label: 'Bitbucket',    icon: 'fa-brands fa-bitbucket', prefix: 'https://bitbucket.org/' }
      ],
      templates: [
        {
          id: 'blank',
          name: 'Blank',
          description: 'From scratch',
          icon: '🗒️',
          prompt: ''
        },
        {
          id: 'from-prompt',
          name: 'From Prompt',
          description: 'AI generated',
          icon: '🤖',
          prompt: `Create a new software project with the following requirements:

Project goal: <describe the main purpose>
Tech stack: <languages, frameworks, libraries>
Key features:
  - <feature 1>
  - <feature 2>
  - <feature 3>

Additional context: <any extra details, constraints or preferences>`
        },
        {
          id: 'react',
          name: 'React + Vite',
          description: 'Modern React',
          icon: '⚛️',
          prompt: `Scaffold a React 18 project using Vite as the build tool.

Include:
  - TypeScript support
  - TailwindCSS for styling
  - React Router for navigation
  - A clean folder structure (src/components, src/pages, src/hooks)

Project goal: <describe what this app will do>`
        },
        {
          id: 'vue',
          name: 'Vue 3 + TS',
          description: 'Vue framework',
          icon: '🍃',
          prompt: `Scaffold a Vue 3 project using Vite and TypeScript.

Include:
  - Pinia for state management
  - Vue Router for navigation
  - TailwindCSS + DaisyUI for styling
  - A clean folder structure (src/components, src/views, src/stores)

Project goal: <describe what this app will do>`
        },
        {
          id: 'nextjs',
          name: 'Next.js',
          description: 'Full-stack React',
          icon: '⚡',
          prompt: `Scaffold a Next.js 14 project using the App Router.

Include:
  - TypeScript
  - TailwindCSS
  - API routes under app/api
  - A clean layout with shared header/footer

Project goal: <describe what this app will do>`
        },
        {
          id: 'node',
          name: 'Node.js',
          description: 'Backend API',
          icon: '🟢',
          prompt: `Scaffold a Node.js REST API using Express and TypeScript.

Include:
  - Express with typed request/response
  - dotenv for environment config
  - A modular folder structure (src/routes, src/controllers, src/services)
  - Basic error handling middleware

Project goal: <describe what this API will do>`
        },
        {
          id: 'python',
          name: 'Python',
          description: 'Python project',
          icon: '🐍',
          prompt: `Scaffold a Python project with a virtual environment.

Include:
  - requirements.txt with key dependencies
  - A clean package structure (src/, tests/)
  - Basic logging setup
  - A README with setup instructions

Project goal: <describe what this project will do>`
        },
        {
          id: 'rust',
          name: 'Rust',
          description: 'Rust application',
          icon: '🦀',
          prompt: `Scaffold a Rust project using Cargo.

Include:
  - Cargo.toml with key dependencies
  - A modular src layout (main.rs, lib.rs, modules/)
  - Basic error handling with anyhow or thiserror
  - Unit test stubs

Project goal: <describe what this app will do>`
        }
      ]
    }
  },
  computed: {
    selectedTemplateObj() {
      return this.templates.find(t => t.id === this.formData.selectedTemplate) || null
    },
    isFormValid() {
      return !!this.formData.projectName
    }
  },
  methods: {
    selectTemplate(template) {
      this.formData.selectedTemplate = template.id
      this.formData.projectPrompt = template.prompt
    },
    setGitPrefix(prefix) {
      if (!this.formData.gitUrl.startsWith('http')) {
        this.formData.gitUrl = prefix
      }
    },
    createProject() {
      if (!this.isFormValid) return
      this.$emit('project-created', { data: { ...this.formData } })
      this.$emit('close')
    }
  }
}
</script>