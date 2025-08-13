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
}
