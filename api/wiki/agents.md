# Agents

## GitIssuesAgent

The `GitIssuesAgent` is a class designed to process GitHub issues. It includes functionalities for downloading issue information, summarizing conversations, extracting keywords, reasoning about the issue, and proposing solutions. Below is a detailed explanation of the class and its methods.

### Class Definition

```python
import logging
from codx.junior.agents.base_agent import AgentBase
from codx.junior.engine import CODXJuniorSession
from codx.junior.misc.github import (
  Issue,
  IssueComment,
  download_issue_info
)

from typing import List

from codx.junior.db import (
    Chat,
    Message,
)

# Set up logging for this module
logger = logging.getLogger(__name__)

class GitIssuesAgent(AgentBase):
    """
    Agent for processing GitHub issues, including downloading issue information,
    summarizing conversations, finding related project content, reasoning about
    the issue, and proposing solutions.
    """
    def __init__(self, session: CODXJuniorSession):
        super().__init__(agent_name=GitIssuesAgent.__name__, session=session)
```

### Methods

#### `run(issue_url: str) -> None`

This method is the main entry point for processing an issue. It coordinates fetching issue data, summarizing discussions, reasoning, and generating actionable subtasks.

```python
async def run(self, issue_url: str) -> None:
    """
    Main entry point for processing an issue. It coordinates fetching issue
    data, summarizing discussions, reasoning, and generating actionable subtasks.

    Parameters:
    issue_url (str): The URL for the GitHub issue to be processed.
    """
    logger.info(f"Starting the processing for issue at URL: {issue_url}")

    try:
        # Fetch detailed information for the specified issue
        issue_info = download_issue_info(issue_url)
        comments = issue_info.comments
        logger.info(f"Fetched {len(comments)} comments from the issue.")

        # Summarize the conversation based on the comments fetched
        self.summarize_conversation(comments)
        
        # Extract keywords from the summarized comments
        all_keywords = self.extract_keywords_from_comments(comments)
        logger.info(f"Extracted keywords: {all_keywords}")

        # Reason about the issue using summary and project context
        chat = await self.reason_about_issue(issue_info, comments, all_keywords)            
        logger.debug("Reasoning concluded")

        return chat

        # Create subtasks based on the reasoning
        subtasks = self.session.create_subtasks(issue_reasoning)
        logger.debug(f"Subtasks identified: {subtasks}")

        # Generate specific change proposals for each subtask identified
        self.generate_change_proposals(subtasks)

    except Exception as e:
        logger.exception(f"An error occurred while processing the issue: {e}")
```

#### `summarize_conversation(comments: List[IssueComment]) -> List[IssueComment]`

This method summarizes each comment in the issue using AI to understand the consensus or main concerns expressed.

```python
def summarize_conversation(self, comments: List[IssueComment]) -> List[IssueComment]:
    """
    Summarizes each comment in the issue using AI to understand the consensus
    or main concerns expressed.

    Parameters:
    comments (list): A list of dictionaries representing comments from the issue.

    Returns:
    list: A list of IssueComment objects containing original comments and their summaries.
    """
    logger.info("Summarizing the issue conversation from comments.")
    ai = self.get_ai()

    for comment in comments:
        try:
            # Use AI to summarize each comment
            ai_response = ai.chat(prompt=f"Summarize in 5 lines this message: {comment.body}")
            comment.summary = ai_response[-1].content
        except Exception as e:
            logger.exception(f"Failed to summarize comment by {comment.author}: {e}")
```

#### `extract_keywords_from_comments(comments: List[IssueComment]) -> list`

This method extracts keywords from the summarized comments using AI.

```python
def extract_keywords_from_comments(self, comments: List[IssueComment]) -> list:
    """
    Extracts keywords from the summarized comments using AI.

    Parameters:
    comments (list): A list of IssueComment objects.

    Returns:
    list: A list of keywords.
    """
    logger.info("Extracting keywords from the summarized comments.")
    ai = self.get_ai()
    all_keywords = []

    for comment in comments:
        prompt = f"Extract key words from the following text: {comment.summary}"
        ai_response = ai.chat(prompt=prompt)
        keywords = ai_response[-1].content.split(", ")
        all_keywords.extend(keywords)
        logger.debug(f"Extracted keywords from comment by {comment.author}: {keywords}")

    return list(set(all_keywords))  # Remove duplicates
```

#### `reason_about_issue(issue_info: Issue, comments: List[IssueComment], keywords: List[str]) -> Chat`

