# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "Test browser", "created_at": "2024-11-09T17:11:05.558606", "updated_at": "2024-11-09T17:36:54.375223", "mode": "browser", "board": "Browser", "column": "new column", "column_index": 10000, "chat_index": 0, "live_url": "", "branch": ""}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-11-09T17:11:05.558654", "updated_at": "", "images": [], "files": []}]]
How many starts does have codx-junior?
## [[{"role": "", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-11-09T17:36:54.375362", "updated_at": "", "images": [], "files": []}]]
{
  "task": "Retrieve star count for codx-junior repo!",
  "instructions": [
    "go_to(\"https://github.com/gbrian/codx-junior\")",
    "wait_until(S('.social-count').exists)",
    "write(S('.social-count').text(), S('body'))"
  ]
}