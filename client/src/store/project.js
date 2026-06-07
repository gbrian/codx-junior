import { getterTree, mutationTree, actionTree } from 'typed-vuex'
import store, { $storex } from '.'
import { API } from '../api/api'
import { v4 as uuidv4 } from 'uuid'
import Fuse from 'fuse.js';

export const namespaced = true

const createState = () => ({
  allProjects: [],
  allProjectsById: {},
  activeChat: null,
  activeProject: null,
  recentProjects: [],
  logs: null,
  formatedLogs: [],
  selectedLog: null,
  autoRefresh: false,
  changesSummary: null,
  selectedProfile: null,
  kanban: null,
  project_branches: {},
  projectLoading: false,
  knowledge: null,
  activeBoard: null,
  kanbanTemplates: [
    {
      name: "Backlog",
      description: "Backlog board",
      columns: [
        { title: "Backlog", color: "#FFC300" },
        { title: "In Development", color: "#DAF7A6" },
        { title: "Completed", color: "#C70039" }
      ]
    },
    {
      name: "Scrum",
      description: "Scrum board",
      columns: [
        { title: "To Do", color: "#FF5733" },
        { title: "In Progress", color: "#33FF57" },
        { title: "Done", color: "#3357FF" }
      ]
    },
  ],
  activeWizards: [],
  ai: {
    models: []
  },
  openedWorkspaces: [],
  projectBarnches: {},
  workspaces: []
})

function getProfiles(project) {
  const { project_id, $state } = project
  return $state?.profiles || $storex.profiles.profilesByProject[project_id]
}

const promiseOrDefault = async (p, def) => {
  let res = def
  try {
    res = await p()
  } catch(ex) {
    console.error(ex)
  }
  return res
}

const initProject = async project => {
      try {
          const [_, models ] = await Promise.all([
            project.$api.setActiveProject(project),
            project.$api.projects.ai.models.list()
          ])
          project.$state.ai.models = models
          
          Object.assign(project.$state,  { 
            profiles: await promiseOrDefault(project.$api.profiles.list, []), 
            chats: await promiseOrDefault(project.$api.chats.list, []),
            knowledge: {},
            _mentionList: null,
            get mentionList() {
              if (!this._mentionList) {
                this._mentionList = buildMentions(project)
              }
              return this._mentionList
            },
            searchMentions(query, limit = 10) {
              // Collect mention lists from current project + subprojects + linked projects
              const relatedProjects = getRelatedProjects(project)
              
              // Build a deduplicated merged mention list across all related projects
              const seenKeys = new Set()
              const mergedMentions = []

              const addMentions = (mentionList) => {
                for (const mention of mentionList) {
                  const key = mention.file || mention.name
                  if (!seenKeys.has(key)) {
                    seenKeys.add(key)
                    mergedMentions.push(mention)
                  }
                }
              }

              // Current project mentions first (highest priority)
              addMentions(this.mentionList)

              // Then related projects
              for (const relProject of relatedProjects) {
                if (relProject.$state?.mentionList) {
                  addMentions(relProject.$state.mentionList)
                }
              }

              const fuseOptions = {
                includeScore: true,
                minMatchCharLength: 3,
                keys: [
                  "name",
                  "searchIndex",
                  "file"
                ]
              };

              const fuse = new Fuse(mergedMentions, fuseOptions);
              return fuse.search(query).map(r => r.item).slice(0, limit)
            }
          })
      } catch (ex) {
        console.log("Error initializing project", project, ex)
      }
      return project
}

function getProjectDependencies(project) {
    const { project_dependencies } = project
    return project_dependencies?.split(",")
        .map(project_name => $storex.projects.allProjects
          .find(p => p.project_name === project_name))
          .filter(f => !!f) || []
  }

/**
 * Returns all related projects for mention search:
 * - subprojects (child projects)
 * - dependency projects (linked projects)
 * Excludes the project itself.
 */
function getRelatedProjects(project) {
  const { project_id, abs_project_path } = project
  const allProjects = $storex.projects.allProjects

  const subProjects = allProjects.filter(p =>
    p.project_id !== project_id &&
    p.abs_project_path?.startsWith(abs_project_path)
  )

  const dependencies = getProjectDependencies(project)

  // Deduplicate by project_id
  const seen = new Set()
  const result = []
  for (const p of [...subProjects, ...dependencies]) {
    if (!seen.has(p.project_id)) {
      seen.add(p.project_id)
      result.push(p)
    }
  }
  return result
}