This method analyzes the issue using summarized conversations and relevant project content to derive a logical reasoning or action plan.

```python
async def reason_about_issue(self, issue_info: Issue, comments: List[IssueComment], keywords: List[str]) -> Chat:
    """
    Analyzes the issue using summarized conversations and relevant project
    content to derive a logical reasoning or action plan.

    Parameters:
    comments (list): A list of IssueComment objects.
    related_documents (list): A list of related documents.

    Returns:
    str: An analysis or explanation outlining steps to address the issue.
    """
    logger.info("Reasoning about the issue using summary and context.")
    messages = [Message(
        role="user",
        content=comment.summary) for comment in comments]
    
    reasoning = f"""
        Analyse issue '{issue_info.title}' from project @{self.session.settings.project_name} 
        and come up with a proposal to fix the issue
    """
    messages.append(Message(role="user", content=reasoning, profiles=["analyst"]))
    chat = Chat(name=issue_info.title, messages=messages)
    await self.session.chat_with_project(chat=chat)
    logger.debug(f"Reasoning concluded: {reasoning}")
    return reasoning
```

#### `create_subtasks(reasoning: str) -> list`

This method creates a list of actionable subtasks needed to address the identified issue.

```python
def create_subtasks(self, reasoning: str) -> list:
    """
    Creates a list of actionable subtasks needed to address the identified issue.

    Parameters:
    reasoning (str): The reasoning or analysis about the issue.

    Returns:
    list: A list of subtasks detailing actions to be taken.
    """
    logger.info("Developing subtasks based on the issue reasoning.")
    subtasks = [
        {"title": "Evaluate event callback mechanism", "description": reasoning},
        {"title": "Implement fix", "description": "Develop a patch based on findings from the analysis."},
        {"title": "Conduct Tests", "description": "Conduct integration tests to ensure compatibility and performance."}
    ]
    logger.debug(f"Subtasks identified: {subtasks}")
    return subtasks
```

#### `generate_change_proposals(subtasks: list) -> None`

This method generates specific change proposals for each subtask, outlining the changes to be made in the code or process to resolve the issue.

```python
def generate_change_proposals(self, subtasks: list) -> None:
    """
    Generates specific change proposals for each subtask, outlining the changes
    to be made in the code or process to resolve the issue.

    Parameters:
    subtasks (list): The list of subtasks derived from the reasoning process.
    """
    logger.info("Formulating change proposals for the identified subtasks.")
    for subtask in subtasks:
        proposal = f"Proposal for {subtask['title']}: {subtask['description']}"
        logger.info(f"Generated Change Proposal: {proposal}")
```

### Usage Example

To use the `GitIssuesAgent`, you need to initialize it with a `CODXJuniorSession` object and then call the `run` method with the URL of the GitHub issue you want to process.

```python
from codx.junior.engine import CODXJuniorSession
from codx.junior.agents.git_issues_agent import GitIssuesAgent

# Initialize the session
session = CODXJuniorSession(project_name="MyProject")

# Initialize the agent
agent = GitIssuesAgent(session)

# Process an issue
await agent.run("https://github.com/gbrian/codx-junior/issues/1")
```

This will start the processing of the specified GitHub issue, including fetching details, summarizing conversations, extracting keywords, reasoning about the issue, and generating subtasks and change proposals.

### Base Agent Class

The `AgentBase` class is a base class for all agents in the `codx-junior` project. It provides a common interface for all agents and should be inherited by specific agent implementations. It includes common functionalities that all agents should have, such as initialization with a session and logging.

```python
import logging
from codx.junior.engine import CODXJuniorSession

# Set up logging for this module
logger = logging.getLogger(__name__)

class AgentBase:
    """
    Base class for all agents in the codx-junior project.
    
    This class provides a common interface for all agents and should be inherited
    by specific agent implementations. It includes common functionalities that
    all agents should have, such as initialization with a session and logging.
    """

    def __init__(self, agent_name: str, session: CODXJuniorSession):
        """
        Initializes a new instance of the AgentBase class.

        Args:
            agent_name (str): The name of the agent, used for logging or identification.
            session (CODXJuniorSession): The session object which handles context for the agent's operations.
        """
        self.agent_name = agent_name
        self.session = session
        logger.info(f"Agent {self.agent_name} initialized with session: {self.session.settings.project_name}")

    def get_ai(self):
        return self.session.get_ai()
```

This base class ensures that all agents have a consistent structure and functionality, making it easier to manage and extend the system.