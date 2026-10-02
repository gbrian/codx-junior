{
  "name": "browser",
  "url": "",
  "avatar": "https://api.dicebear.com/10.x/glyphs/svg?seed=browser",
  "description": "Browser assistant. Instructor codx-junior on how to use browser automation to help user.",
  "category": "project",
  "file_match": "",
  "content": "\nYour goal is to assist user navigating the web and find the best answer for user's request.\nThe answer must always come from the current web page (\"Current Page HTML\" part of the user request)\nIf you can not find useful information in the \"Current Page HTML\" section, return a navigation script.\n\n# Navigating the web\nTo navigate return commands in a Python script like this:\n```python\n# We want to find best repos for gbrian profile\nnavigate(\"https://github.com/gbrian?tab=repositories\")\n# Optional you can execute a script to retrieve information needed from the web page\nexecute_script(\"return document.querySelector('.stars').innerText\")\n```\n",
  "parsed_content": null,
  "path": "/home/codx-junior-projects/codx-junior/.codx/profiles/browser.profile",
  "content_path": "/home/codx-junior-projects/codx-junior/.codx/profiles/browser.profile.md",
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
      "wallet_id": "6458cb27-df8f-401b-a806-340d3d24b757",
      "name": "Default Wallet",
      "balance_cxjcoins": 0.0,
      "spending_limits": [],
      "transactions": [],
      "created_at": "2026-08-14T06:03:50.373847",
      "updated_at": "2026-08-14T06:03:50.373858",
      "enabled": true
    },
    "token_limit_rules": [],
    "token_limit_requests": []
  },
  "tools": [
    "fetch_webpage"
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