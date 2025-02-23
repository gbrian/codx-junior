# [[{"id": "bd471aa9-7900-48a1-9a07-0ce78fc40975", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "name": "Prompting", "created_at": "", "updated_at": "2025-01-15T06:58:43.982061", "mode": "chat", "board": "Default", "column": "on going", "chat_index": 0, "live_url": "", "branch": "", "file_path": ""}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-01-15 06:56:53.016156", "updated_at": "2025-01-15 06:56:53.016178", "images": [], "files": []}]]
Generate a prompt for llms instructing to apply best practices lits to a file content. Prompt must include place holders for the file content and the best practices section
## [[{"role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-01-15 06:56:53.016156", "updated_at": "2025-01-15 06:56:53.016178", "images": [], "files": []}]]
Certainly! Here's a structured prompt you can use to instruct a language model to apply best practices to a file's content:

---

**Prompt:**

You are given a section of code that requires improvement by applying best practices. Your task is to refactor the code while ensuring that it adheres to the specified best practices. Please follow the instructions below:

### File Content:
```
{file_content}
```

### Best Practices:
- Ensure code readability by using meaningful variable and function names.
- Implement consistent code formatting (indentation, line spacing, etc.).
- Optimize code for performance where applicable.
- Add comments and documentation to explain complex logic.
- Apply error handling and input validation.
- Write clean and maintainable code following DRY (Don't Repeat Yourself) principles.
- Ensure compatibility with the latest version of the language/framework.
- Add unit tests to verify code functionality.
- Use version control effectively to track changes.
- Document all changes clearly in a changelog.

### Instructions:
1. Refactor the provided code content using the best practices outlined above.
2. Ensure the code is well-commented and documented.
3. Add any necessary unit tests to confirm the correctness of the refactored code.
4. Provide a brief summary of the changes made and the reasoning behind them.

Please proceed with applying these best practices to the given file content.

--- 

This prompt is designed to guide the language model in refactoring code by applying a comprehensive set of best practices.