# Deployment and Operations: codx-junior

This document outlines the procedures for building the Docker images for the `codx-junior` project.

## Build Process

To generate the latest project images, the build script performs the following steps:

1.  **Environment Preparation**: The script captures the current working directory (`CWD`) and navigates to the `codx-junior-installer/codx-junior` directory.
2.  **Image Construction**: The script utilizes `docker-compose` to build the required images in the following order:
    *   `codx-junior-debian-image`
    *   `codx-junior-api-image`
    *   `codx-junior-image`
3.  **Cleanup**: Once the build processes are complete, the script returns to the original working directory (`CWD`).

### References
*   **Project**: codx-junior
*   **Category**: Deployment and Operations