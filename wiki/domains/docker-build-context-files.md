# Docker Build Context Files

## Overview

Docker build contexts dictate which local filesystem resources are available to the Docker daemon during an image build process. Managing this context effectively is crucial for optimizing container builds, ensuring speed, and maintaining a secure final artifact. The primary configuration file used for pruning unnecessary files from the context is typically named `.dockerignore`.

This domain manages the rules encoded in the `.dockerignore` file—a powerful complement to `.gitignore`. While Git ignores files it never tracks, Docker build contexts must explicitly ignore these potentially large or irrelevant files (such as dependency folders, local cache directories, and node module directories) before sending them to the daemon. By excluding these assets, we dramatically reduce context overhead, save bandwidth, prevent layer bloat, and ensure that the final container image contains only necessary application code and configuration, leading to smaller and faster builds.

**Key Purpose:** Optimization of build speed and size through deliberate filesystem exclusion.

## Files in Domain

### `.dockerignore`

This file specifies patterns (files, directories, or combinations thereof) that should be excluded from the build context sent to Docker. It operates similarly to `.gitignore`, but its operational impact is specific to preventing files from being uploaded for the image build phase.

**Example Use Case:** To ensure that large dependency folders (`node_modules`) or temporary development assets (like IDE cache directories, e.g., `.idea`) are not included in the Docker context, slowing down the build and potentially bloating the final layer:

```dockerfile
# Example inclusion of a virtual environment setup file
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# The .dockerignore handles excluding the massive artifacts
# such as the venv directory structure itself or build caches.
# Exclude dependency folder artifacts, cache files, and local dev tools.
node_modules/
__pycache__/
*.log
build/
.idea/
```

## Dependencies

This domain does not rely on other specific configuration files listed in the project domain model for its core functionality, as it is a self-contained exclusion mechanism. However, conceptually, it relies heavily on:

*   **.gitignore:** While serving the same general purpose of ignoring dev artifacts, `.dockerignore` specifically addresses the *runtime/build context* issue that merely ignoring files from Git does not solve (Docker still needs to know what *not* to include when gathering the full directory structure).
*   **Project Structure:** The effectiveness of this domain requires deep knowledge of the project's specific build tooling (e.g., knowing if a Vite build output or Python virtual environment is being used) to target exclusions accurately.

## Used By

This context management file is utilized whenever a `docker build` command is executed within the project root directory containing the `.dockerignore` file. Common scenarios include:

*   **CI/CD Pipelines:** Automated builds that use Docker commands (e.g., running `docker build -t myapp:latest .`).
*   **Local Development Setup:** Developers building local images for testing and deployment (`docker-compose up --build`).
*   **Containerization Tooling:** Any scripts or workflows wrapper around the core `Dockerfile` that initiates the image build process.

## Entry Points

`.dockerignore` is considered a critical entry point because its content directly governs the input to the Docker daemon, making it a prerequisite for any successful and optimized build lifecycle.

1. **Primary Build Context Definition:** The file must be present in the root directory where `docker build .` is executed.
2. **Build Optimization Check:** Must be reviewed first whenever new directories (especially generated or large dependency folders) are introduced to the project structure, ensuring appropriate exclusion rules are defined immediately.