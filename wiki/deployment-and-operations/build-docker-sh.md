# Deployment and Operations: codx-junior

This document outlines the procedure for building the Docker images for the `codx-junior` project.

## Build Process

To build the project images, navigate to the project directory and execute the build script. The process performs the following steps:

1.  **Directory Navigation**: The script changes the current working directory to `codx-junior-installer/codx-junior`.
2.  **Image Compilation**: It utilizes `docker-compose` to build the required project components in the following order:
    *   `codx-junior-debian-image`
    *   `codx-junior-api-image`
    *   `codx-junior-image`

After the build process completes, the script restores the original working directory.

### References
*   **Project**: codx-junior
*   **Category**: Deployment and Operations