# [[{"id": "12bde209-5f75-4096-a454-868da745640f", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/wiki/wiki_manager.py"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "build_wiki_home", "description": "The conversation involves a Python script designed to update the home page of a wiki based on modified markdown content. The script first loads the current wiki settings, including language and user instructions. It then prepares a prompt for AI to evaluate the relevance of the new content for the wiki's front page. If deemed relevant, the AI updates the home page content to ensure it is coherent and well-structured. The updated content is then saved, and the process is logged for successful completion or errors.", "created_at": "2025-09-06 13:28:58.498720", "updated_at": "2025-09-06T13:37:08.298943", "mode": "task", "kanban_id": "", "column_id": "", "board": "Wiki manager", "column": "Requirements", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Wiki manager/Requirements/build-wiki-home.12bde209-5f75-4096-a454-868da745640f.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "020979c2-6d72-456f-b875-d1830daae4a3", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-06 13:28:58.495529", "updated_at": "2025-09-06 13:28:58.495558", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Create method build_wiki_home.
Method will create/update the content of the "home" file.
Use user instructions and language.
Method will receive markdown content from a modified project file.
AI must decide if the content is relevant for the front page of the wiki and update home page with the important information coming from the content.

Generate only the method
## [[{"doc_id": "ab927146-189b-42e5-bfff-c73acd3f7729", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-06 13:28:58.495529", "updated_at": "2025-09-06 13:28:58.495558", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]


## [[{"doc_id": "2a33078d-4565-4a3b-8cb4-f241cb902ce6", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-06 13:28:58.495529", "updated_at": "2025-09-06 13:28:58.495558", "images": [], "files": [], "meta_data": {"time_taken": 12.90778112411499, "first_chunk_time_taken": 0.0001513957977294922, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
```python /shared/codx-junior/api/codx/junior/wiki/wiki_manager.py
def build_wiki_home(self, markdown_content: str) -> None:
    """
    Build or update the content of the home page of the wiki based on provided markdown content.
    The method will decide if the content is relevant for the front page and update accordingly.

    Args:
        markdown_content: The markdown content from a modified project file.
    """
    # Load current wiki settings
    wiki_settings = self.load_wiki_settings()
    user_language = wiki_settings.get("language", "English")
    user_instructions = wiki_settings.get("prompt", "")

    # Prepare the prompt for AI to decide on the relevance of the content
    relevance_prompt = f"""
    <markdown_content>
    {markdown_content}
    </markdown_content>
    <home_page_content>
    {self._read_file(self.wiki_home_path)}
    </home_page_content>
    <user_instructions>
    {user_instructions}
    </user_instructions>
    <user_language>
    {user_language}
    </user_language>

    Analyze the provided markdown content and decide if it contains important information 
    that should be included in the front page of the wiki. If relevant, update the home page content 
    with this information. Ensure that content is coherent and well-structured.
    Generated content must be in user_language: {user_language}
    """
    
    try:
        messages = self._ai_chat(prompt=relevance_prompt)
        updated_home_content = messages[-1].content
        
        # Write the updated content to the home page file
        write_file(self.wiki_home_path, updated_home_content)
        logger.info(f"Wiki home page successfully updated at {self.wiki_home_path}")
        
    except Exception as e:
        logger.exception(f"Error updating wiki home page: {e}")
```
