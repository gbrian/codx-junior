export class GitIssueWizard {
  constructor($service, issueUrl) {
    this.$service = $service
    this.$storex = $storex
    this.issueUrl = issueUrl
    this.currentStepIndex = 0
    this.steps = [
      'Loading issue information',
      'Creating kanban',
      'Creating analysis',
      'Searching project for information',
      'Creating subtasks',
      'Implementing task: task_name'
    ]
    this.stepFunctions = {
      'Loading issue information': this.loadIssueInformation.bind(this),
      'Creating kanban': this.createKanban.bind(this),
      'Creating analysis': this.createAnalysis.bind(this),
      'Searching project for information': this.searchProjectForInformation.bind(this),
      'Creating subtasks': this.createSubtasks.bind(this),
      'Implementing task: task_name': this.implementTask.bind(this)
    }
    this.data = { issueUrl }
  }

  async loadIssueInformation() {
    this.data.issueInfo = await this.$storex.api.projects.loadIssue(this.data.issueUrl)
  }

  async createKanban() {
    const { issueInfo, issueUrl } = this.data
    this.$storex.ui.setActiveTab('tasks')
    const boardName = issueInfo.title
    const description = `Fixing issue: ${issueUrl}`
    const columns = this.$storex.projects.kanbanTemplates.find(t => t.name === "Backlog").columns
    const board = await this.$storex.projects.addBoard({
      title: boardName,
      description,
      columns,
    })
    this.data.kanbanBoard = this.$storex.projects.allBoards.find(b => b.title === board.title)
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 1000))
  }

  async createAnalysis() {
    const { kanbanBoard, issueInfo: { title, url, comments } } = this.data
    const { title: boardTitle, id: kaban_id, columns } = kanbanBoard
    const { author, body } = comments[0]
    const { id: column_id, title: columnTitle } = columns[0]
    this.$storex.projects.setActiveBoard(boardTitle)
    this.data.chat = await this.$storex.projects.createNewBoardChat({
      boardTitle,
      columnTitle,
      chat: {
        mode: 'chat',
        name: `[ANALYSIS] ${title}`,
        description: `Issue ${url}`,
        kaban_id: kaban_id,
        column_id: column_id,
        messages: [{
          role: "user",
          author: this.$storex.users.user.username,
          profiles: ["analyst"],
          content: `@${author} Opened this issue:\n${body}\nAnalyse it.`
        }]
      }
    })
    await this.$storex.projects.saveChat(this.data.chat)
    await this.$storex.projects.chatWihProject(this.data.chat)
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 2500))
  }

  async searchProjectForInformation() {
    const { chat: { id: chatId } } = this.data
    const startTime = Date.now()
    return new Promise(resolve => {
      const intervalId = setInterval(async () => {
        const messagesCount = this.$storex.projects.chats[chatId].messages.length
        if (messagesCount > 1 || Date.now() - startTime > 30000) {
          clearInterval(intervalId)
          resolve({ success: messagesCount > 1 })
        }
      }, 3000)
    })
  }

  async createSubtasks() {
    const { chat } = this.data
    const instructions = "Create subtasks based on the issue"
    await this.$storex.projects.createSubTasks({ chat, instructions })
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 1800))
  }

  implementTask() {
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 2200))
  }

  async executeStep(step) {
    const stepFunction = this.stepFunctions[step]
    if (!stepFunction) {
      throw new Error('Unknown step')
    }
    return stepFunction()
  }

  async next() {
    if (this.currentStepIndex >= this.steps.length) {
      return { done: true }
    }

    const step = this.steps[this.currentStepIndex]
    this.currentStepIndex++
    try {
      await this.executeStep(step)
      const done = this.currentStepIndex === this.steps.length
      return { step: this.currentStepIndex, success: true, done }
    } catch (ex) {
      console.error("Error executing", step, ex)
      return { step: this.currentStepIndex, error: ex, done: true }
    }
  }

  cancel() {
    this.currentStepIndex = this.steps.length
  }
}

export default GitIssueWizard