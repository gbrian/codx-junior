# Welcome to the Codx-Junior Project

Codx-Junior is a comprehensive platform designed to streamline development workflows and automate operational tasks. This project integrates advanced AI capabilities with robust backend infrastructure to provide a seamless development experience.

## Project Overview
The Codx-Junior architecture is built around several core pillars:
*   **Intelligent Agent Framework**: Leveraging specialized AI agents (DevOps, Git Issues, and Base Agent) to assist with complex software engineering workflows.
*   **Knowledge Management**: A robust system for processing, storing, and retrieving technical knowledge using advanced embeddings and document enrichment techniques.
*   **Automation & Operations**: A dedicated CLI-driven system for managing deployments, process lifecycles, and real-time monitoring.
*   **Infrastructure & Networking**: A modern service orchestration layer utilizing **Traefik** as a reverse proxy for automated service discovery and secure inter-container communication.

## AI Model Configuration
The platform utilizes the **Qwen2.5-7B-Instruct** model to drive its intelligent features, optimized for high-quality text generation, balanced sampling, and high-performance inference within the `codx-junior` ecosystem.

## Development Environment
To ensure a consistent development experience, the project provides:
*   **Environment Configuration**: Centralized management via `set_env.sh` and standardized documentation, which serves as the single source of truth for environment variables (e.g., API ports and VLLM target devices), workspace paths, and authentication.
*   **Standardized Tooling**: Support for headless browser automation, containerized GUI rendering, and automated initialization of client and API components.
*   **Workspace Templates**: Standardized folder structures to ensure seamless container orchestration.
*   **Repository Standards**: Strict exclusion rules to maintain clean repositories by ignoring build artifacts, temporary metadata, and sensitive environment data.

---

### 🚨 Key Updates (V5.6.0)
*   **Configuration & Documentation Alignment**: Documentation is now systematically refined to ensure high traceability, linking environment variables directly to the project configuration document, and providing clear mapping for VLLM device targets and log storage paths.
*   **Workflow Integration**: Image building and container management have been generalized to support dynamic `docker-compose` workflows.
*   **Standardized Key Management**: `${CODX_JUNIOR_LLMFACTORY_KEY}` is now mapped to `${LITELLM_MASTER_KEY}` for secure, consistent API access.
*   **Precision Localization**: Internationalization settings now utilize an explicit fallback hierarchy (`LANGUAGE=en_US:en`) for better Linux environment compatibility.
*   **Dependency Management**: Shifted to `pyproject.toml` and `requirements.txt` for enhanced maintainability.

---

## Getting Started
To begin working with the platform, we recommend exploring the following documentation sections:

1.  **Project Overview**: Understand the core philosophy and architectural design.
2.  **Setup and Installation**: Follow the guide to initialize your environment, ensuring all `set_env.sh` exports are correctly configured.
3.  **Deployment and Operations**: Utilize the `app.cli` interface and Traefik dashboard to manage your services.
4.  **AI & Knowledge Management**: Learn how our agents and models integrate to provide intelligent insights.

***

### Useful Links
*   [GitHub Repository](https://github.com/codx-junior)
*   [Docker Documentation](https://docs.docker.com/)
*   [Python Virtual Environments](https://docs.python.org/3/library/venv.html)
*   [Traefik Documentation](https://doc.traefik.io/traefik/)
*   [LiteLLM Documentation](https://docs.litellm.ai/docs/)

***

### Links Preview
* [Docker Documentation - Environment Variables](https://docs.docker.com/compose/environment-variables/)
* [Traefik Proxy Documentation](https://doc.traefik.io/traefik/)
* [Python Virtual Environments Guide](https://docs.python.org/3/library/venv.html)
* [LiteLLM Documentation](https://docs.litellm.ai/docs/): Provides background on `LITELLM_MASTER_KEY` and how it manages API access for LLM gateways.
* [Docker Compose Overview](https://docs.docker.com/compose/): Information on the container orchestration used for the `codx-junior` workflow.