
export class GitIssueWizard {
  constructor($service, issueUrl) {
    this.$service = $service
    this.issueUrl = issueUrl
    this.currentStepIndex = 0
    this.steps = [
      'Loading issue information',
      'Creating kanban',
      'Creating analysis',
      'Searching project for information',
      'Creating subtasks',
      'Implementing subtasks'
    ]
    this.stepFunctions = {
      'Loading issue information': this.loadIssueInformation.bind(this),
      'Creating kanban': this.createKanban.bind(this),
      'Creating analysis': this.createAnalysis.bind(this),
      'Searching project for information': this.searchProjectForInformation.bind(this),
      'Creating subtasks': this.createSubtasks.bind(this),
      'Implementing subtasks': this.implementTask.bind(this)
    }
    this.data = { issueUrl }
  }

  async loadIssueInformation() {
    this.data.issueInfo = await this.$service.$storex.api.projects.loadIssue(this.data.issueUrl)
  }

  async createKanban() {
    const { issueInfo, issueUrl } = this.data
    this.$service.$storex.ui.setActiveTab('tasks')
    const boardName = issueInfo.title
    const description = `Fixing issue: ${issueUrl}`
    const columns = this.$service.$storex.projects.kanbanTemplates.find(t => t.name === "Backlog").columns
    const board = await this.$service.$storex.projects.addBoard({
      title: boardName,
      description,
      columns,
    })
    this.data.kanbanBoard = this.$service.$storex.projects.allBoards.find(b => b.title === board.title)
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 1000))
  }

  async createAnalysis() {
    const { kanbanBoard, issueInfo: { title, url, comments } } = this.data
    const { title: boardTitle, id: kaban_id, columns } = kanbanBoard
    const { author, body } = comments[0]
    const { id: column_id, title: columnTitle } = columns[0]
    this.$service.$storex.projects.setActiveBoard(boardTitle)
    this.data.chat = await this.$service.$storex.projects.createNewBoardChat({
      boardTitle,
      columnTitle,
      chat: {
        mode: 'chat',
        name: `[ANALYSIS] ${title}`,
        description: `Issue ${url}`,
        kaban_id: kaban_id,
        column_id: column_id,
        messages: []
      }
    })
    await this.$service.chat.sendMessage({ 
      chat: this.data.chat,
      message: {
        role: "user",
        author: this.$service.$storex.users.user.username,
        profiles: ["analyst"],
        content: `@${author} Opened this issue:\n${body}\nAnalyse it.`
      }
    })
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 2500))
  }

  async searchProjectForInformation() {
    const { chat: { id: chatId } } = this.data
    const startTime = Date.now()
    return new Promise(resolve => {
      const intervalId = setInterval(async () => {
        const isAnalysisDone = this.$service.$storex.projects.chats[chatId].messages[1]?.done
        if (isAnalysisDone || Date.now() - startTime > 30000) {
          clearInterval(intervalId)
          resolve({ success: isAnalysisDone })
        }
      }, 3000)
    })
  }

  async createSubtasks() {
    const { chat } = this.data
    const instructions = "Create subtasks based on the issue"
    await this.$service.$storex.projects.createSubTasks({ chat, instructions, profiles: ["software_developer"] })
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 1800))
  }

  async implementTask() {
    const { data: { chat: { id: chatId } } } = this
    let startTime = null
    const getChatSubtasks = () => {
        return this.$service.$storex.projects.allChats.filter(({ parent_id }) => parent_id === chatId )
    }
    const resetTimeout = () => {
      return (startTime = Date.now())
    }
    const processedChildChats = []

    return new Promise(resolve => {
      resetTimeout()
      const intervalId = setInterval(async () => {
        const subtasks = getChatSubtasks()
        subtasks.forEach(subtask => {
          if (!processedChildChats.find(s => s.id === subtask.id)) {
            this.$service.chat.sendMessage({
              chat: subtask, 
              message: {
                role: "user",
                content: "Implement changes",
                profiles: ["software_developer"]
              }
            })
            processedChildChats.push(subtask)
            resetTimeout()
          }
        })

        const allDone = processedChildChats.every(subtask => subtask.messages[1]?.done)
        if (allDone || Date.now() - startTime > 30000) {
          clearInterval(intervalId)
          resolve({ success: allDone })
        }
      }, 15000)
    })
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
      console.error("Error executing", step, ex, this.data)
      return { step: this.currentStepIndex, error: ex, done: true }
    }
  }

  cancel() {
    this.currentStepIndex = this.steps.length
  }
}

export default GitIssueWizard