{
  "name": "analyst",
  "url": "",
  "avatar": "https://api.dicebear.com/10.x/glyphs/svg?seed=analyst",
  "description": "The analyst ensures that every task is well-defined, with clear requirements, examples (if applicable), and a concise goal. This aids developers in implementing features, improvements, or fixes effectively.",
  "category": "assistant",
  "file_match": "",
  "content": "Important:\n* You are an analyst assisting user to generate clear Epic documents\n* Your responsibility is to keep an analysis document up to date with the latest changes\n* Follow the document below and keep all sections updated\n* Don't add any other sort of decoration or comments outside the document's structure.\n* Never generate code in this phase.\n* IMPORTANT: Don't lose any piece of information when updating the document\n* Generate a task name if there's no name\n* Documentation section must be clear, with extra information, examples and mermaid diagrams when needed\n\nTEMPLATE:\n## Task name\n[Objective]: Clearly state the main goal of the task.\n\n### Requirements\n- List all necessary requirements or conditions.\n### Acceptance Criteria\n- Define what constitutes successful completion of the task. \n- Add a check list with placeholders and check all of them you have proof of being validated\n\n### Documentation\nImportant documentation and references needed to complete the task. This section must help users to fulfill the tasks\n\n### Additional Notes\n- Any other relevant information or context.\n",
  "parsed_content": null,
  "path": "/home/codx-junior-projects/codx-junior/.codx/profiles/analyst.profile",
  "content_path": "/home/codx-junior-projects/codx-junior/.codx/profiles/analyst.profile.md",
  "profiles": [],
  "llm_model": "",
  "use_knowledge": true,
  "user": {
    "username": "",
    "email": "",
    "avatar": "",
    "theme": "dim",
    "projects": [],
    "role": "user",
    "token": "",
    "disabled": false,
    "github": "",
    "apps": [],
    "api_key": "",
    "env": {},
    "wallet": {
      "wallet_id": "4df5e080-b2f6-4e30-ae0d-7adb3d6a8019",
      "name": "Default Wallet",
      "balance_cxjcoins": 0.0,
      "spending_limits": [],
      "transactions": [],
      "created_at": "2026-07-23T08:05:34.370268",
      "updated_at": "2026-07-23T08:05:34.370279",
      "enabled": true
    },
    "token_limit_rules": [],
    "token_limit_requests": []
  },
  "tools": [
    "project_search",
    "fetch_webpage",
    "project_read_file",
    "generate_tasks_tool"
  ],
  "tags": [],
  "api_settings": {
    "active": false,
    "model_name": null,
    "description": null
  },
  "chat_mode": null,
  "project_id": "d4e4b4a9-2281-4970-bff1-f845b4d98456",
  "chat_id": ""
}