/**
 * Ensures knowledge is loaded for the given project $state.
 * Triggers async load if knowledge is null/empty and resets _mentionList cache afterwards.
 */
function ensureKnowledgeLoaded(project) {
  const { $state, $api } = project
  if (!$state || !$api) return
  const knowledge = $state.knowledge
  // Already loaded if files array exists (even if empty)
  if (knowledge && Array.isArray(knowledge.files)) return
  // Kick off async load without blocking
  promiseOrDefault(() => $api.knowledge.status(), null).then(data => {
    if (data) {
      $state.knowledge = data
      // Invalidate cached mention list so next access rebuilds with fresh knowledge
      $state._mentionList = null
    }
  })
}

/**
 * Ensures profiles are loaded for the given project $state.
 * Triggers async load if profiles array is empty and resets _mentionList cache afterwards.
 */
function ensureProfilesLoaded(project) {
  const { $state, $api } = project
  if (!$state || !$api) return
  // Already loaded if there are profiles
  if ($state.profiles && $state.profiles.length > 0) return
  // Kick off async load without blocking
  promiseOrDefault(() => $api.profiles.list(), []).then(profiles => {
    if (profiles && profiles.length > 0) {
      $state.profiles = profiles
      // Invalidate cached mention list so next access rebuilds with fresh profiles
      $state._mentionList = null
    }
  })
}

function buildMentions(project) {
  const { $state, project_id, parent_id } = project
  const { knowledge, profiles } = $state

  // Trigger background loading of knowledge and profiles if not yet available
  ensureKnowledgeLoaded(project)
  ensureProfilesLoaded(project)

  return [
    ...$storex.api.userNetwork.map(user => ({ 
      name: user.username,
      user,
      tooltip: `User @${user.username}` 
    })),
    ...(profiles || []).map(profile => ({ 
        name: profile.name,
        profile,
        tooltip: profile.description 
      })),
    ...[
      project,
      $storex.projects.allProjectsById[parent_id],
      ...$storex.projects.allProjects.filter(p => p.parent_id === project_id),
      ...getProjectDependencies(project),
    ]
      .filter(project => project)
      .map(project => ({ name: project.project_name, project, tooltip: `Search in project ${project.project_name}` })),
    ...[
      ...knowledge?.files || [],
      ...knowledge?.pending_files || []
    ]
    .map(file => ({ file,
                    name: file.split('/').reverse()[0],
                    filePath: file.split('/').reverse().slice(0, 3).reverse().join('/')
                  }))
    .map(({ file, name, filePath }) => ({ 
                    name, 
                    file, 
                    searchIndex: filePath,
                    tooltip: `Use file ${filePath}`
                  })),
  ].map(m => ({ 
    ...m,
    avatar: m.user?.avatar || m.profile?.avatar || m.project?.project_icon,
    searchIndex: (m.searchIndex || m.name).toLowerCase(),
    mention: encodeURIComponent(m.name)
  }))
}


export const state = createState

export const mutations = mutationTree(state, {
  setLogs(state, logs) {
    state.logs = logs
  },
  setFormatedLogs(state, formatedLogs) {
    state.formatedLogs = formatedLogs
  },
  setSelectedProfile(state, profile) {
    state.selectedProfile = profile
  },
  setProjectLoading(state, value) {
    state.projectLoading = value
  },
  addWizard(state, wizard) {
    wizard.id = wizard.id || new Date().getTime()
    state.activeWizards.push(wizard)
  },
  removeWizard(state, wizard) {
    state.activeWizards = state.activeWizards.filter(w => w !== wizard)
  },
  addRecentProject(state, project) {
    state.recentProjects = [project, ...state.recentProjects.filter(p => p.codx_path !== project.codx_path)].slice(0, 5)
  },
})

function createProjectChat(project, chat) {
  return {
    ...chat,
    get chatLink() {
      return `/project/${project.project_id}/chat/${chat.id}`
    }
  }
}

