# CodX-Junior Core Systems

## Overview
The **CodX-Junior Core Systems** domain serves as the architectural backbone and primary data management infrastructure for the CodX-Junior platform. This domain is responsible for maintaining standardized data storage solutions and providing the foundational operational logic required to support general application services.

It acts as the central hub for system configuration, project management workflows, and intelligent service orchestration. By housing critical components such as the `AIManager` and various background services, this domain ensures that AI-driven features and system-level tasks are executed with consistency and reliability across the platform.

### Key Capabilities
*   **AI Model Management:** Controls the lifecycle, loading, and refreshing of AI models via the `AIManager`.
*   **Infrastructure Management:** Orchestrates background services and global system settings.
*   **Data Integrity:** Manages quarantine status and scheduling to ensure system stability during error states or data anomalies.
*   **Project Oversight:** Provides the core logic necessary for tracking project management metadata and operational status.

## Files in Domain
*   `/home/codx-junior/codx-junior/api/wiki/database-and-data-storage/readme-md.md`
*   `domains/general.md`
*   `domains/codx-junior-core.md`

## Dependencies
*   *This domain currently operates as the primary architectural foundation; specific file-level dependencies are integrated within the core module definitions.*

## Used By
*   *This domain provides services utilized across the broader CodX-Junior ecosystem, specifically for components requiring persistent storage access and AI model orchestration.*

## Entry Points
*   `/home/codx-junior/codx-junior/api/wiki/database-and-data-storage/readme-md.md`: Documentation on data storage protocols.
*   `domains/general.md`: General operational guidelines and global settings entry.
*   `domains/codx-junior-core.md`: Primary reference for core architectural logic and service definitions.

***

### Reference Links
* [CodX-Junior Documentation Portal](https://codx-junior.github.io/wiki/)
* [Managing AI Model Lifecycles in Core Systems](https://codx-junior.github.io/wiki/ai-management)
* [Data Storage Standards for CodX-Junior](https://codx-junior.github.io/wiki/database-and-data-storage)