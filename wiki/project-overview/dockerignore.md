# Project Overview

The Codx Junior project is a comprehensive application that integrates client-side interfaces, backend functionality utilizing a specialized database/framework, and advanced generative models. The architecture suggests a full-stack setup designed for AI and data processing capabilities.

## Architecture and Components

The overall structure divides responsibilities into testing, static assets, configuration, model management, and service layers.

### Data and Services
*   **Codx Framework:** Core functionalities and database structures are managed through the `.codx` directory, which includes a dedicated `db` path suggesting persistent data storage and application logic implementation.
*   **Client Application:** The user interface is handled by the client application located within the `client/.vite` structure.
*   **Model Management:** The application integrates with large language models via resources stored in the `ollama_models` directory.

### Development Assets and Infrastructure

Different directories manage various aspects of development, testing, and runtime operations:

| Component | Purpose | Details |
| :--- | :--- | :--- |
| **Assets** | Storage for static content used across the application (e.g., images, fonts). | `assets` |
| **Testing Suite** | Contains all code and resources necessary for running automated unit and integration tests. | `tests` |
| **Development/Cache** | Temporary files and dependencies necessary for build processes (`node_modules`, `.venv`, `__pycache__`). | Included in the root directory. |
| **Logging** | Stores operational records, logs, and runtime data from the application. | `logs` |

### Configuration and Documentation
*   **Documentation:** The dedicated `wiki` folder serves as the repository for project documentation and knowledge articles.
*   **Local Settings:** Global user or environment settings are contained within a specific configuration JSON file (`global_settings.json`).