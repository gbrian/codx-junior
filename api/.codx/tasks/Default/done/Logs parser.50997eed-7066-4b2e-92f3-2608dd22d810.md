# [[{"id": "50997eed-7066-4b2e-92f3-2608dd22d810", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "name": "Logs parser", "created_at": "2025-01-17 04:17:58.936905+00:00", "updated_at": "2025-01-17T19:26:37.643109", "mode": "chat", "board": "Default", "column": "done", "chat_index": 0, "live_url": "", "branch": "", "file_path": "/usr/local/codx-junior/api/.codx/tasks/Default/on going/Logs parser.50997eed-7066-4b2e-92f3-2608dd22d810.md"}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-01-15 09:00:42.894638", "updated_at": "2025-01-15 09:00:42.894659", "images": [], "files": []}]]
Create logs parser extracting log information from logs stream.
Exxample of logs:
```txt
[2025-01-15 09:01:58,191] INFO [codx.junior.ai.openai_ai:51] AI response: <openai.Stream object at 0x7f14042ca610>
[2025-01-15 09:02:10,354] DEBUG [codx.junior.ai.openai_ai:94] [2025-01-15T09:02:10.354697] model: gpt-4o, temperature: 0.7
[system]
BEGIN INSTRUCTIONS
        This is a conversation between you and the user about the project codx-ui.
```
We must return a list of objects like this:
```
[
{ "timestamp": "2025-01-15 09:01:58,191", "level": "DEBUG", "module": "codx.junior.ai.openai_ai", "line": 51, "content": "A multiline content can be here" },
{ "timestamp": "2025-01-15 09:01:58,191", "level": "INFO", "module": "", "line": 51, "content": "A multiline content can be here" }
]
```
Log content can be multiple lines, create new entry every time you match the time, leve, module, line 