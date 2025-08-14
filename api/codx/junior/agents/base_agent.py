import logging
import re
from codx.junior.engine import CODXJuniorSession
from codx.junior.utils.utils import exec_command

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

