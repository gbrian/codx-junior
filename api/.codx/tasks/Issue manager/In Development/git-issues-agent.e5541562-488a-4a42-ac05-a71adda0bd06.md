# [[{"id": "e5541562-488a-4a42-ac05-a71adda0bd06", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "profiles": ["analyst"], "users": ["admin"], "name": "git_issues agent", "description": "In a GitHub issue discussion, user \"lcarrettin\" highlights a bug involving a null `eventEmitterCallback` in `BaseJavaModule.java` on arm32 architecture, causing app crashes. The conversation focuses on identifying the source of the issue, where the callback is assigned and later utilized without checks, leading to application instability. The user's detailed observation pinpoints a specific line in the codebase as the potential culprit, suggesting areas for potential fixes. The absence of comments from project maintainers indicates the issue may require additional verification and proposed solutions for resolution.", "created_at": "2025-05-28 15:21:34.696219", "updated_at": "2025-05-28T15:45:52.915960", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Issue manager", "column": "In Development", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/api/.codx/tasks/Issue manager/In Development/git-issues-agent.e5541562-488a-4a42-ac05-a71adda0bd06.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "8d83595e-9036-46ab-b9fd-3bc7bbcf4679", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-28 15:21:34.694442", "updated_at": "2025-05-28 15:21:34.694477", "images": [], "files": [], "meta_data": {}, "profiles": ["analyst"], "user": "admin", "knowledge_topics": []}]]
Git issues agent will:
* Download a git issue comments
* Summarize conversarion
* Find related content in the project that can help with the reasoning
* Reasoning about the issue
* Create subtasks to fix the issue
* For each subtask generate a change proposal


Agent will inherit from AgentBase and will receive a session (CODXJuniorSession)
We'll need "from codx.junior.misc.github import  download_issue_info" to get info from the issue.
Issue info has thi structure:
```json
{
    "issue": "https://github.com/facebook/react-native/issues/51628",
    "comments": [
        {
            "author": {
                "__typename": "User",
                "login": "lcarrettin",
                "avatarUrl": "https://avatars.githubusercontent.com/u/52881070?v=4",
                "profileUrl": "https://github.com/lcarrettin",
                "id": "MDQ6VXNlcjUyODgxMDcw"
            },
            "body": "It seems that on arm32 in packages/react-native/ReactAndroid/src/main/java/com/facebook/react/bridge/BaseJavaModule.java\n\nthis method\n\nhttps://github.com/facebook/react-native/blob/e7901a720bcf3877e8a011f7b211c7d59c694853/packages/react-native/ReactAndroid/src/main/java/com/facebook/react/bridge/BaseJavaModule.java#L139\n\nis called with a null eventEmitterCallback which is assigned to mEventEmitterCallback in the following line.\nmEventEmitterCallback is then used to emit an event, but being null the app crashes.\n\n",
            "createdAt": "2025-05-27T14:53:53Z",
            "url": "https://github.com/facebook/react-native/issues/51628#issuecomment-2912830732",
            "authorAssociation": "NONE"
        },
]
}
```

When authorAssociation is MEMBER then the message is coming from a repo maintainer, give it more credit.
The first comment details the issue. 




## [[{"doc_id": "13021c2a-2c11-4974-850f-aa7c63160f49", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-28 15:39:30.073342", "updated_at": "2025-05-28 15:39:30.073382", "images": [], "files": [], "meta_data": {"time_taken": 17.183793544769287, "first_chunk_time_taken": 2.149578094482422, "model": "gpt-4o"}, "profiles": ["analyst", "analyst"], "user": null, "knowledge_topics": []}]]
To transform the user requirements into tasks for the developers, let's evaluate the provided information and determine how to organize it into epics and subtasks.

### User Requirement Evaluation

The requirement is to develop a Git issues agent that can:
1. **Download Git issue comments**
2. **Summarize the conversation**
3. **Find related content/material in the project**
4. **Reason about the issue based on the provided and related information**
5. **Create subtasks to fix the issue**
6. **Generate change proposals for each subtask**

Given these functions, this requirement seems broad and involves several distinct functionalities. Therefore, it is suitable to be structured as an epic with subtasks.

---

## Epic: Development of a Git Issues Agent

**Description:**
Develop a Git Issues Agent that inherits from `AgentBase` and utilizes a `CODXJuniorSession` to process issues from GitHub. The agent will perform a series of functions, including downloading issue comments, summarizing conversations, finding related project content, reasoning about the issue, creating subtasks, and generating change proposals.

### Business Requirements
- The agent must be able to download and process comments from a given GitHub issue.
- The agent should accurately summarize conversations from the comments.
- The agent should inspect the project's codebase to find related content that might help in understanding and reasoning about the issue.
- The agent has to reason about the issues to propose potential solutions or fixes.
- The agent must break down issues into implementable subtasks.
- Each subtask should have a proposed code change or solution.

### Acceptance Criteria
- Successful download and parsing of GitHub issue comments using the `download_issue_info` function.
- Accurately generated summaries of the comment threads from the issues.
- Correct identification of relevant content and materials from the related project files.
- Logical and insightful reasoning with potentially helpful solutions or improvements based on the issue.
- Clear, precise subtask creation that aligns with solving the identified issue.
- Each subtask includes a viable change proposal, facilitating easy implementation by developers.

### Subtasks
- **Task 1: Set up AgentBase Inheritance and Session Handling**
  - Implement agent class inheriting from `AgentBase`
  - Configure session handling using `CODXJuniorSession`
  
- **Task 2: Develop Functionality to Download and Parse Issue Comments**
  - Integrate `download_issue_info` to fetch issue data
  - Parse and store comment sections

- **Task 3: Implement Conversation Summarization Logic**
  - Develop a method to summarize the comment conversation
  - Ensure accurate representation of the main points and issue details

- **Task 4: Create Related Content Finder**
  - Scan the project directory to identify related files or code blocks
  - Link related content to the current issue context for better understanding

- **Task 5: Develop Reasoning Engine for Issue Analysis**
  - Implement logic to analyze and reason about issues using comment and project data

- **Task 6: Design Method for Subtask Creation**
  - Breakdown issues into discrete, actionable subtasks

- **Task 7: Generate Change Proposals for Subtasks**
  - Develop proposals including code changes or suggested solutions for each subtask

These subtasks represent the key functionalities required to achieve the outlined business requirements and meet the acceptance criteria for the Git issues agent. Each task involves implementing specific features of the agent, contributing to its overall purpose of efficiently managing and processing GitHub issues.