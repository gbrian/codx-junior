# Agents

## AgentBase

The `AgentBase` class serves as the foundational class for all agents within the codx-junior project. It establishes a common interface and incorporates essential functionalities required by every agent, including initialization with a session object and logging capabilities.

### Initialization

When a new `AgentBase` instance is created, it is initialized with an agent's name and a `CODXJuniorSession` object. This session object manages the context for the agent's operations.

```python
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
```

### Getting AI Instance

Agents can retrieve the AI instance associated with their session.

```python
def get_ai(self):
    return self.session.get_ai()
```

### Retrieving Git Repository URL

This method executes a Git command to fetch the repository URL from a specified project path.

```python
def get_git_repo_url(self, project_path: str) -> str:
    """
    Executes a Git command to get the repository URL from the provided project path.

    Args:
        project_path (str): Path to the project directory.

    Returns:
        str: The Git repository URL.
    """
    try:
        command = "git config --get remote.origin.url"
        stdout, stderr = exec_command(command, cwd=project_path)
        if stderr:
            logger.error(f"Error executing command: {stderr}")
            return None
        return stdout.strip()
    except Exception as e:
        logger.error(f"Failed to retrieve Git repo URL: {str(e)}")
        return None
```

### Extracting DevOps Information

The `extract_devops_info` method parses a Git repository URL to extract relevant DevOps information such as user, token, host, organization, and repository name.

```python
def extract_devops_info(self, repo_url: str):
    """
    Extracts user, token, and DevOps info from the repository URL.

    Args:
        repo_url (str): The Git repository URL.

    Returns:
        dict: A dictionary containing extracted information or error message.
    """
    try:
        regex = r"(https?://)?(\w+):(\w+)@([\w\.]+)/([\w-]+)/([\w-]+)"
        match = re.match(regex, repo_url)
        if not match:
            return {"error": "Invalid repo URL format"}
        
        protocol, user, token, host, org, repo = match.groups()
        return {
            "user": user,
            "token": token,
            "host": host,
            "organization": org,
            "repository": repo
        }
    except Exception as e:
        logger.error(f"Failed to extract info: {str(e)}")
        return {"error": f"Failed to extract info: {str(e)}"}
```