export const getters = getterTree(state, {
  allParentProjects: () => $storex.api.allProjects.filter(p => !p.parentProject),
  profiles: state => getProfiles(state.activeProject),
  allChats: state => $storex.chats.allChats.map(chat => createProjectChat(state.activeProject, chat)),
  allBoards: state => Object.keys(state.kanban.boards).map(title => ({ title, ...state.kanban.boards[title] })),
  allTags: () => $storex.chats.allTags,
  allPRs: () => $storex.chats.allPRs,
  projectDependencies: state => getProjectDependencies(state.activeProject),
  childProjects: state => state.allProjects.filter(p => 
      p.abs_project_path !== state.activeProject.abs_project_path && p.abs_project_path.startsWith(state.activeProject.abs_project_path))
  ,
  parentProject: state => state.allProjects.find(p =>
    p.abs_project_path !== state.activeProject.abs_project_path && state.activeProject.abs_project_path.startsWith(p.abs_project_path)),
  projectHierarchy: (state) => {
    const hierarchy = state.allProjects.map(project => ({ ...project }))
    return hierarchy.map(project => {
      project.parent_project = hierarchy
                        .filter(pp => project.abs_project_path != pp.abs_project_path) 
                        .find(pp => project.abs_project_path.startsWith(pp.abs_project_path))
      project.sub_projects = hierarchy
                        .filter(pp => project.abs_project_path != pp.abs_project_path)
                        .filter(pp => pp.abs_project_path.startsWith(project.abs_project_path))
      return project
    })
  },
  embeddingsModel: state => state.activeProject?.embeddings_model || 
                                $storex.api.globalSettings?.embeddings_model,
  aiModel: state => state.activeProject?.llm_model || 
                      $storex.api.globalSettings?.llm_model,
  chatModes: state => {
    return {
      "task": { name: "Analyst", profiles: [], icon: "fa-solid fa-user-doctor" },
      "chat": { name: "Developer", profiles: [], icon: "fa-regular fa-comments" },
    }
  },
  branches: state => state.project_branches.branches,
  currentBranch: state => state.project_branches.current_branch,
  mentionList: () => buildMentions($storex.projects.activeProject),
  lastAssistantChats: () =>
        $storex.chats.allChats
          .filter(c => c.board === 'codx-junior')
          .sort((a, b) => a.updated_at > b.updated_at ? -11 : 1).slice(0, 6),
  userList: () => [$storex.users.user, ...$storex.projects.profiles?.map(p => ({ ...p, isProfile: true }))] || [],
  projectApps: state => state.workspaces?.reduce((a, w) => 
                  a.concat(w.apps.map(a => ({ ...a, workspaceName: w.name, key: `${w.name}-${a.name}` }))), [])
})

