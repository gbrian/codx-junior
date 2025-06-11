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