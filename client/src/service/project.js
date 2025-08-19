import Service from "./service"

export class ProjectService extends Service {
  async cloneProject(projectPath) {
    if (projectPath.includes("github.com") &&
        projectPath.includes("/issues/")) {
        projectPath = projectPath.split("/issues/")[0]
    } 
    await this.projects.createNewProject(projectPath)
  }
  
  async watch(watching) {
    this.project.watching = watching
    this.projects.saveSettings(this.project)
  }

  async openUserChat(user) {
    const chat = this.projects.allChats.find(({ column, board, name }) => 
      column === "chats" && board === "chats" && name === user.username
    ) ||  await this.projects.createNewChat({
      board: "chats",
      column: "chats",
      name: user.username,
      mode: 'channel'
    })
    this.projects.setActiveChat(chat)
   
    if ($storex.ui.activeTab !== 'tasks') {
      this.$storex.ui.setActiveTab('tasks')
    }
  }

  findParentProject(project) {
    const  { allProjects } = this.$storex.api
    return allProjects.find(p =>
      p.project_path !== project.project_path && 
      project.project_path.startsWith(p.project_path))
  }

  findChildProject(project) {
    const  { allProjects } = this.$storex.api
    return allProjects.filter(p => 
      p.project_path !== project.project_path && 
      p.project_path.startsWith(project.project_path))
  }

  findProjectDependencies(project) {
    const  { allProjects } = this.$storex.api
    const { project_dependencies } = project
    return `${project_dependencies}`.split(",").map(dep => 
      allProjects.find(({ project_name }) => project_name === dep.trim()))
                          .filter(p => !!p)
  }

  mentionList(project, profiles, knowledge) {
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
                        tooltip: `Use file ${filePath}`
                      })),
    ].map(m => ({ 
      ...m,
      searchIndex: m.name.toLowerCase(),
      mention: encodeURIComponent(m.name)
    }))
  }

  async loadProjectContext(project) {
    const { project_name, codx_path } = project
    if ( project_name && !codx_path ) {
      project = this.$storex.projects.allProjects.find(p => p.project_name === project_name)
    }

    const API = await this.$storex.api.project(project)
    const [models, profiles, knowledge ] = await Promise.all([
      API.projects.ai.models.list(),
      API.profiles.list(),
      API.knowledge.status(),
    ])
    const mentionList = this.mentionList(project, profiles, knowledge)
    return {
      ...project,
      models,
      profiles,
      knowledge,
      mentionList
    }
  }
}
