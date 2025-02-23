# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": ["/codx/junior/engine.py"], "profiles": ["software_developer"], "name": "project metrics", "created_at": "2024-10-16T12:20:53.939791", "updated_at": "2025-02-02T16:44:52.671759", "mode": "chat", "board": "Default", "column": "tasks", "chat_index": 2, "live_url": "", "branch": "", "file_path": "/usr/local/codx-junior/api/.codx/tasks/Default/tasks/project metrics.0.md"}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-02-02 16:42:11.850631", "updated_at": "2025-02-02 16:42:11.850674", "images": [], "files": []}]]
List all methods from engine
## [[{"doc_id": "98656a00-6b90-4aea-baa9-d738bb2080c7", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-02-02 16:42:12.497725", "updated_at": "2025-02-02 16:42:12.497760", "images": [], "files": []}]]
Here is a list of all methods defined in the `engine.py` file:

1. `create_project(project_path: str)`
2. `coder_open_file(settings: CODXJuniorSettings, file_name: str)`
3. `find_project_from_file_path(file_path: str)`
4. `find_all_projects()`
5. `update_engine()`
6. `__init__(self, settings: CODXJuniorSettings = None, codx_path: str = None, channel: SessionChannel = None)`
7. `log_info(self, msg)`
8. `get_channel(self)`
9. `event_data(self, data: dict)`
10. `send_event(self, message: str)`
11. `chat_event(self, chat: Chat, message: str = None, event_type: str = None)`
12. `message_event(self, chat: Chat, message: Message)`
13. `delete_project(self)`
14. `get_chat_manager(self)`
15. `get_profile_manager(self)`
16. `get_ai(self)`
17. `get_knowledge(self)`
18. `get_browser(self)`
19. `load_chat(self, board, chat_name)`
20. `list_chats(self)`
21. `save_chat(self, chat: Chat, chat_only=False)`
22. `delete_chat(self, file_path)`
23. `list_profiles(self)`
24. `save_profile(self, profile)`
25. `read_profile(self, profile_name)`
26. `delete_profile(self, profile_name)`
27. `reload_knowledge(self, path: str = None)`
28. `knowledge_search(self, knowledge_search: KnowledgeSearch)`
29. `delete_knowledge_source(self, sources: [str])`
30. `delete_knowledge(self)`
31. `select_afefcted_documents_from_knowledge(self, ai: AI, query: str, ignore_documents=[])`
32. `select_afected_files_from_knowledge(self, ai: AI, query: str)`
33. `improve_existing_code_patch(self, code_generator: AICodeGerator)`
34. `improve_existing_code(self, chat: Chat, apply_changes: bool=None)`
35. `get_ai_code_generator_changes(self, response: str)`
36. `project_script_test(self)`
37. `apply_improve_code_changes(self, code_generator: AICodeGerator, chat: Chat = None)`
38. `change_file_with_instructions(self, instruction_list: [str], file_path: str, content: str)`
39. `check_knowledge_status(self)`
40. `check_project_changes(self)`
41. `process_project_changes(self)`
42. `extract_changes(self, content)`
43. `split_blocks_by_gt_lt(self, content)`
44. `get_line_changes(self, content)`
45. `change_file(self, context_documents, query, file_path, org_content, save_changes=False)`
46. `check_file_for_mentions(self, file_path: str, content: str = None, silent: bool = False)`
47. `process_image_mention(self, image_mentions, file_path: str, content: str)`
48. `generate_tasks(self, chat: Chat)`
49. `chat_with_project(self, chat: Chat, use_knowledge: bool=True, callback=None, append_references: bool=True, chat_mode: str=None)`
50. `check_project(self)`
51. `extract_tags(self, doc)`
52. `get_keywords(self, query)`
53. `get_wiki_file(self, file_path:str)`
54. `get_readme(self)`
55. `update_wiki(self, file_path: str)`
56. `update_project_profile(self, file_path: str)`
57. `get_project_metrics(self)`
58. `api_image_to_text(self, image_bytes)`
59. `parse_file_line(self, file, base_path)`
60. `read_directory(self, path: str)`
61. `read_file(self, path: str)`
62. `process_project_file_before_saving(self, file_path: str, content: str)`
63. `apply_file_profile(self, file_path: str, content: str, profile: Profile)`
64. `write_project_file(self, file_path: str, content: str)`
65. `search_files(self, search: str)`
66. `run_app(self, app_name: str)`
67. `get_project_apps(self)`
68. `get_project_branches(self)`
69. `get_project_current_branch(self)`
70. `get_project_parent_branch(self)`
71. `get_project_changes(self, parent_branch: str = None)`
72. `build_code_changes_summary(self, force = False)`
73. `load_boards(self)`
74. `save_boards(self, kanbans: [])`