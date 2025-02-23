# [[{"id": "3d48c097-0897-43a0-8a09-1f370364aa2b", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "name": "RAG testing", "created_at": "2025-01-18 06:14:38.062367+00:00", "updated_at": "2025-01-18T12:31:16.507773", "mode": "chat", "board": "kanban", "column": "on going", "chat_index": 0, "live_url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/kanban/on going/RAG testing.3d48c097-0897-43a0-8a09-1f370364aa2b.md"}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-01-18 06:44:02.534897", "updated_at": "2025-01-18 06:44:02.534920", "images": [], "files": []}]]
List all rag methods in the project
## [[{"role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-01-18 12:29:58.973728", "updated_at": "2025-01-18 12:29:58.973750", "images": [], "files": ["/codx/junior/engine.py"]}]]
The project you are working on involves several methods that are part of the Retrieve-Augment-Generate (RAG) process. These methods are primarily concerned with retrieving and processing documents from a knowledge base to generate relevant outputs. Here is a list of the RAG-related methods found in the `CODXJuniorSession` class located in `/shared/codx-junior/api/codx/junior/engine.py`:

1. **`knowledge_search`**: This method is responsible for searching documents in the knowledge base using different search strategies, such as embeddings or source-based searches.

2. **`select_afefcted_documents_from_knowledge`**: This method retrieves documents from the knowledge base that are relevant to a given query. It considers subprojects and project dependencies to include documents from related projects as well.

3. **`select_afected_files_from_knowledge`**: This method utilizes the `select_afefcted_documents_from_knowledge` method to find documents and then extracts the file paths of those documents, ensuring duplicates are removed.

These methods are integral to the RAG process as they handle the retrieval of documents based on user queries, allowing the system to generate informed and contextually relevant responses. If you need further details about how these methods work or require assistance with maintaining or extending them, feel free to ask.