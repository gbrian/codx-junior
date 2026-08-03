import Service from "./service"

export class ProjectService extends Service {
  async cloneProject(projectPath) {
    if (projectPath.includes("github.com") &&
        projectPath.includes("/issues/")) {
        projectPath = projectPath.split("/issues/")[0]
    } 
    await this.$projects.createNewProject(projectPath)
  }
  
  async watch(watching) {
    this.$project.$api.projects.watch(watching)
  }

  async openUserChat(user) {
    const chat = this.$projects.allChats.find(({ column, board, name }) => 
      column === "chats" && board === "chats" && name === user.username
    ) ||  await this.$chats.createNewChat({
      board: "chats",
      column: "chats",
      name: user.username,
      mode: 'channel'
    })
    this.$projects.setActiveChat(chat)
   
    if (this.$ui.activeTab !== 'tasks') {
      this.$ui.setActiveTab('tasks')
    }
  }

  findParentProject(project) {
    const  { allProjects } = this.$storex.api
    return allProjects.find(p =>
      p.abs_project_path !== project.abs_project_path && 
      project.abs_project_path.startsWith(p.abs_project_path))
  }

  findChildProject(project) {
    const  { allProjects } = this.$storex.api
    return allProjects.filter(p => 
      p.abs_project_path !== project.abs_project_path && 
      p.abs_project_path.startsWith(project.abs_project_path))
  }

  findProjectDependencies(project) {
    const  { allProjects } = this.$storex.api
    const { project_dependencies } = project
    return `${project_dependencies}`.split(",").map(dep => 
      allProjects.find(({ project_name }) => project_name === dep.trim()))
                          .filter(p => !!p)
  }

  async searchProjectFiles(project, searchQuery, limit = 20) {
    const relatedProjects = this.getRelatedProjects(project)
    const allProjectsToSearch = [project, ...relatedProjects]
    
    const fileResults = []
    const seenFiles = new Set()

    for (const proj of allProjectsToSearch) {
      if (!proj?.$api) continue
      
      try {
        const results = await proj.$api.files.search({
          search: searchQuery,
          pageSize: limit,
          page: 0
        })
        
        if (results?.files) {
          for (const file of results.files) {
            const key = file.path?.toLowerCase() || file
            if (!seenFiles.has(key)) {
              seenFiles.add(key)
              fileResults.push({
                file: file.path || file,
                name: (file.path || file).split('/').reverse()[0],
                project: proj,
                searchIndex: (file.path || file).split('/').reverse().slice(0, 3).reverse().join('/')
              })
            }
          }
        }
      } catch (ex) {
        console.error(`Error searching files in project ${proj.project_name}:`, ex)
      }
    }

    return fileResults.slice(0, limit)
  }

  getRelatedProjects(project) {
    const { project_id, abs_project_path } = project
    const allProjects = this.$storex.projects.allProjects

    const subProjects = allProjects.filter(p =>
      p.project_id !== project_id &&
      p.abs_project_path?.startsWith(abs_project_path)
    )

    const dependencies = this.findProjectDependencies(project)

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

  async mentionList(project, profiles) {
    const parentProject = this.findParentProject(project)
    const childProjects = this.findChildProject(project)
    const projectDependencies = this.findProjectDependencies(project)
    return [
      ...this.$storex.api.userNetwork.map(user => ({ 
        name: user.username,
        user,
        tooltip: `User @${user.username}` 
      })),
      ...profiles.map(profile => ({ 
          name: profile.name,
          profile,
          tooltip: profile.description 
        })),
      ...[
        project,
        parentProject,
        ...childProjects,
        ...projectDependencies,
      ]
        .filter(project => project)
        .map(project => ({ name: project.project_name, project, tooltip: `Search in project ${project.project_name}` })),
    ].map(m => ({ 
      ...m,
      searchIndex: m.searchIndex || m.name.toLowerCase(),
      mention: encodeURIComponent(m.name)
    }))
  }

  async loadProjectContext(project) {
    const { project_name, codx_path } = project
    if ( project_name && !codx_path ) {
      project = this.$storex.projects.allProjects.find(p => p.project_name === project_name)
    }

    const API = await this.$storex.api.project(project)
    const [models, profiles ] = await Promise.all([
      API.projects.ai.models.list(),
      API.profiles.list(),
    ])
    const mentionList = await this.mentionList(project, profiles)
    return {
      ...project,
      api: API,
      models,
      profiles,
      mentionList
    }
  }
}