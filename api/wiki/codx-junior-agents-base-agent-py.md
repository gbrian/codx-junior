# AgentBase Class Documentation

## Overview
The `AgentBase` class is a base class for all agents in the codx-junior project. It provides a common interface and functionalities that all agents should have, such as initialization with a session and logging.

## Initialization
The `__init__` method initializes a new instance of the `AgentBase` class.

### Arguments
- `agent_name (str)`: The name of the agent, used for logging or identification.
- `session (CODXJuniorSession)`: The session object which handles context for the agent's operations.

### Example
```python
from codx.junior.engine import CODXJuniorSession
from codx.junior.agents.base_agent import AgentBase

session = CODXJuniorSession(project_name="MyProject")
agent = AgentBase(agent_name="MyAgent", session=session)
```

## Methods

### get_ai
This method returns the AI object associated with the session.

#### Returns
- `AI object`: The AI object from the session.

#### Example
```python
ai = agent.get_ai()
print(ai)
```

### get_git_repo_url
This method executes a Git command to get the repository URL from the provided project path.

#### Arguments
- `project_path (str)`: Path to the project directory.

#### Returns
- `str`: The Git repository URL.
- `None`: If an error occurs during the execution of the command.

#### Example
```python
repo_url = agent.get_git_repo_url("/path/to/project")
print(repo_url)
```

### extract_devops_info
This method extracts user, token, and DevOps info from the repository URL using a regular expression.

#### Arguments
- `repo_url (str)`: The Git repository URL.

#### Returns
- `dict`: A dictionary containing extracted information or an error message.

#### Example
```python
info = agent.extract_devops_info("https://username:token@github.com/organization/repository.git")
print(info)
```

## Logging
The `AgentBase` class uses the `logging` module to log messages at different levels (info, error).

### Setup
Logging is set up at the beginning of the module using:
```python
import logging
logger = logging.getLogger(__name__)
```

### Usage
- **Info**: Logs when an agent is initialized.
- **Error**: Logs errors encountered during command execution or info extraction.

## Regular Expression
The `extract_devops_info` method uses a regular expression to parse the repository URL. The regex pattern is:
```python
regex = r"(https?://)?(\w+):(\w+)@([\w\.]+)/([\w-]+)/([\w-]+)"
```
This pattern matches URLs in the format:
```
[protocol]://user:token@host/organization/repository.git
```

## Tips
- Ensure that the `project_path` argument passed to `get_git_repo_url` is correct and accessible.
- The `repo_url` should be in the correct format to avoid parsing errors.
- Use the `exec_command` function carefully, especially when dealing with sensitive information like tokens.

## Error Handling
- The `get_git_repo_url` method logs any errors encountered during the execution of the Git command and returns `None`.
- The `extract_devops_info` method logs any errors encountered during the parsing of the repository URL and returns a dictionary with an error message.

## Conclusion
The `AgentBase` class is a fundamental part of the codx-junior project, providing essential functionalities and logging capabilities for all agents. By inheriting from this class, specific agent implementations can leverage these features and focus on their unique tasks.