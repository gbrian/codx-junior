# Junior Coding Platform Backend

## Overview

The Junior Coding Platform Backend domain defines the comprehensive API architecture and core business logic layer for the codx-junior educational platform. This module is essential for managing all critical, user-facing operations related to learning progress, access control, billing, and content viewing. It serves as a robust API gateway that abstracts complex backend functions into manageable endpoints.

**Key Responsibilities:**

*   **Billing & Validation:** Implementing wallet validation (`wallet_check.py`) to govern feature access and premium usage.
*   **Analytics:** Generating granular user analytics and consumption tracking, critical for reporting, monetization strategies, and educational progress assessment.
*   **Content Management:** Governing the view lifecycle (defining which content is available and how users navigate through lessons via `view_manager.py`).
*   **Architecture:** Provides a structured, API-first approach to defining CRUD endpoints and managing session state across the application.
*   **DevOps:** Includes scripts for environment setup, development containerization, and deployment management.

## Files in Domain

This domain encompasses configuration settings, infrastructural tools, and three main packages responsible for core business logic: AI/Wallet, Analytics, and Views.

| File Path | Type | Description | Key Functionality |
| :--- | :--- | :--- | :--- |
| `build-docker.sh` | Shell Script | Container orchestration and deployment script. | Manages the development environment build process, ensuring consistency across local machines and staging environments. |
| `.vscode/settings.json` | Configuration (Client) | VSCode workspace settings. | Ensures developers have standardized configuration for working within the project codebase. |
| `code-server/User/settings.json` | Configuration (Remote) | Code Server user settings. | Defines persistent settings for remote development sessions, managing developer productivity environment. |
| `api/codx/junior/ai/wallet_check.py` | Core API Logic | Handles advanced logic related to billing and resource access. | The primary interface for validating a user's payment status or resource availability before allowing progress (Access Control). |
| `api/codx/junior/analytics/__init__.py` | Package | Collects, processes, and stores usage data. | Tracks user actions, lesson completion rates, time spent, and consumption metrics necessary for reporting and monetization decisions. |
| `api/codx/junior/api/views.py` | Core API Endpoint | Defines the main routing logic for educational content views. | Acts as a router or controller layer, directing incoming requests to the correct view manager based on user context and lesson ID. |
| `api/codx/junior/views/view_manager.py` | Utility Module | Manages the state and progression of educational content. | Determines if a user is authorized to access a specific viewing resource, managing the educational flow structure. |

## Dependencies

The modules within this domain are highly interconnected, forming a cohesive API stack. Key logical dependencies include:

*   **Views $\leftarrow$ Wallet/Access Control:** Before `view_manager.py` can grant access to an educational view, it must call methods in `wallet_check.py` to ensure the user has paid or earned sufficient credits.
*   **Analytics $\rightarrow$ All Modules:** Nearly every action performed by the platform (accessing a view, checking wallet status) should trigger logging events handled by the analytics mechanism, making this dependency cross-cutting concerns.
*   **Views/API $\leftarrow$ Configuration:** All client and server configurations are foundational dependencies that ensure environment variables and paths are correctly set before code execution.

## Used By

Since this domain represents the core backend API logic, it is consumed (used by) internal or external clients:

1.  **Frontend Client Application:** The primary user interface (Web/Mobile App) makes direct calls to the endpoints exposed by `views.py` and relies on validation from `wallet_check.py`.
2.  **API Gateway / Edge Layer:** A preceding API gateway consumes this domain's services, providing rate limiting, authentication middleware, and routing *before* the request hits the business logic layer.
3.  **Admin/Management Dashboard:** Backend systems (e.g., billing reconciliation or content management dashboards) directly integrate with `wallet_check.py` and `analytics/__init__.py` to pull metrics and manage user accounts.

## Entry Points

Entry points define how a system starts up, performs validation, or requires the initial setup of the development environment.

1.  **Environment Setup & Deployment:**
    *   `/home/codx-junior-projects/codx-junior/build-docker.sh`: Used to initialize the entire development stack and create containerized build environments (Docker).
2.  **Core Business Logic Execution:**
    *   `api/codx/junior/ai/wallet_check.py`: The primary programmatic entry point for validating user status or initiating billing checks before any core functionality is executed.
3.  **Developer Environment Configuration:**
    *   `/home/codx-junior-projects/codx-junior/.vscode/settings.json` and `/home/codx-junior-projects/codx-junior/code-server/User/settings.json`: These files dictate the environment setup required for developers to successfully contribute code.
4.  **API Route Definition (Conceptual):**
    *   Via API calls to endpoints defined in `api/codx/junior/api/views.py`, external clients initiate interactions with the educational platform's content progression system.