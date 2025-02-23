import json
from codx.junior.engine import CODXJuniorSession
from codx.junior.utils import extract_blocks  # Importing extract_blocks

class TaskManager:
    def __init__(self, session: CODXJuniorSession):
        self.session = session

    def create_tasks_from_prompt(self, prompt: str):
        ai = self.session.get_ai()
        messages = ai.chat(prompt=f"""Generate a list of sub tasks from user's prompt in this format:
        ```json
        [
          {{
            "task_name": "Task name 1",
            "task_description": "## Task description in markdown syntax"
          }}
        ]
        ```
        Output a single JSON array with the task list.
        User request:
        {prompt}
        """)

        response_content = messages[-1].content.strip()

        # Extract the JSON block using the extract_blocks function
        json_blocks = list(extract_blocks(response_content))
        json_data = ""
        
        # Find the JSON block and concatenate its content
        for block in json_blocks:
            if block['type'] == 'json':
                json_data = block['content']
                break
        
        # Parse the JSON response
        try:
            tasks = json.loads(json_data)
            return tasks
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse tasks from response: {e}")