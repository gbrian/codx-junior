# Build Context Filtering

## Overview
Build Context Filtering defines which files and directories should be included in the context that Docker utilizes when building a container image. The core concept revolves around minimizing the transferred data—only essential artifacts, source code, or configuration files should be packaged into this context. This mechanism is achieved primarily through the use of a `.dockerignore` file (analogous to `.gitignore`).

### Importance
Properly implementing build context filtering is crucial for maintaining the health and efficiency of continuous integration/continuous deployment (CI/CD) pipelines:

*   **Reduced Image Size:** By excluding large, unused assets (like local node modules, test data, or IDE configuration files), we ensure that only necessary code reaches the build stage.
*   **Faster Build Time:** The less data Docker has to transfer and process, the faster the initial stages of the `docker build` command will complete, leading to improved CI reliability.
*   **Security:** Filtering prevents accidental inclusion of sensitive local files (like API keys or database credentials) that should never be part of the image context.

### Practical Use Cases
This domain directly addresses managing ephemeral artifacts such as:

*   Development tools and simulators.
*   Local environment variables dumped into configuration.
*   Large test data directories (`__fixtures__`, `test/`).
*   Automatically generated cache or temporary build outputs (e.g., Vite development bundles).

***

## Files in Domain
*   `.dockerignore`

The `.dockerignore` file is the primary artifact of this domain. It functions identically to a standard `.gitignore` file but specifically tells the Docker client which files and directories *not* to include when creating the build context sent to the daemon.

**Common Exclusions:**
| Pattern | Reason for Exclusion |
| :--- | :--- |
| `node_modules/` | The runtime dependencies should be installed *inside* the container during the respective build stage, not copied from the host machine. |
| `.git/`, `.hg/` | Version control metadata is unnecessary and adds bloat to the context. |
| `*.log`, `cache/` | Temporary logs or local cache files are irrelevant for a clean production build. |
| IDE configs (`.idea/`) | Environment-specific editor configurations clutter the build output unnecessarily. |

***

## Dependencies
There are no external file dependencies managed by this domain. This context filtering mechanism operates entirely upon defining exclusions within the project's root directory relative to the Dockerfile execution.

***

## Used By
This domain is fundamental and is not directly consumed or referenced by other defined software domains in this scope. It serves as a foundational pre-build step required *before* any Docker build process can reliably begin.

***

## Entry Points
The entry point for managing this domain is solely the `.dockerignore` file itself. This file must be present and accurately configured at the project root to ensure that all subsequent builds utilize the minimal context data necessary for optimal performance.