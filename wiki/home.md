# Welcome to Codx-Junior Project
Codx-Junior is a comprehensive platform designed to streamline development workflows and automate operational tasks. This project integrates advanced AI capabilities with robust backend infrastructure to provide a seamless and highly standardized software engineering experience.

## Project Overview
The Codx-Junior architecture is built around several core, interconnected pillars:
*   **Intelligent Agent Framework**: Utilizing specialized AI agents (DevOps, Git Issues, and Base Agent) to assist with complex software workflows, automating tasks from code generation to deployment preparation.
*   **Knowledge Management System**: A robust system for ingesting, processing, storing, and retrieving technical knowledge using advanced embeddings, document chunking techniques, and vector databases (e.g., Milvus).
*   **Automation & Operations**: A dedicated CLI-driven system overseeing process lifecycles, deployments across containers, and real-time monitoring via a standardized operational layer. Includes network monitoring capabilities through tools like Scan Watcher for observing outbound traffic and system activities.
*   **Infrastructure & Networking**: A modern service orchestration layer that utilizes **Traefik** as the automated reverse proxy for seamless service discovery and secure inter-container communication.

## AI Model Configuration
The platform is powered by industry-leading AI models, primarily utilizing **Qwen2.5-7B-Instruct** for high-quality, balanced text generation, while also providing modular support for other accelerators like VLLM (optimized for CPU/GPU targeting) and OpenAI API integration, ensuring maximum flexibility for advanced NLP tasks within the codx-junior ecosystem.

## Development Environment & Setup
To ensure ultimate consistency and stability across all development instances, we mandate a highly standardized environment setup. The use of `set_env.sh` is the single source of truth for initialization.

**Key Operational Standards:**
*   **Environment Stability**: All deployments require strict environmental configuration checks (e.g., ensuring correct locale settings like `LANG=en_US:en`) before execution begins to guarantee repeatable and predictable behavior across operating system boundaries.
*   **Critical Credentials**: Critical credentials, such as API keys (`CODX_JUNIOR_LLMFACTORY_KEY`), must never be hardcoded. They must always be dynamically sourced from the external runtime environment variables for security best practices.
*   **Path Initialization**: Environment paths are established reliably by prioritizing existing OS variables and falling back to defined default values, guaranteeing that internal modules can locate dependencies regardless of execution context.

This rigorous standardization ensures seamless container orchestration and reproducible development experiences across all workspaces.