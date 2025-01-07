# [[{"id": "0", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "Logs api endpoint", "created_at": "2024-10-20T06:10:18.336736", "updated_at": "2025-01-06T06:06:58.794335", "mode": "task", "board": "Default", "column": "tasks", "chat_index": 0, "live_url": "", "branch": "", "file_path": "/home/codxuser/projects/codx-junior/api/.codx/tasks/Default/tasks/Logs api endpoint.md"}]]
## [[{"role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-10-20T06:40:00.570274", "updated_at": "2025-01-05 13:20:27.838221", "images": [], "files": ["/codx/junior/engine.py", "/codx/junior/profiles/roles/software_developer", "/codx/junior/utils.py"]}]]
**TASK: Create New API Endpoints for Logs**

**Objective:**
Develop two new API endpoints to manage and retrieve application logs. These endpoints should follow RESTful design principles and integrate seamlessly with the existing project architecture and conventions.

**Endpoints:**

1. **Endpoint:** `/api/logs`
   - **Method:** GET
   - **Description:** Returns a list of available log types from the `supervisor.conf` file.
   - **Response:** JSON array containing the names of the logs.

2. **Endpoint:** `/api/logs/{log_name}`
   - **Method:** GET
   - **Description:** Returns the last X lines from the specified log using the `exec_command` utility function.
   - **Parameters:**
     - `log_name`: The name of the log file to retrieve. This is a dynamic parameter.
     - `lines` (optional query parameter): The number of last lines to retrieve. Default value is 100 if not specified.
   - **Response:** JSON object containing the last X lines of the specified log.

**Implementation Details:**

- **Location:** Implement the logic for retrieving logs in a separate module, `logs.py`. The FastAPI routing should remain in `app.py` to keep concerns separated.
- **Log Handling:** Utilize the `exec_command` function from `utils.py` to run the `tail` command on log files.
- **Log Sources:** Use the `supervisor.conf` file to identify the available logs. Logs are located at paths specified within `supervisor.conf`, such as `/var/log/supervisor/novnc.log`, `/var/log/supervisor/vncserver.log`, etc.
- **Security:** No additional security measures or access controls are required for these endpoints as per user comments.
- **Validation & Error Handling:** Include input validation and error handling to ensure robustness.

**Example Code Implementation in `logs.py`:**

```python
# /projects/codx-junior/api/codx/junior/logs.py
from codx.junior.utils import exec_command

# Example log directory and default number of lines
LOG_PATHS = {
    "novnc": "/var/log/supervisor/novnc.log",
    "vncserver": "/var/log/supervisor/vncserver.log",
    "dbus": "/var/log/supervisor/dbus.log",
    "kde": "/var/log/supervisor/kde.log",
    "code-server": "/var/log/supervisor/code-server.log",
    "codx-junior-api": "/var/log/supervisor/codx-junior-api.log",
    "codx-junior-web": "/var/log/supervisor/codx-junior-web.log"
}
DEFAULT_LINES = 100

def get_logs() -> list:
    return list(LOG_PATHS.keys())

def get_log_lines(log_name: str, lines: int = DEFAULT_LINES):
    log_path = LOG_PATHS.get(log_name)
    if not log_path:
        raise ValueError("Log file not found")

    try:
        command = f"tail -n {lines} {log_path}"
        result = exec_command(command)
        return {"log_name": log_name, "lines": result.splitlines()}
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve log lines: {e}")
```

**Example Integration in `app.py`:**

```python
# /projects/codx-junior/api/codx/junior/app.py
from fastapi import FastAPI, Query, HTTPException
from codx.junior.logs import get_logs, get_log_lines
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/api/logs")
def api_get_logs():
    return JSONResponse(content=get_logs())

@app.get("/api/logs/{log_name}")
def api_get_log_lines(log_name: str, lines: int = Query(DEFAULT_LINES, gt=0)):
    try:
        return JSONResponse(content=get_log_lines(log_name, lines))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**DOUBTS:**

- Are there any security or access control concerns that need to be addressed when exposing these logs via API?
- Should there be any specific restrictions on the number of lines that can be retrieved to prevent performance issues?