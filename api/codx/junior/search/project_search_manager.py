import logging
from codx.junior.settings import CODXJuniorSettings
from codx.junior.knowledge.knowledge_milvus import Knowledge

logger = logging.getLogger(__name__)

class ProjectSearchManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.knowledge = Knowledge(settings=self.settings)
        logger.info("ProjectSearchManager initialized.")

    def search(self, query: str) -> list:
        """
        Searches across indexed project data for the given query.

        Args:
            query: The search string.

        Returns:
            A list of search results, each with 'id', 'name', and 'resource_type'.
        """
        logger.debug(f"Performing search for query: '{query}'")
        results = self.knowledge.search(query)
        logger.debug(f"Search completed. Found {len(results)} results.")
        return results
