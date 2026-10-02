# Chat Engine

The `ChatEngine` class in `codx/junior/chat/chat_engine.py` is responsible for managing and processing chat interactions within the CODX Junior project. It orchestrates communication with AI models, handles knowledge base integration, and interacts with project management features.

## Initialization

The `ChatEngine` is initialized with the following parameters:

- `settings`: An instance of `CODXJuniorSettings` containing project-specific configurations.
- `event_manager`: An object for managing and dispatching chat-related events.
- `user`: An optional `CodxUser` object representing the current user.

```python
def __init__(self,
             settings,
             event_manager,
             user: CodxUser = None):
    self.settings = settings
    self.event_manager = event_manager
    self.knowledge = Knowledge(settings=settings)
    self.user = user
```

## Core Functionality

### `chat_with_project`

This is the primary method for interacting with the AI to process chat messages. It handles:

- **Context Switching:** If the chat belongs to a different project, it switches the context using `switch_project`.
- **Message Processing:** It converts chat messages into a format suitable for the AI model.
- **Knowledge Integration:** It searches the knowledge base for relevant documents based on the user's query and existing chat context.
- **Profile and Tool Integration:** It incorporates information from user profiles and defined tools to guide the AI's response.
- **Chat Modes:** Supports different chat modes like "chat", "task" (refinement), and "agent" (iterative task completion).
- **Event Management:** Dispatches events for various stages of the chat processing, such as "starting", "error", and "done".
- **Response Handling:** Processes the AI's response, extracts reasoning (if any), and updates the chat message.
- **Chat Description Generation:** Creates a summary of the conversation.

```python
@profile_function
async def chat_with_project(self, chat: Chat, disable_knowledge: bool = False, callback=None, append_references: bool=True, chat_mode: str=None, iteration: int = 0):
    # ... (implementation details as in the provided document)
```

### `switch_project`

This method allows the `ChatEngine` to switch its context to a different project based on a provided `project_id`. It updates the internal `settings` to reflect the new project.

```python
def switch_project(self, project_id: str) -> 'ChatEngine':
    # ... (implementation details as in the provided document)
```

### `get_ai`

Returns an instance of the `AI` class, configured with the current project settings and an optional language model.

```python
def get_ai(self, llm_model: Optional[str] = None) -> AI:
    # ... (implementation details as in the provided document)
```

### `get_ai_code_generator_changes`

Parses the AI's response to extract code changes, applying necessary path adjustments.

```python
def get_ai_code_generator_changes(self, response: str) -> AICodeGenerator:
    # ... (implementation details as in the provided document)
```

### `select_documents_from_knowledge`

Searches the knowledge base for relevant documents based on a query, considering documents to ignore and specific projects to search within.

```python
def select_documents_from_knowledge(self, chat: Chat, query: str, ignore_documents=None,
                                             search_projects=None) -> Tuple[List[Document], List[str]]:
    # ... (implementation details as in the provided document)
```

### `create_knowledge_search_query`

Enhances a user's query by extracting keywords to improve the effectiveness of knowledge base searches.

```python
def create_knowledge_search_query(self, query: str) -> str:
    # ... (implementation details as in the provided document)
```

### `get_query_mentions`

Identifies and extracts mentions of profiles and projects from the user's query and chat context.

```python
def get_query_mentions(self, chat, user_message) -> QueryMentions:
    # ... (implementation details as in the provided document)
```

### `get_chat_analysis_parents`

Recursively traverses parent chats to gather their content, useful for providing historical context.

```python
def get_chat_analysis_parents(self, chat: Chat):
    # ... (implementation details as in the provided document)
```

### `convert_message`

A static method to convert internal `Message` objects into `langchain` message types (`HumanMessage`, `AIMessage`), including handling of images.

```python
@staticmethod
def convert_message(message):
    # ... (implementation details as in the provided document)
```

### `get_all_search_projects`

Retrieves a list of all projects relevant for searching, including the current project, its child projects, and dependencies.

```python
def get_all_search_projects(self):
    # ... (implementation details as in the provided document)
```

### `index_chat`

Indexes a chat session as a `Document` in the knowledge system, making its content searchable.

```python
def index_chat(self, chat: Chat):
    # ... (implementation details as in the provided document)
```