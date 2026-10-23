# Web Automation Infrastructure: Browser Use + Ephemeral LinuxServer Webtop

This comprehensive architectural guide explains how to design and build an on-demand web automation infrastructure using **[Browser Use](https://github.com/browser-use/browser-use)** running within an ephemeral **[LinuxServer.io Webtop](https://docs.linuxserver.io/images/docker-webtop/)** Docker container. It includes complete steps to handle persistent browser contexts, state serialization (cookies and localStorage), and container orchestration.

---

## 🏗️ Core Architectural Strategy

To create a highly reliable, stateless runner that preserves persistent sessions across clean teardowns, the system relies on three layers:

```
[ Your Orchestrator Script ]
      │ (1) Spins up on-demand
      ▼
┌────────────────────────────────────────────────────────┐
│ Docker Host                                            │
│   ┌────────────────────────────────────────────────┐   │
│   │ Container: linuxserver/webtop                  │   │
│   │   ├── Port 6080 / 3000 (VNC/noVNC Debugging)   │   │
│   │   └── Persistent Volumes                       │   │
│   │        └── /config/browser_state/ ◄────────────┼───┼──► [ Host Storage / S3 ]
│   └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

1. **Ephemeral Provisioning:** A controlling orchestration script spins up the `linuxserver/webtop` Docker container on-the-fly when an automation task is triggered.
2. **State Persistence:** Persistent data (session cookies, indexedDB, localStorage) is mapped to a dedicated host directory or object store, allowing Playwright to mount it seamlessly during consecutive launches.
3. **Graceful Teardown:** Once the execution finishes, the container is safely stopped, cleaned, and destroyed to free up host compute overhead.

---

## 🐳 Step 1: Docker Container Infrastructure

The [LinuxServer.io Webtop](https://docs.linuxserver.io/images/docker-webtop/) image provides a full-featured desktop environment inside a container, matching perfectly with Playwright's heavy graphical requirements when running headful browsers under vision-based AI workflows.

### Docker Compose Reference Configuration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  webtop_automation:
    image: lscr.io/linuxserver/webtop:ubuntu-openbox
    container_name: web_automation_runner
    security_opt:
      - seccomp:unconfined # Required for Chrome sandbox behaviors inside Docker
    environment:
      - PID=1000
      - GID=1000
      - TZ=Etc/UTC
      - SUBFOLDER=/ # Adjust if proxying through Nginx/Traefik
    volumes:
      # Mount a local path to retain state files, cookies, and local profiles across instances
      - ./host_browser_state:/config/browser_state
      # Mount your local automation project folder into the runner workspace
      - ./automation_code:/config/workspace
    ports:
      - "3000:3000" # HTTPS Web Desktop UI (useful for real-time monitoring/debugging)
      - "6080:6080" # HTTP VNC UI
    shm_size: "2gb" # Crucial: Prevents browser processes from crashing due to memory starvation
    restart: unless-stopped
```

---

## 🔒 Step 2: Preserving & Re-using Sessions in Browser Use

To prevent being locked out or flagged by login checkpoints upon subsequent browser startups, you must instruct Playwright to explicitly load from and write to a continuous persistent directory profile.

### Configuration Template: `automation_agent.py`

This script leverages `browser-use`'s internal custom browser layout setup to handle persistent sessions out of the box.

```python
import asyncio
import os
from pathlib import Path
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI

# 1. Define paths inside your Docker workspace environment
BROWSER_STATE_DIR = Path("/config/browser_state/user_profile")
BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    # 2. Configure Browser Use to write into a persistent context profile directory
    config = BrowserConfig(
        headless=True,  # Set to False if you want to visually see it execute via the Webtop desktop
        # Point Playwright directly to your state storage volume
        chrome_instance_path=None,  # Use bundled Chromium inside playwright 
        extra_chromium_args=[
            f"--user-data-dir={BROWSER_STATE_DIR}",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]
    )
    
    # Instantiate custom browser architecture configuration
    browser = Browser(config=config)
    
    # 3. Setup Custom Model Configuration
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.0
    )
    
    # 4. Instantiate and invoke your browser automation task
    agent = Agent(
        task=(
            "Navigate to an authenticated dashboard (e.g., https://github.com). "
            "If already signed in via session data, extract my notification count. "
            "If an active session doesn't exist, tell me immediately without trying to guess passwords."
        ),
        llm=llm,
        browser=browser
    )
    
    try:
        result = await agent.run()
        print("Execution Result:", result.final_result)
    finally:
        # Crucial step: Explicitly close the browser context to flush storage files to disk
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## ⚙️ Step 3: Complete Automation Orchestration Lifecycle

Below is an administrative automation pipeline script running on your host machine (or CI/CD manager node). It manages the setup, execution, context preservation, and aggressive resource deletion on-demand.

### Infrastructure Control Pipeline: `run_pipeline.py`

```python
import subprocess
import time
import sys

CONTAINER_NAME = "web_automation_runner"
COMPOSE_FILE = "docker-compose.yml"

def run_command(cmd, shell=False):
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {' '.join(cmd) if not shell else cmd}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def main():
    print("🚀 Phase 1: Provisioning Ephemeral Webtop Environment...")
    # Spin up the containers in detached mode safely
    run_command(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"])
    
    print("⏳ Phase 2: Waiting for VNC and XServer desktop startup initialization...")
    time.sleep(10) # Give LinuxServer init initialization scripts a few seconds to run cleanly
    
    print("📦 Phase 3: Synchronizing systemic Playwright system packages inside the container...")
    # Install dependencies inside the container if not baked into the workspace image
    run_command([
        "docker", "exec", CONTAINER_NAME, 
        "bash", "-c", "pip install browser-use langchain-openai playwright && playwright install chromium"
    ])
    
    print("🤖 Phase 4: Launching Browser Use Automation Script...")
    # Execute the persistent python automation agent inside the container environment
    output = run_command([
        "docker", "exec", CONTAINER_NAME, 
        "python3", "/config/workspace/automation_agent.py"
    ])
    print("
--- AGENT OUTPUT ---")
    print(output)
    print("---------------------
")
    
    print("🔒 Phase 5: Sessions saved to disk successfully via bound volume mappings.")
    print("🧹 Phase 6: Executing aggressive infrastructure teardown...")
    
    # Tear down containers and delete internal ephemeral resources while safely preserving volume data
    run_command(["docker", "compose", "-f", COMPOSE_FILE, "down"])
    print("🎯 Infrastructure closed out elegantly. Host computational overhead reclaimed.")

if __name__ == "__main__":
    main()
```

---

## 💡 Engineering Best Practices for Ephemeral Runners

* **Persistent Context Volume Strategy:** Always use `user-data-dir` inside Playwright arguments rather than manually dumping cookies to structured JSON files. This ensures `localStorage`, `sessionStorage`, `indexedDB` cache records, and user session cookies are seamlessly maintained in sync.
* **Shared Memory Allocations:** Always scale your `--shm-size` parameter to at least `2gb` within Docker. Browsers like Chromium store temporary page graphics rendering structures in system shared memory; the standard Docker container default (`64mb`) will crash the runtime execution during heavy visual analysis workloads.
* **Granular Session Locking:** When writing states concurrently, run separate instances with unique directory paths (e.g., `/config/browser_state/session_abc`). Chromium locks its state tracking directories when initialized, meaning concurrent access calls will block or corrupt user data files.