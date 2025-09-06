# [[{"id": "b14c1336-1db2-4fe3-b443-c58bd1ca8446", "doc_id": null, "project_id": "ac9804d5-fcb2-4026-81c0-61f2308f6380", "parent_id": "12bde209-5f75-4096-a454-868da745640f", "status": "", "tags": [], "file_list": [], "check_lists": [], "profiles": [], "users": [], "name": "Add categories to the home page", "description": "1. The task involves modifying the `build_wiki_home` method in a Python script to update a wiki's home page content based on provided markdown content.\n2. The method should strip the \"files\" field from the current categories before using them in the AI prompt for relevance analysis.\n3. The AI prompt is structured to include the markdown content, existing home page content, stripped categories, user instructions, and language preferences.\n4. The AI determines the relevance of the markdown content for inclusion on the wiki's front page, ensuring the content is coherent and well-structured.\n5. The updated home page content is then written to the home page file, with logging for successful updates and exception handling for errors.", "created_at": "2025-09-06 13:43:12.162587", "updated_at": "2025-09-06T13:53:35.197016", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Wiki manager", "column": "Requirements", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Wiki manager/Requirements/add-categories-to-the-home-page.b14c1336-1db2-4fe3-b443-c58bd1ca8446.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "d41fca92-5b1a-4ded-8721-915776e4a46f", "role": "user", "task_item": "", "think": "", "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-06 13:43:12.160296", "updated_at": "2025-09-06 13:43:12.160325", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
Home page must receive the categories information. For this first we need to strip the "files" field from the current categories before using in the AI prompt
## [[{"doc_id": "b359e43f-37b3-4186-9373-3a8748371683", "role": "assistant", "task_item": "", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-06 13:43:12.160296", "updated_at": "2025-09-06 13:43:12.160325", "images": [], "files": [], "meta_data": {"time_taken": 15.861664772033691, "first_chunk_time_taken": 0.010686159133911133, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To ensure that the home page receives the categories information without the "files" field, you need to modify the `build_wiki_home` method to strip the "files" field from the categories before including them in the AI prompt. Here’s how you can do it:

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

    # Strip the "files" field from the categories
    categories_without_files = [
        {key: category[key] for key in category if key != "files"}
        for category in self._get_all_categories(wiki_settings["categories"])
    ]

    # Prepare the prompt for AI to decide on the relevance of the content
    relevance_prompt = f"""
    <markdown_content>
    {markdown_content}
    </markdown_content>
    <home_page_content>
    {self._read_file(self.wiki_home_path)}
    </home_page_content>
    <categories>
    {json.dumps(categories_without_files, indent=2)}
    </categories>
    <user_instructions>
    {user_instructions}
    </user_instructions>
    <user_language>
    {user_language}
    </user_language>

    Analyze the provided markdown content and decide if it contains important information 
    that should be included in the front page of the wiki. If relevant, update the home page content 
    with this information. Ensure that content is coherent and well-structured.
    Remember that the home page must show a high level overview don't deep down into details user will navigate the wiki for this.
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

In this code, I've added a step to strip the "files" field from each category before passing them to the AI prompt. This ensures that the AI receives only the necessary category information for updating the home page.