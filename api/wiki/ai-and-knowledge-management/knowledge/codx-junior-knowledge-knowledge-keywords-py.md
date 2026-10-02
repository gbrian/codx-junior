### Knowledge Keywords

This module provides functionality to manage keywords associated with documents within a project. It allows for adding, retrieving, and removing keywords, which can be used for document enrichment and potentially for code splitting strategies.

#### `KnowledgeKeywords` Class

The `KnowledgeKeywords` class handles the storage and retrieval of keywords.

```python
# /codx/junior/knowledge/knowledge_keywords.py
import json
import logging
import sqlite3
from slugify import slugify
from codx.junior.settings import CODXJuniorSettings

from codx.junior.utils.utils import write_file

logger = logging.getLogger(__name__)

class KnowledgeKeywords:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.path = self.settings.project_path
        self.index_name = slugify(str(self.path))
        self.db_path = f"{settings.codx_path}/db/{self.index_name}"
        self.db_keywords_file = f"{self.db_path}/keywords.json"
        
    def get_keywords(self, query: str = None):
        def load():
            try:
                with open(self.db_keywords_file) as f:
                    return json.loads(f.read())
            except:
                pass
            return {}
        keywords = load()
        if query:
            query = query.lower()
            filtered = {}
            for key, value in keywords.items():
                matches = [val for val in value if query in val.lower()]
                if matches:
                    filtered[key] = matches 
            keywords = filtered
        return keywords

    def add_keywords(self, file_path, file_keywords):
        keywords = self.get_keywords()
        keywords[file_path] = [word.strip() for word in file_keywords.split(",")]
        write_file(self.db_keywords_file, json.dumps(keywords, indent=2))

    def remove_keywords(self, file_path):
        keywords = self.get_keywords()
        if file_path in keywords:
            del keywords[file_path]
            write_file(self.db_keywords_file, json.dumps(keywords, indent=2))
```

##### Initialization

The `__init__` method initializes the `KnowledgeKeywords` object. It takes a `CODXJuniorSettings` object as input and sets up paths for storing the keyword data.

*   `settings`: An instance of `CODXJuniorSettings`.
*   `path`: The project path derived from `settings`.
*   `index_name`: A slugified version of the project path, used for creating a unique database directory.
*   `db_path`: The path to the directory where keyword data will be stored.
*   `db_keywords_file`: The path to the JSON file that stores the keywords.

##### Methods

*   `get_keywords(query: str = None)`:
    *   Loads keywords from the `keywords.json` file.
    *   If a `query` string is provided, it filters the keywords, returning only those entries where the query string (case-insensitive) is found within the keywords associated with a file.
    *   Returns a dictionary where keys are file paths and values are lists of keywords.

*   `add_keywords(file_path, file_keywords)`:
    *   Retrieves existing keywords.
    *   Adds or updates the keywords for a given `file_path`. The `file_keywords` are expected to be a comma-separated string, which will be parsed into a list of strings.
    *   Saves the updated keywords back to the `keywords.json` file.

*   `remove_keywords(file_path)`:
    *   Retrieves existing keywords.
    *   If the `file_path` exists in the keywords dictionary, it removes the entry.
    *   Saves the updated keywords back to the `keywords.json` file.