<script setup>
import WikiMarkdown from '@/components/wiki/WikiMarkdown.vue'
import WikiProjectTree from '@/components/wiki/WikiProjectTree.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
</script>

<template>
  <div class="wiki-shell flex h-full min-h-0 bg-base-100 text-base-content">
    <!-- Mobile backdrop -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-30 bg-black/50"
      @click="sidebarOpen = false"
    ></div>

    <!-- ── Sidebar ─────────────────────────────────────────────────────── -->
    <aside
      v-if="sidebarVisible"
      class="wiki-sidebar z-40 flex shrink-0 flex-col border-r border-base-content/10 bg-base-200/60 backdrop-blur transition-all duration-200"
      :class="isPhone
        ? 'fixed inset-y-0 left-0 w-64 shadow-2xl xl:w-72'
        : ['relative', sidebarRail ? 'w-12' : 'w-64 xl:w-72']"
    >
      <!-- Collapsed rail (desktop): only the expand affordance remains -->
      <div v-if="sidebarRail" class="flex flex-col items-center gap-2 py-3">
        <button
          class="flex h-8 w-8 items-center justify-center rounded-lg text-base-content/50 transition-colors hover:bg-base-content/10 hover:text-base-content"
          title="Expand sidebar"
          aria-label="Expand sidebar"
          @click="toggleSidebarCollapse"
        >
          <i class="fa-solid fa-angle-right text-xs"></i>
        </button>
      </div>

      <div v-if="!sidebarRail" class="flex items-center gap-2 border-b border-base-content/10 px-4 py-3">
        <div class="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-lg">
          <img v-if="site.project.icon" :src="site.project.icon" class="h-full w-full object-contain" alt="" />
          <i v-else class="fa-solid fa-book-open text-primary"></i>
        </div>
        <div class="min-w-0 flex-1">
          <div class="text-[0.65rem] font-bold uppercase tracking-[0.18em] opacity-50">Documentation</div>
          <div class="truncate text-sm font-bold">{{ site.project.title || site.project.name || 'Wiki' }}</div>
        </div>
        <button v-if="isPhone" class="btn btn-ghost btn-xs btn-circle" aria-label="Close menu" @click="sidebarOpen = false">
          <i class="fa-solid fa-xmark"></i>
        </button>
        <button
          v-else
          class="btn btn-ghost btn-xs btn-circle"
          title="Collapse sidebar"
          aria-label="Collapse sidebar"
          @click="toggleSidebarCollapse"
        >
          <i class="fa-solid fa-angle-left text-xs"></i>
        </button>
      </div>

      <!-- Project switcher -->
      <div v-if="!sidebarRail" class="relative px-3 pt-3">
        <details class="dropdown w-full" ref="projectMenu">
          <summary class="btn btn-sm w-full justify-between gap-2 border-base-content/10 bg-base-100/70 font-normal">
            <span class="flex min-w-0 items-center gap-2">
              <i class="fa-solid fa-folder-tree text-primary"></i>
              <span class="truncate">{{ site.project.name }}</span>
              <span v-if="projectLinks.length" class="badge badge-ghost badge-sm">{{ projectLinks.length }}</span>
            </span>
            <i class="fa-solid fa-chevron-down text-[0.6rem] opacity-50"></i>
          </summary>
          <ul class="menu dropdown-content z-50 mt-1 w-64 rounded-box border border-base-content/10 bg-base-100 p-2 shadow-xl">
            <li class="menu-title text-xs">Documentation projects</li>
            <li v-if="site.parent_project">
              <a @click="selectProject(site.parent_project.name)">
                <i class="fa-solid fa-arrow-up"></i>
                <span class="truncate">{{ site.parent_project.title }}</span>
                <span class="badge badge-ghost badge-xs">parent</span>
              </a>
            </li>
            <li>
              <a class="active" @click="selectProject(site.project.name)">
                <i class="fa-solid fa-book"></i>
                <span class="truncate">{{ site.project.title || site.project.name }}</span>
                <span class="badge badge-primary badge-xs">{{ site.stats.pages || 0 }}</span>
              </a>
            </li>
            <li v-for="child in site.child_projects" :key="child.project_id || child.name">
              <a @click="selectProject(child.name)">
                <span class="status-badge" :class="'status-' + (child.status || 'pending')"></span>
                <span class="truncate">{{ child.title || child.name }}</span>
                <span class="badge badge-ghost badge-xs">{{ child.page_count || 0 }}</span>
              </a>
            </li>
            <li v-if="!projectLinks.length" class="px-3 py-2 text-xs opacity-50">
              Child project docs appear here once they are linked.
            </li>
          </ul>
        </details>
      </div>

      <!-- Search -->
      <div v-if="!sidebarRail" class="px-3 pt-2">
        <button
          class="btn btn-sm w-full justify-start gap-2 border-base-content/10 bg-base-100/50 font-normal text-base-content/60"
          @click="openSearch"
        >
          <i class="fa-solid fa-magnifying-glass"></i>
          <span>Search docs</span>
          <kbd class="kbd kbd-xs ml-auto">⌘K</kbd>
        </button>
      </div>

      <!-- Navigation -->
      <nav v-if="!sidebarRail" class="mt-3 flex-1 overflow-y-auto px-2 pb-4">
        <div v-for="section in site.navigation" :key="section.title" class="mb-1">
          <button
            class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[0.68rem] font-bold uppercase tracking-[0.12em] opacity-60 hover:bg-base-300/60 hover:opacity-100"
            @click="toggleSection(section.title)"
          >
            <i :class="section.icon || 'fa-regular fa-folder'"></i>
            <span class="truncate">{{ section.title }}</span>
            <span class="ml-auto text-[0.62rem] opacity-60">{{ section.items.length }}</span>
            <i class="fa-solid text-[0.55rem]" :class="isSectionCollapsed(section.title) ? 'fa-chevron-right' : 'fa-chevron-down'"></i>
          </button>
          <ul v-show="!isSectionCollapsed(section.title)" class="mt-0.5 space-y-0.5">
            <li v-for="item in section.items" :key="item.path">
              <button
                class="group flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[0.82rem] transition-colors"
                :class="isActive(item.path) ? 'bg-base-content/10 font-semibold' : 'hover:bg-base-content/5'"
                @click="openPage(item.path)"
              >
                <i :class="[item.icon || 'fa-regular fa-file-lines', isActive(item.path) ? 'text-primary' : 'opacity-45']" class="w-4 shrink-0 text-center text-[0.72rem]"></i>
                <span class="truncate">{{ item.title }}</span>
                <span v-if="item.kind === 'overview'" class="badge badge-ghost badge-xs ml-auto">start</span>
              </button>
            </li>
          </ul>
        </div>

        <div v-if="projectTree.length" class="mt-4 border-t border-base-content/10 pt-3">
          <div class="px-2 text-[0.68rem] font-bold uppercase tracking-[0.12em] opacity-60">Projects</div>
          <WikiProjectTree
            :nodes="projectTree"
            :current="site.project?.name"
            class="mt-1"
            @select="selectProject"
          />
        </div>

        <div v-if="!site.navigation.length" class="px-3 py-6 text-center text-xs opacity-50">
          <i class="fa-regular fa-folder-open mb-2 block text-2xl opacity-40"></i>
          No documentation pages yet.
        </div>
      </nav>

      <!-- Sidebar footer -->
      <div v-if="!sidebarRail" class="border-t border-base-content/10 px-3 py-3">
        <div class="flex items-center gap-2 text-[0.7rem] text-base-content/60">
          <span class="status-dot" :class="updateStatus.running || updateStatus.pending ? 'is-busy' : 'is-ok'"></span>
          <span class="min-w-0 flex-1 truncate">{{ updateLabel }}</span>
          <button class="btn btn-ghost btn-xs btn-circle" title="Refresh documentation" @click="requestRefresh">
            <i class="fa-solid fa-rotate" :class="{ 'animate-spin': refreshing }"></i>
          </button>
        </div>
        <button v-if="assistantEnabled" class="btn btn-primary btn-sm mt-2 w-full gap-2" @click="toggleAssistant(true)">
          <i class="fa-solid fa-wand-magic-sparkles"></i>
          Ask the docs assistant
        </button>
      </div>
    </aside>

    <!-- ── Main ─────────────────────────────────────────────────────────── -->
    <div class="flex min-w-0 flex-1 flex-col">
      <!-- Top bar -->
      <header class="flex h-14 shrink-0 items-center gap-2 border-b border-base-content/10 bg-base-100/80 px-3 backdrop-blur lg:px-5">
        <button v-if="isPhone" class="btn btn-ghost btn-sm gap-2" aria-label="Open documentation menu" @click="sidebarOpen = true">
          <i class="fa-solid fa-bars"></i>
          <span>Docs</span>
        </button>
        <button
          v-else-if="sidebarCollapsed"
          class="btn btn-ghost btn-sm btn-square"
          title="Expand sidebar"
          aria-label="Expand sidebar"
          @click="toggleSidebarCollapse"
        >
          <i class="fa-solid fa-bars"></i>
        </button>

        <div class="hidden min-w-0 items-center gap-1.5 text-xs text-base-content/55 sm:flex">
          <button class="hover:text-primary" @click="openPage(site.home.page)">Docs</button>
          <i class="fa-solid fa-chevron-right text-[0.5rem] opacity-40"></i>
          <span v-if="page?.section" class="truncate">{{ page.section }}</span>
          <template v-if="page && page.section">
            <i class="fa-solid fa-chevron-right text-[0.5rem] opacity-40"></i>
          </template>
          <span class="max-w-[36vw] truncate font-medium text-base-content/80">{{ page?.title || site.project.title }}</span>
        </div>

        <div class="ml-auto flex items-center gap-1.5">
          <span class="hidden items-center gap-1 rounded-full border border-base-content/10 px-2 py-1 text-[0.65rem] text-base-content/50 md:flex">
            <span class="status-dot" :class="updateStatus.running || updateStatus.pending ? 'is-busy' : 'is-ok'"></span>
            {{ updateLabel }}
          </span>
          <button class="btn btn-ghost btn-sm gap-2" title="Search documentation (⌘K)" @click="openSearch">
            <i class="fa-solid fa-magnifying-glass"></i>
            <span class="hidden sm:inline">Search</span>
          </button>
          <button
            v-if="assistantEnabled"
            class="btn btn-sm gap-2"
            :class="assistantOpen ? 'btn-secondary' : 'btn-primary'"
            @click="toggleAssistant()"
          >
            <i class="fa-solid fa-comment-dots"></i>
            <span class="hidden sm:inline">Ask AI</span>
          </button>
        </div>
      </header>

      <!-- Document + assistant live in a resizable splitter so the chat side
           can be widened/narrowed and the split is remembered. On phones the
           splitter falls back to a plain container: the assistant takes the
           full width while it is open. -->
      <VerticalSplitter
        class="relative flex min-h-0 flex-1"
        :split="!isPhone"
        :show-left="!isPhone || !assistantOpen"
        :show-right="assistantOpen"
        :show-handle="true"
        persist-key="wiki-assistant"
        :panels="{
          left: { minSize: 40, defaultSize: 70, collapsible: false },
          right: { minSize: 22, defaultSize: 30, collapsible: false }
        }"
      >
        <template #left>
          <main ref="scroller" class="h-full min-w-0 overflow-y-auto scroll-smooth" @scroll="onScroll">
            <div v-if="error && !loadingSite" class="mx-auto mt-4 max-w-5xl px-5">
              <div class="alert alert-error shadow-sm">
                <i class="fa-solid fa-circle-exclamation"></i>
                <span class="text-sm">{{ error }}</span>
                <button class="btn btn-ghost btn-xs" @click="loadSite(projectName)">Retry</button>
              </div>
            </div>

            <!-- Loading -->
            <div v-if="loadingSite" class="mx-auto flex max-w-5xl flex-col gap-4 p-6 lg:p-10">
              <div class="skeleton h-8 w-1/3 rounded-lg"></div>
              <div class="skeleton h-4 w-2/3 rounded"></div>
              <div class="skeleton h-4 w-1/2 rounded"></div>
              <div class="skeleton h-64 w-full rounded-2xl"></div>
            </div>

            <!-- Empty / disabled -->
            <div v-else-if="!site.navigation.length" class="mx-auto max-w-2xl p-8 text-center lg:p-16">
              <div class="mx-auto mb-5 flex h-16 w-16 items-center justify-center text-3xl text-primary">
                <i class="fa-solid fa-book-open-reader"></i>
              </div>
              <h2 class="text-2xl font-bold">This project has no wiki yet</h2>
              <p class="mt-2 text-sm opacity-60">
                Create a documentation site from the project layout. The first overview pages
                appear immediately; detailed pages are generated in the background.
              </p>
              <div class="mt-5 flex flex-wrap justify-center gap-2">
                <button class="btn btn-primary btn-sm gap-2" :disabled="creatingWiki" @click="createWiki">
                  <span v-if="creatingWiki" class="loading loading-spinner loading-xs"></span>
                  <i v-else class="fa-solid fa-wand-magic-sparkles"></i>
                  {{ creatingWiki ? 'Creating wiki…' : 'Create wiki' }}
                </button>
                <button class="btn btn-ghost btn-sm gap-2" :disabled="creatingWiki" @click="requestRefresh">
                  <i class="fa-solid fa-rotate"></i> Check again
                </button>
                <button class="btn btn-ghost btn-sm gap-2" @click="openWikiSettings">
                  <i class="fa-solid fa-sliders"></i> Wiki settings
                </button>
              </div>
            </div>

            <!-- Landing -->
            <div v-else-if="isHome" class="pb-16">
              <section class="relative overflow-hidden border-b border-base-content/10">
                <div class="relative mx-auto max-w-5xl px-6 py-10 lg:px-10 lg:py-14">
                  <div class="inline-flex items-center gap-2 rounded-full border border-base-content/15 px-3 py-1 text-[0.68rem] font-semibold text-base-content/70">
                    <i class="fa-solid fa-sparkles"></i>
                    {{ site.home.badge || 'Living documentation' }}
                  </div>
                  <div class="mt-5 flex items-start gap-4">
                    <div v-if="site.project.icon" class="hidden h-14 w-14 shrink-0 sm:block">
                      <img :src="site.project.icon" class="h-full w-full object-contain" alt="" />
                    </div>
                    <div class="min-w-0">
                      <h1 class="text-3xl font-black tracking-tight lg:text-5xl">{{ site.home.title }}</h1>
                      <p class="mt-2 max-w-2xl text-lg text-base-content/70">{{ homeTagline }}</p>
                      <p class="mt-3 max-w-3xl text-sm leading-relaxed text-base-content/60">{{ homeDescription }}</p>
                    </div>
                  </div>

                  <div class="mt-6 flex flex-wrap gap-2">
                    <button class="btn btn-primary gap-2" @click="openPage(site.home.page)">
                      <i class="fa-solid fa-book-open"></i> Start reading
                    </button>
                    <button v-if="assistantEnabled" class="btn btn-outline gap-2" @click="toggleAssistant(true)">
                      <i class="fa-solid fa-wand-magic-sparkles"></i> Ask the assistant
                    </button>
                    <a v-if="site.project.repository" :href="site.project.repository" target="_blank" rel="noopener" class="btn btn-ghost gap-2">
                      <i class="fa-brands fa-github"></i> Repository
                    </a>
                  </div>

                  <div class="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div v-for="stat in landingStats" :key="stat.label" class="rounded-xl border border-base-content/10 bg-base-100/60 px-3 py-3">
                      <div class="text-xl font-black">{{ stat.value }}</div>
                      <div class="text-[0.65rem] font-semibold uppercase tracking-[0.14em] opacity-50">{{ stat.label }}</div>
                    </div>
                  </div>
                </div>
              </section>

              <section class="mx-auto max-w-5xl px-6 py-10 lg:px-10">
                <div class="flex items-end justify-between gap-4">
                  <div>
                    <h2 class="text-xl font-bold">Explore the docs</h2>
                    <p class="text-sm opacity-55">Curated entry points, not a folder listing.</p>
                  </div>
                  <button class="btn btn-ghost btn-sm gap-1" @click="openSearch">
                    Browse all <i class="fa-solid fa-arrow-right"></i>
                  </button>
                </div>
                <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <button
                    v-for="feature in site.home.features"
                    :key="feature.title"
                    class="group rounded-2xl border border-base-content/10 bg-base-200/40 p-4 text-left transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg"
                    @click="openPage(feature.path)"
                  >
                    <span class="flex h-9 w-9 items-center justify-center text-primary/80">
                      <i :class="feature.icon || 'fa-regular fa-file-lines'"></i>
                    </span>
                    <span class="mt-3 block text-sm font-bold">{{ feature.title }}</span>
                    <span class="mt-1 block text-xs leading-relaxed opacity-60">{{ feature.details }}</span>
                    <span class="mt-3 flex items-center gap-1 text-[0.68rem] font-semibold text-primary opacity-0 transition group-hover:opacity-100">
                      Read page <i class="fa-solid fa-arrow-right text-[0.6rem]"></i>
                    </span>
                  </button>
                </div>

                <div v-if="site.home.quick_links.length" class="mt-8">
                  <h2 class="text-xl font-bold">Quick links</h2>
                  <div class="mt-3 divide-y divide-base-content/10 rounded-2xl border border-base-content/10 bg-base-100">
                    <button
                      v-for="link in site.home.quick_links"
                      :key="link.path"
                      class="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-base-200/60"
                      @click="openPage(link.path)"
                    >
                      <i :class="link.icon" class="w-5 text-center text-primary/70"></i>
                      <span class="min-w-0 flex-1">
                        <span class="block truncate text-sm font-semibold">{{ link.title }}</span>
                        <span class="block truncate text-xs opacity-50">{{ link.description }}</span>
                      </span>
                      <i class="fa-solid fa-arrow-right text-[0.65rem] opacity-30"></i>
                    </button>
                  </div>
                </div>

                <div v-if="landingPage" class="wiki-overview mt-10 rounded-2xl border border-base-content/10 bg-base-100 p-5 lg:p-7">
                  <div class="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] opacity-45">
                    <i class="fa-regular fa-map"></i> Project overview
                  </div>
                  <WikiMarkdown :text="landingPage.content" hide-title @open-page="openPage" />
                </div>
              </section>
            </div>

            <!-- Document -->
            <article v-else-if="page" class="mx-auto flex max-w-6xl gap-8 px-5 py-8 lg:px-10">
              <div class="min-w-0 flex-1">
                <div class="mb-6">
                  <div class="flex flex-wrap items-center gap-2 text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-base-content/45">
                    <span class="rounded-md bg-base-200 px-2 py-0.5">{{ page.section }}</span>
                    <span>{{ page.reading_time }} min read</span>
                    <span v-if="page.updated_at">Updated {{ formatDate(page.updated_at) }}</span>
                    <span v-if="page.has_diagram" class="flex items-center gap-1"><i class="fa-solid fa-diagram-project"></i> diagrams</span>
                  </div>
                  <h1 class="mt-3 text-3xl font-black tracking-tight lg:text-4xl">{{ page.title }}</h1>
                  <p v-if="page.description" class="mt-2 max-w-3xl text-base text-base-content/60">{{ page.description }}</p>
                  <div class="mt-3 flex flex-wrap items-center gap-2">
                    <span v-for="tag in page.tags" :key="tag" class="badge badge-ghost badge-sm">#{{ tag }}</span>
                    <button v-if="page.source" class="badge badge-outline badge-sm gap-1 hover:border-primary hover:text-primary" :title="page.source" @click="openSource(page.source)">
                      <i class="fa-solid fa-code"></i> source
                    </button>
                    <button class="badge badge-outline badge-sm gap-1 hover:border-primary hover:text-primary" @click="copyLink">
                      <i class="fa-regular fa-copy"></i> copy link
                    </button>
                    <button v-if="assistantEnabled" class="badge badge-outline badge-sm gap-1 hover:border-primary hover:text-primary" @click="askAboutPage">
                      <i class="fa-solid fa-wand-magic-sparkles"></i> ask about this page
                    </button>
                  </div>
                </div>

                <div v-if="pageLoading" class="space-y-3">
                  <div class="skeleton h-4 w-full rounded"></div>
                  <div class="skeleton h-4 w-11/12 rounded"></div>
                  <div class="skeleton h-4 w-4/5 rounded"></div>
                  <div class="skeleton h-40 w-full rounded-xl"></div>
                </div>
                <WikiMarkdown v-else :text="page.content" @open-page="openPage" />

                <div class="mt-10 flex flex-col gap-3 border-t border-base-content/10 pt-5 sm:flex-row sm:items-center">
                  <button v-if="previousPage" class="btn btn-ghost h-auto justify-start gap-3 py-2 text-left" @click="openPage(previousPage.path)">
                    <i class="fa-solid fa-arrow-left text-xs opacity-50"></i>
                    <span>
                      <span class="block text-[0.62rem] uppercase tracking-wider opacity-40">Previous</span>
                      <span class="block text-sm font-semibold">{{ previousPage.title }}</span>
                    </span>
                  </button>
                  <div class="grow"></div>
                  <button v-if="nextPage" class="btn btn-ghost h-auto justify-end gap-3 py-2 text-right" @click="openPage(nextPage.path)">
                    <span>
                      <span class="block text-[0.62rem] uppercase tracking-wider opacity-40">Next</span>
                      <span class="block text-sm font-semibold">{{ nextPage.title }}</span>
                    </span>
                    <i class="fa-solid fa-arrow-right text-xs opacity-50"></i>
                  </button>
                </div>

                <div class="mt-5 flex items-center justify-between rounded-xl border border-base-content/10 bg-base-200/30 px-4 py-3 text-xs">
                  <span class="opacity-55">Was this page helpful?</span>
                  <div class="flex gap-1">
                    <button class="btn btn-ghost btn-xs gap-1" :class="{ 'text-success': feedback === 'yes' }" @click="sendFeedback('yes')">
                      <i class="fa-regular fa-thumbs-up"></i> Yes
                    </button>
                    <button class="btn btn-ghost btn-xs gap-1" :class="{ 'text-error': feedback === 'no' }" @click="sendFeedback('no')">
                      <i class="fa-regular fa-thumbs-down"></i> No
                    </button>
                  </div>
                </div>
              </div>

              <!-- On this page -->
              <aside class="hidden w-56 shrink-0 xl:block">
                <div class="sticky top-6">
                  <div class="mb-2 text-[0.65rem] font-bold uppercase tracking-[0.14em] opacity-40">On this page</div>
                  <nav class="space-y-1 border-l border-base-content/10">
                    <button
                      v-for="heading in page.headings"
                      :key="heading.id"
                      class="block w-full border-l-2 py-1 pl-3 text-left text-xs transition-colors"
                      :class="[
                        heading.level === 3 ? 'ml-3' : '',
                        activeHeading === heading.id
                          ? 'border-primary font-semibold text-primary'
                          : 'border-transparent opacity-55 hover:border-base-content/30 hover:opacity-90'
                      ]"
                      @click="scrollToHeading(heading.id)"
                    >
                      {{ heading.text }}
                    </button>
                  </nav>
                  <div v-if="assistantEnabled" class="mt-5 rounded-xl border border-base-content/10 bg-base-200/40 p-3">
                    <div class="text-[0.65rem] font-bold uppercase tracking-wider opacity-40">Need help?</div>
                    <p class="mt-1 text-xs opacity-60">Ask the assistant about this page.</p>
                    <button class="btn btn-primary btn-xs mt-2 w-full" @click="askAboutPage">Ask AI</button>
                  </div>
                </div>
              </aside>
            </article>

            <div v-else class="p-10 text-center text-sm opacity-50">Select a page from the sidebar.</div>
          </main>
        </template>

        <!-- ── Assistant panel ────────────────────────────────────────── -->
        <template #right>
          <aside class="flex h-full min-w-0 flex-col border-l border-base-content/10 bg-base-100">
            <div class="flex items-center gap-2 border-b border-base-content/10 px-4 py-3">
              <div class="flex h-8 w-8 items-center justify-center text-primary">
                <i class="fa-solid fa-robot text-sm"></i>
              </div>
              <div class="min-w-0 flex-1">
                <div class="text-sm font-bold">{{ site.assistant.name || 'Docs assistant' }}</div>
                <div class="text-[0.65rem] opacity-50">Answers from this project's docs</div>
              </div>
              <button class="btn btn-ghost btn-xs btn-circle" aria-label="Close assistant" @click="assistantOpen = false">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>

            <div class="flex items-center gap-2 border-b border-base-content/10 px-3 py-1.5 text-[0.65rem] text-base-content/60">
              <label class="flex cursor-pointer items-center gap-1.5">
                <input v-model="assistantIncludeChildren" type="checkbox" class="checkbox checkbox-xs" />
                Child projects
              </label>
              <span>Depth</span>
              <select v-model.number="assistantChildDepth" class="select select-xs select-bordered h-6 min-h-0 py-0">
                <option :value="1">1</option>
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="4">4</option>
              </select>
            </div>

            <div ref="assistantScroll" class="flex-1 space-y-4 overflow-y-auto px-3 py-4">
              <div v-for="(message, index) in assistantMessages" :key="index" class="flex gap-2" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
                <div v-if="message.role === 'assistant'" class="mt-1 flex h-7 w-7 shrink-0 items-center justify-center text-primary/70">
                  <i class="fa-solid fa-robot text-[0.7rem]"></i>
                </div>
                <div class="min-w-0 max-w-[85%]" :class="message.role === 'user' ? 'order-first' : ''">
                  <div
                    class="rounded-2xl px-3 py-2 text-sm"
                    :class="message.role === 'user' ? 'rounded-br-sm bg-primary text-primary-content' : 'rounded-bl-sm bg-base-200'"
                  >
                    <WikiMarkdown v-if="message.role === 'assistant'" :text="message.content" compact @open-page="openPage" />
                    <span v-else class="whitespace-pre-wrap">{{ message.content }}</span>
                  </div>
                  <div v-if="message.citations?.length" class="mt-2 flex flex-wrap gap-1">
                    <button
                      v-for="citation in message.citations"
                      :key="citation.type + citation.path"
                      class="badge badge-outline badge-sm max-w-full gap-1 hover:border-primary hover:text-primary"
                      :title="citation.description"
                      @click="openCitation(citation)"
                    >
                      <i :class="citation.icon || 'fa-regular fa-file-lines'" class="text-[0.6rem]"></i>
                      <span class="max-w-[11rem] truncate">{{ citation.title }}</span>
                    </button>
                  </div>
                </div>
              </div>

              <div v-if="assistantLoading" class="flex items-center gap-2 text-xs opacity-60">
                <span class="loading loading-dots loading-sm"></span>
                Searching the docs…
              </div>

              <div v-if="assistantMessages.length === 1 && !assistantLoading" class="space-y-1.5">
                <div class="px-1 text-[0.65rem] font-bold uppercase tracking-wider opacity-40">Try asking</div>
                <button
                  v-for="suggestion in assistantSuggestions"
                  :key="suggestion"
                  class="block w-full rounded-xl border border-base-content/10 bg-base-200/40 px-3 py-2 text-left text-xs transition hover:border-primary/40 hover:bg-base-200"
                  @click="askAssistant(suggestion)"
                >
                  {{ suggestion }}
                </button>
              </div>
            </div>

            <div class="border-t border-base-content/10 p-3">
              <div class="flex items-end gap-2 rounded-xl border border-base-content/15 bg-base-200/40 p-2 focus-within:border-primary/50">
                <textarea
                  ref="assistantInput"
                  v-model="assistantInput"
                  rows="1"
                  class="max-h-28 min-h-[2rem] flex-1 resize-none bg-transparent px-1 py-1 text-sm outline-none"
                  placeholder="Ask about the architecture, a module…"
                  @keydown.enter.exact.prevent="askAssistant()"
                  @input="resizeAssistantInput"
                ></textarea>
                <button class="btn btn-primary btn-sm btn-square" :disabled="assistantLoading || !assistantInput.trim()" @click="askAssistant()">
                  <i class="fa-solid fa-paper-plane text-xs"></i>
                </button>
              </div>
              <div class="mt-1.5 flex items-center justify-between text-[0.62rem] opacity-40">
                <span>Grounded in this project's wiki</span>
                <span>Enter to send · Shift+Enter for newline</span>
              </div>
            </div>
          </aside>
        </template>
      </VerticalSplitter>
    </div>

    <!-- ── Search palette ──────────────────────────────────────────────── -->
    <div v-if="searchOpen" class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 pt-[12vh] backdrop-blur-sm" @click.self="closeSearch">
      <div class="w-full max-w-xl overflow-hidden rounded-2xl border border-base-content/10 bg-base-100 shadow-2xl">
        <div class="flex items-center gap-2 border-b border-base-content/10 px-4 py-3">
          <i class="fa-solid fa-magnifying-glass text-primary"></i>
          <input
            ref="searchInput"
            v-model="searchQuery"
            type="text"
            class="flex-1 bg-transparent text-sm outline-none"
            placeholder="Search titles, sections and tags…"
            @keydown.esc="closeSearch"
          />
          <kbd class="kbd kbd-xs">esc</kbd>
        </div>
        <div class="flex items-center justify-between border-b border-base-content/10 px-4 py-2 text-[0.7rem] text-base-content/60">
          <label class="flex cursor-pointer items-center gap-2">
            <input v-model="searchIncludeChildren" type="checkbox" class="checkbox checkbox-xs" />
            Include child project docs
          </label>
          <span>Depth {{ site.search?.depth ?? 0 }}</span>
        </div>
        <div class="max-h-[55vh] overflow-y-auto p-2">
          <button
            v-for="result in searchResults"
            :key="result.path"
            class="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-base-200"
            @click="openSearchResult(result)"
          >
            <i :class="result.icon || 'fa-regular fa-file-lines'" class="w-4 text-center text-primary/60"></i>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-sm font-semibold">{{ result.title }}</span>
              <span class="block truncate text-[0.7rem] opacity-50">{{ result.section }} · {{ result.description }}</span>
            </span>
            <span v-if="result.project && result.project !== site.project?.name" class="badge badge-ghost badge-xs">{{ result.project_title || result.project }}</span>
            <span class="text-[0.6rem] uppercase tracking-wider opacity-30">{{ result.kind }}</span>
          </button>
          <div v-if="!searchResults.length" class="px-4 py-8 text-center text-sm opacity-50">
            No pages match "{{ searchQuery }}".
          </div>
        </div>
      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="fixed bottom-5 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-neutral px-4 py-2 text-xs font-medium text-neutral-content shadow-xl">
      {{ toast }}
    </div>
  </div>
