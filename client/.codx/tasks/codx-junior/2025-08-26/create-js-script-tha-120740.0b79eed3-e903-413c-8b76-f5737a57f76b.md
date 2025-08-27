# [[{"id": "0b79eed3-e903-413c-8b76-f5737a57f76b", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Create js script tha - 120740", "description": "In the conversation, the user requested a JavaScript script to detect mobile devices and add debugging scripts to the body if detected. The provided code creates two script elements: one to load Eruda, a JavaScript console for debugging, and another to initialize it. The instructions emphasized returning the markdown document clean, without additional comments.", "created_at": "2025-08-26 08:31:10.201520", "updated_at": "2025-08-26T10:07:45.939281", "mode": "task", "kanban_id": "", "column_id": "", "board": "codx-junior", "column": "2025-08-26", "chat_index": 0, "url": "", "branch": "", "file_path": "", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "ea46c7db-7884-4841-a7a5-e45014676109", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-26 08:31:10.194624", "updated_at": "2025-08-26 08:31:10.194737", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
Create js script that If it is mobile add this to the body: <script src="https://cdn.jsdelivr.net/npm/eruda"></script> <script>eruda.init();</script>
## [[{"doc_id": "15b209db-ab21-4183-94b4-817d7c111ed0", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-08-26 08:31:10.194624", "updated_at": "2025-08-26 08:31:10.194737", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
Create js script that If it is mobile add this to the body: <script src="https://cdn.jsdelivr.net/npm/eruda"></script> <script>eruda.init();</script>
                    Create new document based on user comments.
                    User comments:
                    Create js script that If it is mobile add this to the body: <script src="https://cdn.jsdelivr.net/npm/eruda"></script> <script>eruda.init();</script>
                    Important: Always return the mardown document without any comments before or after, to keep it clean.
## [[{"doc_id": "02a1cf35-67a9-4010-98f9-617b7847d4d4", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-08-26 08:31:10.194624", "updated_at": "2025-08-26 08:31:10.194737", "images": [], "files": [], "meta_data": {"time_taken": 2.6685049533843994, "first_chunk_time_taken": 0.0002548694610595703, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false, "read_by": []}]]
```js /file/path/mobile-check.js
(function() {
  function isMobile() {
    return /Mobi|Android/i.test(navigator.userAgent);
  }

  if (isMobile()) {
    var script1 = document.createElement('script');
    script1.src = "https://cdn.jsdelivr.net/npm/eruda";
    document.body.appendChild(script1);

    script1.onload = function() {
      var script2 = document.createElement('script');
      script2.innerHTML = "eruda.init();";
      document.body.appendChild(script2);
    };
  }
})();
```