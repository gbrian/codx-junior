import unittest
from unittest.mock import MagicMock
from codx.junior.task_manager import TaskManager

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
            MagicMock(content='Some pre-text\n```json\n{\n { "task_name": "Task 1", "task_description": "## Description 1",\n  "task_name": "Task 2", "task_description": "## Description 2"\n}\n```Some post-text')
        ]

        prompt = "Please create tasks for project Z"
        with self.assertRaises(ValueError) as context:
            self.task_manager.create_tasks_from_prompt(prompt)
        
        self.assertTrue("Failed to parse tasks from response:" in str(context.exception))

    def test_create_tasks_from_prompt_json_with_code_block(self):
        self.mock_session.get_ai().chat.return_value = [
            MagicMock(content='Some pre-text\n```json\n{\n { "task_name": "Task 1", "task_description": "## Description 1 ```json { "a": 2 }```",\n  "task_name": "Task 2", "task_description": "## Description 2"\n}\n```Some post-text')
        ]
        @codx-processing: finish this test

if __name__ == '__main__':
    unittest.main()