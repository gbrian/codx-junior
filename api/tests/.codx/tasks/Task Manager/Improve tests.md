# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "Improve tests", "created_at": "2024-11-25T07:19:57.141464", "updated_at": "2024-11-25T07:19:57.141464", "mode": "task", "board": "Task Manager", "column": "new column", "column_index": 10000, "chat_index": 0, "live_url": "", "branch": ""}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-11-25 07:08:40.037285", "updated_at": "2024-11-25T07:16:25.584Z", "images": [], "files": []}]]
Improve tests TestTaskManager. Test more complex responses

## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-11-25 07:08:40.037285", "updated_at": "2024-11-25 07:08:40.037306", "images": [], "files": []}]]
Create new tests with more complex responses. Specially test a response which has a json block inside 
## [[{"role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-11-25 07:08:40.037285", "updated_at": "2024-11-25 07:08:40.037306", "images": [], "files": ["/test_task_manager.py"]}]]
To enhance the tests in `TestTaskManager` with more complex responses, particularly focusing on JSON blocks, you can introduce variations such as nested JSON objects and arrays. Here are some additional test cases that you can add:

```python
# File: /projects/codx-junior/api/tests/test_task_manager.py
class TestTaskManager(unittest.TestCase):
    def setUp(self):
        # Create a mock session
        self.mock_session = MagicMock()
        self.task_manager = TaskManager(session=self.mock_session)

    def test_create_tasks_from_prompt_nested_json(self):
        # Mock AI response with nested JSON
        self.mock_session.get_ai().chat.return_value = [
            MagicMock(content='Some pre-text\n```json\n[\n  {"task_name": "Task 1", "details": {"task_description": "## Description 1", "due_date": "2023-12-01"}},\n  {"task_name": "Task 2", "details": {"task_description": "## Description 2", "due_date": "2023-12-02"}}\n]\n```Some post-text')
        ]

        prompt = "Please create tasks for project X with details"
        tasks = self.task_manager.create_tasks_from_prompt(prompt)
        
        expected_tasks = [
            {"task_name": "Task 1", "details": {"task_description": "## Description 1", "due_date": "2023-12-01"}},
            {"task_name": "Task 2", "details": {"task_description": "## Description 2", "due_date": "2023-12-02"}}
        ]
        
        self.assertEqual(tasks, expected_tasks)

    def test_create_tasks_from_prompt_json_array_with_varied_data(self):
        # Mock AI response with JSON array containing varied data
        self.mock_session.get_ai().chat.return_value = [
            MagicMock(content='Some pre-text\n```json\n[\n  {"task_name": "Task 1", "task_description": "## Description 1", "priority": "high"},\n  {"task_name": "Task 2", "task_description": "## Description 2", "priority": "low", "tags": ["urgent", "backend"]}\n]\n```Some post-text')
        ]

        prompt = "Please create tasks for project Y with priorities"
        tasks = self.task_manager.create_tasks_from_prompt(prompt)
        
        expected_tasks = [
            {"task_name": "Task 1", "task_description": "## Description 1", "priority": "high"},
            {"task_name": "Task 2", "task_description": "## Description 2", "priority": "low", "tags": ["urgent", "backend"]}
        ]
        
        self.assertEqual(tasks, expected_tasks)

    def test_create_tasks_from_prompt_malformed_json(self):
        # Mock AI response with malformed JSON
        self.mock_session.get_ai().chat.return_value = [
            MagicMock(content='Some pre-text\n```json\n{\n  "task_name": "Task 1", "task_description": "## Description 1",\n  "task_name": "Task 2", "task_description": "## Description 2"\n}\n```Some post-text')
        ]

        prompt = "Please create tasks for project Z"
        with self.assertRaises(ValueError) as context:
            self.task_manager.create_tasks_from_prompt(prompt)
        
        self.assertTrue("Failed to parse tasks from response:" in str(context.exception))

```

### Explanation:
- **Nested JSON**: This test checks if the function can handle nested JSON objects by including a `details` field in each task.
- **Varied Data in JSON Arrays**: This test includes additional fields like `priority` and `tags` to see if the function can parse arrays with varied data structures.
- **Malformed JSON**: This test ensures the function correctly raises an exception when it encounters JSON with structural issues.

These tests will help ensure that your `TaskManager` can handle more complex and varied JSON responses from the AI.