</template>

<script>
const EMPTY_SITE = {
  project: {},
  home: { features: [], quick_links: [] },
  navigation: [],
  pages: {},
  child_projects: [],
  parent_project: null,
  hierarchy: [],
  assistant: { search_children: true, search_depth: 2 },
  stats: {},
  search: { items: [] }
}

// Remember whether the documentation sidebar is collapsed (desktop only)
const SIDEBAR_COLLAPSED_KEY = 'wiki:sidebar-collapsed'

function readSidebarCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1'
  } catch (e) {
    return false
  }
}

export default {
  components: { WikiMarkdown, WikiProjectTree, VerticalSplitter },
  data() {
    return {
      site: { ...EMPTY_SITE },
      projectName: null,
      page: null,
      pageLoading: false,
      pageCache: {},
      prefetchTimer: null,
      loadingSite: true,
      error: null,
      sidebarOpen: false,
      sidebarCollapsed: readSidebarCollapsed(),
      creatingWiki: false,
      isPhone: typeof window !== 'undefined'
        && window.matchMedia('(max-width: 479px)').matches,
      collapsedSections: [],
      activeHeading: '',
      searchOpen: false,
      searchQuery: '',
      searchIncludeChildren: true,
      assistantOpen: false,
      assistantIncludeChildren: true,
      assistantChildDepth: 2,
      assistantInput: '',
      assistantLoading: false,
      assistantMessages: [
        {
          role: 'assistant',
          content: 'Hi! I can answer questions using this project\'s documentation. What would you like to know?',
          citations: [],
          suggestions: []
        }
      ],
      assistantSuggestions: [],
      updateStatus: { pending: false, running: false },
      updateTimer: null,
      lastSuccessAt: null,
      refreshing: false,
      feedback: null,
      toast: null,
      toastTimer: null,
      scrollTimer: null
    }
  },
  computed: {
    sidebarVisible() {
      // Phones keep the off-canvas behaviour; desktop just hides the panel.
      return this.isPhone ? this.sidebarOpen : !this.sidebarCollapsed
    },
    // Desktop collapsed state: the sidebar shrinks to a narrow rail.
    sidebarRail() {
      return !this.isPhone && this.sidebarCollapsed
    },
    homeTagline() {
      return this.cleanText(this.site.home?.tagline)
        || this.cleanText(this.site.home?.description)
        || 'Project documentation'
    },
    homeDescription() {
      return this.cleanText(this.site.home?.description)
        || this.cleanText(this.site.project?.description)
        || ''
    },
    landingPage() {
      const homePath = this.site.home?.page
      return homePath && this.page?.path === homePath ? this.page : null
    },
    isHome() {
      return !this.page || Boolean(this.site.home?.page && this.page.path === this.site.home.page)
    },
    projectTree() {
      if (this.site.hierarchy?.length) return this.site.hierarchy
      const fallback = []
      if (this.site.parent_project) fallback.push({ ...this.site.parent_project, depth: 0, children: [] })
      fallback.push({ ...this.site.project, depth: 0, is_current: true, children: [] })
      for (const child of this.site.child_projects || []) {
        fallback.push({ ...child, depth: 1, children: [] })
      }
      return fallback
    },
    flatPages() {
      return (this.site.navigation || []).flatMap(section => section.items || [])
    },
    previousPage() {
      const index = this.flatPages.findIndex(item => item.path === this.page?.path)
      return index > 0 ? this.flatPages[index - 1] : null
    },
    nextPage() {
      const index = this.flatPages.findIndex(item => item.path === this.page?.path)
      return index >= 0 && index < this.flatPages.length - 1 ? this.flatPages[index + 1] : null
    },
    assistantEnabled() {
      return this.site.assistant?.enabled !== false
    },
    projectLinks() {
      const links = []
      if (this.site.parent_project) links.push({ ...this.site.parent_project, relation: 'parent' })
      for (const child of this.site.child_projects || []) links.push({ ...child, relation: child.relation || 'child' })
      return links.filter(link => link.name && link.name !== this.site.project?.name)
    },
    landingStats() {
      const stats = this.site.stats || {}
      return [
        { label: 'Pages', value: stats.pages || 0 },
        { label: 'Architecture', value: stats.domains || 0 },
        { label: 'Guides', value: (stats.pages || 0) - (stats.domains || 0) },
        { label: 'Projects', value: (stats.child_projects || 0) + 1 }
      ]
    },
    searchResults() {
      const query = this.searchQuery.trim().toLowerCase()
      const items = this.site.search?.items?.length
        ? this.site.search.items
        : this.flatPages
      const enriched = items.map(item => {
        const nav = this.flatPages.find(page => page.path === item.path) || {}
        return { ...nav, ...item }
      })
      const filtered = this.searchIncludeChildren
        ? enriched
        : enriched.filter(item => !item.project || item.project === this.site.project?.name)
      if (!query) return filtered.slice(0, 12)
      const terms = query.split(/\s+/).filter(Boolean)
      return filtered
        .map(item => {
          const haystack = `${item.title} ${item.description} ${item.section} ${(item.tags || []).join(' ')}`.toLowerCase()
          const score = terms.reduce((total, term) => total + (haystack.includes(term) ? 1 : 0), 0)
          return { item, score }
        })
        .filter(entry => entry.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 20)
        .map(entry => entry.item)
    },
    updateLabel() {
      if (this.updateStatus.running) return 'Updating docs…'
      if (this.updateStatus.pending) {
        if (this.updateStatus.stalled) return 'Docs update stalled — refresh'
        const next = this.updateStatus.next_run_at ? Math.max(0, this.updateStatus.next_run_at - Math.floor(Date.now() / 1000)) : null
        return next !== null ? `Docs update queued · ${next}s` : 'Docs update queued'
      }
      if (this.updateStatus.manifest?.stale) return 'Docs manifest refreshing'
      if (this.updateStatus.last_error) return 'Last update failed'
      return 'Docs up to date'
    },
    feedbackKey() {
      if (!this.page?.path) return ''
      return `wiki-feedback:${this.projectName}:${this.page.path}`
    }
  },
  watch: {
    assistantOpen(value) {
      if (value) this.$nextTick(() => this.focusAssistant())
    }
  },
  async created() {
    this.projectName = this.site.project?.name || this.$project?.project_name || null
    await this.bootstrap()
  },
  mounted() {
    window.addEventListener('keydown', this.onGlobalKeydown)
    this.phoneMedia = window.matchMedia('(max-width: 479px)')
    this.phoneMedia.addEventListener('change', this.onPhoneMediaChange)
    this.isPhone = this.phoneMedia.matches
    this.updateTimer = setInterval(() => this.pollUpdates(), 15000)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onGlobalKeydown)
    this.phoneMedia?.removeEventListener('change', this.onPhoneMediaChange)
    clearInterval(this.updateTimer)
    clearTimeout(this.toastTimer)
    clearTimeout(this.scrollTimer)
    clearTimeout(this.prefetchTimer)
  },
  methods: {
    api() {
      return this.$storex.api
    },

    // ── bootstrap / project navigation ────────────────────────────────────
    async bootstrap() {
      const params = new URLSearchParams(window.location.search)
      const project = params.get('project') || this.projectName
      const page = params.get('page')
      await this.loadSite(project, page)
    },

    async loadSite(projectName, pagePath = null) {
      this.loadingSite = true
      this.error = null
      try {
        const site = await this.api().wiki.site(projectName)
        const nextProject = site.project?.name || projectName
        if (nextProject !== this.projectName) this.resetAssistant(nextProject)
        this.site = { ...EMPTY_SITE, ...site }
        this.projectName = nextProject
        // Keep long sections (e.g. 100 architecture pages) collapsed by default
        // so the sidebar stays usable; short sections open for quick scanning.
        this.collapsedSections = (this.site.navigation || [])
          .filter(section => (section.items?.length || 0) > 12)
          .map(section => section.title)
        this.assistantSuggestions = this.site.assistant?.suggestions || []
        this.assistantIncludeChildren = this.site.assistant?.search_children !== false
        this.assistantChildDepth = Number(this.site.assistant?.search_depth ?? 2)
        this.searchIncludeChildren = this.site.search?.children !== false
        const initial = pagePath || this.site.home?.page || this.flatPages[0]?.path
        this.loadingSite = false
        if (initial) {
          await this.loadPage(initial, { skipHistory: true })
          this.syncUrl()
        }
        await this.pollUpdates()
      } catch (error) {
        console.error('Wiki site load failed', error)
        this.error = error?.message || 'Could not load the documentation site'
        this.loadingSite = false
      }
    },

    async loadPage(path, options = {}) {
      if (!path) return
      const cacheKey = `${this.projectName}:${path}`
      if (!options.force) {
        const cached = this.pageCache[cacheKey]
        if (cached) {
          this.pageLoading = false
          this.applyPage(cached, options)
          this.schedulePrefetch()
          return
        }
      }
      this.pageLoading = true
      this.error = null
      try {
        const page = await this.api().wiki.page(path, this.projectName)
        this.cachePage(cacheKey, page)
        this.applyPage(page, options)
        this.schedulePrefetch()
      } catch (error) {
        console.error('Wiki page load failed', error)
        this.error = error?.message || 'Could not load this page'
        this.page = null
      } finally {
        this.pageLoading = false
      }
    },

    applyPage(page, options = {}) {
      this.page = page
      this.activeHeading = ''
      if (!options.skipHistory) this.syncUrl()
      this.$nextTick(() => {
        if (this.$refs.scroller) this.$refs.scroller.scrollTop = 0
      })
      this.feedback = localStorage.getItem(this.feedbackKey)
    },

    cachePage(key, page) {
      if (!page) return
      this.pageCache[key] = page
      const keys = Object.keys(this.pageCache)
      if (keys.length > 40) delete this.pageCache[keys[0]]
    },

    schedulePrefetch() {
      clearTimeout(this.prefetchTimer)
      this.prefetchTimer = setTimeout(() => {
        for (const candidate of [this.previousPage, this.nextPage]) {
          if (candidate) this.prefetchPage(candidate.path)
        }
      }, 350)
    },

    async prefetchPage(path) {
      if (!path) return
      const key = `${this.projectName}:${path}`
      if (this.pageCache[key]) return
      try {
        const page = await this.api().wiki.page(path, this.projectName)
        this.cachePage(key, page)
      } catch {
        // Prefetch is best effort.
      }
    },

    async selectProject(name) {
      if (!name) return
      this.page = null
      this.closeProjectMenu()
      this.sidebarOpen = false
      await this.loadSite(name)
    },

    openPage(path) {
      if (!path) return
      this.loadPage(path)
      this.sidebarOpen = false
    },

    syncUrl() {
      const params = new URLSearchParams()
      if (this.projectName && this.projectName !== this.$project?.project_name) {
        params.set('project', this.projectName)
      }
      if (this.page?.path) params.set('page', this.page.path)
      const query = params.toString()
      const url = `${window.location.pathname}${query ? `?${query}` : ''}`
      window.history.replaceState({}, '', url)
    },

    onPhoneMediaChange(event) {
      this.isPhone = event.matches
      if (!this.isPhone) this.sidebarOpen = false
    },
    // Collapse/expand the documentation sidebar (desktop) and remember it.
    toggleSidebarCollapse() {
      this.sidebarCollapsed = !this.sidebarCollapsed
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, this.sidebarCollapsed ? '1' : '0')
      } catch (e) {
        // Storage may be unavailable (private mode) — ignore
      }
    },
    closeProjectMenu() {
      if (this.$refs.projectMenu) this.$refs.projectMenu.open = false
    },

    // ── navigation helpers ───────────────────────────────────────────────
    isActive(path) {
      return this.page?.path === path
    },
    toggleSection(title) {
      const index = this.collapsedSections.indexOf(title)
      if (index >= 0) this.collapsedSections.splice(index, 1)
      else this.collapsedSections.push(title)
    },
    isSectionCollapsed(title) {
      return this.collapsedSections.includes(title)
    },
    scrollToHeading(id) {
      const element = document.getElementById(id)
      if (element) element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      this.activeHeading = id
    },
    onScroll() {
      clearTimeout(this.scrollTimer)
      this.scrollTimer = setTimeout(() => {
        if (!this.$refs.scroller || !this.page?.headings?.length) return
        const scrollerTop = this.$refs.scroller.getBoundingClientRect().top
        let active = ''
        for (const heading of this.page.headings) {
          const element = document.getElementById(heading.id)
          if (!element) continue
          if (element.getBoundingClientRect().top - scrollerTop <= 120) active = heading.id
        }
        this.activeHeading = active
      }, 60)
    },

    // ── search ───────────────────────────────────────────────────────────
    openSearch() {
      this.searchOpen = true
      this.searchQuery = ''
      this.$nextTick(() => this.$refs.searchInput?.focus())
    },
    closeSearch() {
      this.searchOpen = false
    },
    openSearchResult(result) {
      this.closeSearch()
      if (result.project && result.project !== this.site.project?.name) {
        this.loadSite(result.project, result.path)
      } else {
        this.openPage(result.path)
      }
    },
    onGlobalKeydown(event) {
      const key = event.key.toLowerCase()
      if ((event.metaKey || event.ctrlKey) && key === 'k') {
        event.preventDefault()
        this.openSearch()
      }
      if (key === 'escape') {
        this.searchOpen = false
        this.sidebarOpen = false
      }
    },

    // ── assistant ────────────────────────────────────────────────────────
    resetAssistant(projectName) {
      this.assistantMessages = [{
        role: 'assistant',
        content: `Hi! I can answer questions using the ${projectName || 'project'} documentation. What would you like to know?`,
        citations: [],
        suggestions: []
      }]
      this.assistantInput = ''
      this.assistantLoading = false
    },
    toggleAssistant(force) {
      this.assistantOpen = force === undefined ? !this.assistantOpen : force
    },
    focusAssistant() {
      this.resizeAssistantInput()
      this.$refs.assistantInput?.focus()
    },
    resizeAssistantInput() {
      const element = this.$refs.assistantInput
      if (!element) return
      element.style.height = 'auto'
      element.style.height = `${Math.min(112, element.scrollHeight)}px`
    },
    askAboutPage() {
      if (!this.page) return
      this.toggleAssistant(true)
      this.askAssistant(`Explain "${this.page.title}" with a concrete example.`)
    },
    async askAssistant(question) {
      const text = (question || this.assistantInput || '').trim()
      if (!text || this.assistantLoading) return
      this.assistantInput = ''
      this.$nextTick(this.resizeAssistantInput)
      this.assistantMessages.push({ role: 'user', content: text, citations: [] })
      this.assistantLoading = true
      this.scrollAssistantToBottom()
      try {
        const history = this.assistantMessages
          .filter(message => message.role === 'user' || message.citations?.length)
          .slice(-8)
          .map(message => ({ role: message.role, content: message.content }))
        const response = await this.api().wiki.assistant({
          question: text,
          project: this.projectName,
          page: this.page?.path,
          include_children: this.assistantIncludeChildren,
          child_depth: this.assistantChildDepth,
          history
        })
        this.assistantMessages.push({
          role: 'assistant',
          content: response.answer || 'I could not find an answer in the docs.',
          citations: response.citations || [],
          suggestions: response.suggestions || []
        })
        if (response.suggestions?.length) this.assistantSuggestions = response.suggestions
      } catch (error) {
        console.error('Wiki assistant failed', error)
        this.assistantMessages.push({
          role: 'assistant',
          content: 'I could not reach the documentation assistant. Please try again in a moment.',
          citations: []
        })
      } finally {
        this.assistantLoading = false
        this.scrollAssistantToBottom()
      }
    },
    openCitation(citation) {
      if (!citation || citation.type !== 'wiki') return
      if (citation.project && citation.project !== this.site.project?.name) {
        this.loadSite(citation.project, citation.path)
      } else {
        this.openPage(citation.path)
      }
    },
    scrollAssistantToBottom() {
      this.$nextTick(() => {
        const element = this.$refs.assistantScroll
        if (element) element.scrollTop = element.scrollHeight
      })
    },

    async createWiki() {
      if (this.creatingWiki) return
      this.creatingWiki = true
      this.error = null
      try {
        const response = await this.api().wiki.create({ project: this.projectName })
        const created = response?.site || response
        if (created?.navigation) this.site = { ...EMPTY_SITE, ...created }
        await this.loadSite(this.projectName)
        this.showToast('Wiki created — detailed pages are being generated')
      } catch (error) {
        console.error('Wiki creation failed', error)
        this.error = error?.message || 'Could not create the wiki'
      } finally {
        this.creatingWiki = false
      }
    },
    openWikiSettings() {
      const ui = this.$storex?.ui
      if (ui?.openApp) {
        ui.openApp({ appKey: 'knowledge_settings', payload: { tab: 'wiki' } })
      } else {
        this.$ui.setActiveTab('knowledge_settings')
      }
    },

    // ── background updates ───────────────────────────────────────────────
    async pollUpdates() {
      try {
        const status = await this.api().wiki.updates(this.projectName)
        const previousSuccess = this.lastSuccessAt
        this.updateStatus = status || {}
        this.lastSuccessAt = status?.last_success_at || null
        if (previousSuccess && this.lastSuccessAt && this.lastSuccessAt !== previousSuccess) {
          // Pages were regenerated: drop cached copies so navigation shows the
          // new content, then reload the current page.
          this.pageCache = {}
          const current = this.page?.path
          await this.loadSite(this.projectName, current)
        }
      } catch {
        // Status polling is best effort; never disrupt reading.
      }
    },
    async requestRefresh() {
      if (this.refreshing) return
      this.refreshing = true
      try {
        // Queue rather than run in the request: a real regeneration can take
        // longer than the HTTP timeout. The poll loop reloads the page when the
        // scheduler reports a successful run.
        await this.api().wiki.update({
          project: this.projectName,
          action: 'schedule',
          debounce_seconds: 1
        })
        this.showToast('Documentation refresh queued')
        await this.pollUpdates()
      } catch (error) {
        console.error('Wiki refresh failed', error)
        this.showToast('Could not refresh the documentation')
      } finally {
        this.refreshing = false
      }
    },

    // ── page utilities ───────────────────────────────────────────────────
    formatDate(timestamp) {
      if (!timestamp) return ''
      return new Date(timestamp * 1000).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    },
    cleanText(value) {
      return String(value || '')
        .replace(/\{\{\s*\w+\s*\}\}/g, ' ')
        .replace(/project'?s path is:\s*['"]?\s*['"]?/gi, ' ')
        .replace(/\s+/g, ' ')
        .trim()
    },
    openSource(source) {
      if (!this.$ui?.openFile) return
      const absolute = source.startsWith('/') || !this.$project?.abs_project_path
        ? source
        : `${this.$project.abs_project_path.replace(/\/$/, '')}/${source}`
      this.$ui.openFile(absolute)
    },
    async copyLink() {
      try {
        await navigator.clipboard.writeText(window.location.href)
        this.showToast('Link copied')
      } catch {
        this.showToast('Could not copy the link')
      }
    },
    sendFeedback(value) {
      const key = this.feedbackKey
      if (key) localStorage.setItem(key, value)
      this.feedback = value
      this.showToast(value === 'yes' ? 'Thanks for the feedback!' : 'Thanks — we will improve this page.')
    },
    showToast(message) {
      this.toast = message
      clearTimeout(this.toastTimer)
      this.toastTimer = setTimeout(() => { this.toast = null }, 2500)
    }
  }
}
</script>

<style scoped>
.wiki-shell {
  --wiki-sidebar-width: 18rem;
}
.wiki-sidebar {
  scrollbar-width: thin;
}
.wiki-sidebar nav::-webkit-scrollbar,
main::-webkit-scrollbar,
aside ::-webkit-scrollbar {
  width: 6px;
}
.status-dot {
  display: inline-block;
  height: 0.45rem;
  width: 0.45rem;
  border-radius: 9999px;
  background: #22c55e;
}
.status-dot.is-busy {
  background: #f59e0b;
  animation: wiki-pulse 1.2s ease-in-out infinite;
}
.status-badge {
  display: inline-block;
  height: 0.45rem;
  width: 0.45rem;
  flex-shrink: 0;
  border-radius: 9999px;
  background: #94a3b8;
}
.status-badge.status-ready { background: #22c55e; }
.status-badge.status-pending { background: #f59e0b; }
.status-badge.status-disabled { background: #94a3b8; }
@keyframes wiki-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}
</style>