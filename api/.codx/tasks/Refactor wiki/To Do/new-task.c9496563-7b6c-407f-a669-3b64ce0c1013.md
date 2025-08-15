# [[{"id": "c9496563-7b6c-407f-a669-3b64ce0c1013", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/wiki/wiki_manager.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "New Task", "description": "In this conversation, we discussed modifications to the `WikiManager` class to eliminate its dependency on VitePress. The goal was to simplify its responsibilities to creating configurations, building a home page with project overviews, and generating category files. I provided an updated version of the `WikiManager` class featuring straightforward methods for these tasks, focusing on using plain JSON files and Markdown for documentation. The updated class reflects a leaner design, focusing solely on essential functions without external framework dependencies.", "created_at": "2025-08-15 08:11:18.123495", "updated_at": "2025-08-15T08:58:14.124887", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Refactor wiki", "column": "To Do", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Refactor wiki/To Do/new-task.c9496563-7b6c-407f-a669-3b64ce0c1013.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "4ee8192d-c4ef-42f6-ae25-30d727f29f98", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-08-15 08:11:18.121380", "updated_at": "2025-08-15 08:11:18.121406", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
We are going to change the way we build the wiki and forget about vitepress.


New WikiManger will have these responsabilities:
 * Create config: That includes categories and "top sections"
 * Build home: A home page with an overview of the project
 * Category files: For each category we'll maintain a wiki page





