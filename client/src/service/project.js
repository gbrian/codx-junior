import Service from "./service"

export class ProjectService extends Service {
  async cloneProject(projectPath) {
    if (projectPath.includes("github.com") &&
        projectPath.includes("/issues/")) {
        projectPath = projectPath.split("/issues/")[0]
    } 
    await this.projects.createNewProject(projectPath)
  }
}