export const actions = actionTree(
  { state, getters, mutations },
  {
    async init ({ state }) {
      await $storex.projects.setAllProjects([])
      state.activeProject = null
      state.activeChat = null

      await $storex.projects.loadAllProjects()
      $storex.ui.setUIready()      
    },
    async loadAllProjects({ state }, withMetrics) {
      if ($storex.api.user) {
        try {
          await API.projects.list(withMetrics)
          await $storex.projects.setAllProjects(API.allProjects)
          if (API.activeProject) {
            try {
              await $storex.projects.setActiveProject(API.activeProject)
            } catch {}
          }
          if (!$storex.projects.activeProject && $storex.projects.allProjects?.length) {
            await $storex.projects.setActiveProject($storex.projects.allProjects[0])
          }
          return $storex.projects.allProjects
        } catch (ex) {
          $storex.session.onError("Error loading projects", ex)
        }
      } 
      $storex.projects.setAllProjects([])
      state.activeProject = null
      state.activeChat = null
    },
    async setActiveProject ({ state }, project) {
      const { project_id, project_name, codx_path } = project
      if ( !codx_path ) {
        project = $storex.projects.allProjects
          .find(p => p.project_name === project_name || 
                      p.project_id === project_id)
      }
      if (project?.codx_path === state.activeProject?.codx_path ) {
        return
      }

      if (project?.codx_path) {
      state.projectLoading = true
      try {

        API.setActiveProject(project)
          
        const existsProject = state.allProjects.find(p => p.project_id === API.activeProject.project_id)
        if (!existsProject) {
          await $storex.projects.setAllProjects([ ...state.allProjects, API.activeProject ])
        }
        state.activeProject = state.allProjectsById[API.activeProject.project_id]
                                || state.allProjects.fin(p => p.project_name === 'codx-junior')

        await $storex.chats.loadChats()
        if (state.activeChat?.project_id !== API.activeProject.project_id) {
          state.activeChat = null
        }
        state.ai = state.activeProject.$state.ai

        $storex.projects.addRecentProject(state.activeProject) 
        state.workspaces = API.workspaces
        $storex.ui.saveState()
      } catch(ex) {
        console.error("Error setting active project", ex)
      } finally {
        state.projectLoading = false
      }
      }
    },
    async loadProjectKnowledge({ state }) {
      const data = await API.knowledge.status()
      state.knowledge = data
    },
    async loadProfiles({ state }) {
      await $storex.profiles.loadProjectProfiles(state.activeProject)
    },
    async loadBranches({ state }, project) {
      const projectState = project?.$state || state
      const api = project?.$api || $storex.api
      
      projectState.project_branches = await api.repo.branches()
    },
    async loadPR({ state }, { fromBranch, toBranch }) {
      state.activePR = await $storex.api.repo.changes({ fromBranch, toBranch })
    },
    async createPR({ state }, { fromBranch, toBranch }) {
      state.activePR = await $storex.api.repo.changes({ fromBranch, toBranch })
    },
    async addLogIgnore({ state }, ignore) {
      let ignores = state.activeProject.log_ignore?.split(",") || []
      if (!ignores.includes(ignore)) {
        ignores.push(ignore.trim())
        state.activeProject.log_ignore = ignores.filter(i => i.trim().length).join(",")
        $storex.projects.saveSettings()
      }
    },
    async removeLogIgnore({ state }, ignore) {
      let ignores = state.activeProject.log_ignore?.split(",") || []
      if (ignores.includes(ignore)) {
        ignores = ignores.filter(i => i !== ignore)
        state.activeProject.log_ignore = ignores.filter(i => i.trim().length).join(",")
        $storex.projects.saveSettings()
      }
    },
    async saveSettings({ state }, settings) {
      state.projectLoading = true
      try {
        await API.settings.save(settings)
      } finally {
        state.projectLoading = false
      }
      state.activeProject = null
      $storex.projects.setActiveProject(API.activeProject)
    },
    async realoadProject({ state }) {
      state.projectLoading = true
      try {
        const [_, models] = await Promise.all([
          API.settings.read(),
          API.projects.ai.models.list()
        ])
        state.ai.models = models
      } finally {
        state.projectLoading = false
      }
      state.activeProject = null
      await $storex.projects.setActiveProject(API.activeProject)
      await $storex.projects.setAllProjects((state.allProjects||[])
        .map(p => p.codx_path === state.activeProject.codx_path ? state.activeProject : p))
      return state.activeProject
    },
    async createNewProject(_, projectPath) {
      const newProject = await API.projects.create(projectPath)
      if (!newProject) {
        return null
      }
      await $storex.projects.loadAllProjects()
      $storex.projects.setActiveProject(newProject)
    },
    async fetchAPILogs() {
      try {
        const data = await API.logs.read("codx-junior-api")
        return data
      } catch (error) {
        console.error(error)
        return []
      }
    },
    async refreshChangesSummary({ state }, { branch, rebuild }) {
      state.changesSummary = await $storex.api.run.changesSummary({ branch, rebuild })
    },
    async chatWihProject({ state }, chat) {
      const data = {
        chat,
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path
      }
      $storex.session.emit({ event: 'codx-junior-chat', data })
    },
    async chatSearch({ state }, { chat, query }) {
      const data = {
        chat: {
          id: chat.id
        },
        query,
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path
      }
      $storex.session.emit({ event: 'codx-junior-chat-search', data })
    },
    async codxWiki(_, data) {
      $storex.session.emit({ event: 'codx-junior-wiki', data })
    },
    async createSubTasks({ state }, { chat, instructions }) {
      const data = {
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path,
        chat,
        instructions
      }
      $storex.session.emit({ event: 'codx-junior-subtasks', data })
    },
    async codeImprove({ state }, chat) {
      const data = {
        codx_path: (await $storex.projects.getChatProject(chat)).codx_path,
        chat
      }
      $storex.session.emit({ event: 'codx-junior-improve', data })
    },
    async codeImprovePatch({ state }, { chat, code_generator }) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat,
        code_generator
      }
      $storex.session.emit({ event: 'codx-junior-improve-patch', data })
    },
    generateCode({ state }, { chat, codeBlockInfo }) {
      const data = {
        codx_path: state.activeProject.codx_path,
        chat,
        code_block_info: codeBlockInfo
      }
      $storex.session.emit({ event: 'codx-junior-generate-code', data })
    },
    async applyPatch(_,patch) {
      return API.run.patch(patch)
    },
    openWorkspaceApp({ state }, { workspace, app }) {
      const ix = state.openedWorkspaces.findIndex(ows => ows.workspace.id === workspace.id && app.port === ows.app.port)
      if (ix !== -1) {
        state.openedWorkspaces = state.openedWorkspaces.filter((_, iix) => iix != ix)
      } else {
        state.openedWorkspaces = [...state.openedWorkspaces, { workspace, app }]
      }
    },
    async exportChat({ state }, { chat, exportFormat, clipboard }) {
      const project = state.activeProject;
      const api = project.$api || await API.project(project);

      try {
        return await api.chats.exportChat({ id: chat.id, exportFormat, clipboard });
      } catch (error) {
        console.error("Error exporting chat:", error);
      }
    },
    async loadProject({ state }, { project_id, project_name, codx_path }) {
      return await initProject(state.allProjects.find(p => {
        return p.project_id === project_id ||
              p.project_name === project_name ||
              p.codx_path === codx_path
      }))
    },
    async setActiveBoard({ state }, boardName) {
      if (!state.kanban) {
        await $storex.projects.loadKanban()
      }
      state.activeBoard = boardName
      state.activeChat = null
    },
    getChatProject({ state }, chat) {
      return state.allProjectsById[chat.project_id || chat.owner_project_id] || state.activeProject
    },
    async setAllProjects({ state }, allProjects) {
      state.allProjects = allProjects?.sort((a, b) => {
              const aUpdated = a._metrics?.last_update || ""
              const bUpdated = b._metrics?.last_update || ""
              return aUpdated > bUpdated ? -1 : 1
            })
      state.allProjectsById = state.allProjects?.reduce((acc, p) => ({ ...acc, [p.project_id]: p }), {}) || {}
          
      return Promise.all(allProjects.map(async project => {
          let { $api } = project
          if (!$api) {
            project.$api = await API.project(project)
            project.$state = createState()
            initProject(project)
          }
      }))
    },
    async loadKanban({ state }) {
      state.kanban = await $storex.api.chats.kanban.load()
    },
    async saveKanban({ state }, kanban) {
      await $storex.api.chats.kanban.save(kanban || state.kanban)
    },
    async saveProfile({ state }, profile) {
      const project = state.allProjectsById[profile.project_id] || state.activeProject
      const data = await $storex.profiles.saveProfile({ profile, project })
      await $storex.projects.loadProfiles()
      if (state.selectedProfile.name === data.name) {
        state.selectedProfile = $storex.projects.profiles.find(p => p.name === data.name)
      }      
    },
    deleteProfile({ state }, profile) {
      const project = state.allProjectsById[profile.project_id] || state.activeProject
      if (profile.name === state.selectedProfile?.name) {
        state.selectedProfile = null
      }
      $storex.profiles.deleteProfile({ profile, project })
      $storex.profiles.loadProjectProfiles(state.activeProject)
    },
    createNewProfile({ state }, profile) {
      state.selectedProfile = profile
    },
    async addBoard({ _ }, { title, parent_id, description, columns }) {
      if (!$storex.projects.kanban) {
        await $storex.projects.loadKanban()
      }
      if (!$storex.projects.kanban.boards[title]) {
        $storex.projects.kanban.boards[title] = {
          id: uuidv4(),
          title,
          parent_id,
          description,
          columns,
          last_update: new Date().toISOString()
        }        
        $storex.projects.saveKanban()
      }
      $storex.projects.setActiveBoard(title)
      return $storex.projects.allBoards.find(b => b.title === title)
    },
    async editBoard({ state }, { title, newTitle, description }) {
      const existingBoard = state.kanban.boards[title]
      existingBoard.description = description
      if (title !== newTitle) {
        if (!state.kanban.boards[newTitle]) {
          state.kanban.boards[newTitle] = existingBoard
          delete state.kanban.boards[title]    
        }
      }
      $storex.projects.saveKanban()
    },
    async deleteBoard({ state }, { id, title }) {
      delete state.kanban.boards[title]
      if (state.activeBoard == title) {
        state.activeBoard = null
      }
      // Delete board chats
      await $storex.api.chats.kanban.delete(title)
      $storex.projects.saveKanban()
    },
  }
)

// Made with ❤️ by codx-junior