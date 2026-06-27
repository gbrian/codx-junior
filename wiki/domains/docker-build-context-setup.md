# Docker Build Context Setup
## Overview

The Docker Build Context Setup module manages how local project files are provided to the Docker daemon during image creation. This process utilizes a dedicated file, **`.dockerignore`**, which serves the exact functional purpose of Git's `.gitignore`, but specifically for the build context.

When you run `docker build .`, Docker packages the entire contents of the current directory (the "context") and transfers it to the Docker daemon. If this context includes unnecessary files—such as large test directories, local node modules, temporary cache folders, IDE settings, or sensitive configuration secrets—it:
1.  Increases the transfer time between the host machine and the daemon.
2.  Slows down the build process unnecessarily.
3.  Potentially allows unintended artifacts to be included in layers, leading to a bloated or insecure final image.

By defining patterns within `.dockerignore`, developers explicitly tell Docker *what not* to send, ensuring that only essential source code and necessary assets are included in the transfer context, thus optimizing build performance and resulting image size.

## Files in Domain

**`.dockerignore`**
This is a plain text file placed at the root of the project directory. It contains file paths and directory patterns (similar to those used in `.gitignore`) that should be excluded from the build context sent to Docker.

*   **Purpose:** To minimize the scope of files transferred to the builder, ensuring only relevant code reaches the daemon.
*   **Common Entries:** `node_modules/`, `*.log`, `.vscode/**`, `dist/**` (if handled by a separate build stage), cache directories (`/.cache`), and secrets directory references.

## Dependencies

This module does not technically depend on specific source files within the project structure, but its effectiveness relies conceptually on two major components:

1.  **Docker CLI:** The primary mechanism for reading and utilizing the `.dockerignore` file during the `docker build` command execution.
2.  **Project Directory Structure:** Understanding the layout of external build artifacts (e.g., Vite output, local test reports) is crucial to ensure they are correctly excluded from the context sent to Docker.

## Used By

The principles governed by this domain are integral to several development workflows:

*   **Containerized CI/CD Pipelines:** Ensures that CI runners only process necessary code when building images.
*   **Development Environments (Local Builds):** Dramatically speeds up local testing and debugging cycles by preventing the transfer of large, transient cache files.
*   **Docker Compose:** When defining services that build images locally using `docker-compose build`, proper `.dockerignore` setup is mandatory for efficiency.

## Entry Points

The primary entry point for leveraging this domain functionality is executing the standard Docker build command from within the project root directory:

```bash
# The build command automatically reads the .dockerignore file 
# located in the current working context (.) before packaging files.
docker build -t image-name:tag . 
```