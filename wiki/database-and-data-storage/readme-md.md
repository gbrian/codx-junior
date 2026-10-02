# codx-junior Wiki Documentation

## ⚙️ Overview
codx-junior is an AI-powered project management sidekick designed for open-source development. It aims to simplify the workflow and streamline tasks within complex projects, serving as a collaborator ready to lighten the load on maintaining open-source initiatives. The goal of developing codx-junior is to free developers from tedious manual tasks so they can focus on creativity (Note from the author).

***

## ✨ Key Features
codx-junior offers a comprehensive suite of tools and capabilities designed to enhance the entire software development lifecycle:

*   **AI-Powered Assistance**: Automates and streamlines modern software development tasks.
*   **Project Management**: Keeps tasks synchronized with the codebase, ensuring consistency and detailed organization.
*   **Code Generation and Review**: Automates repetitive coding tasks while promoting a structured code review process.
*   **Deployment and Operations**: Simplifies deployment using robust Docker support and automates related operational tasks.
*   **Collaboration & Communication**: Supports effective collaboration through mentions and manages user profiles to tailor code suggestions based on the user's preferences.
*   **Knowledge Sharing**: Utilizes advanced RAG (Retrieval Augmented Generation) indexing for improved response quality and knowledge dissemination.
*   **Development Tools**: Provides a set of tools dedicated to aiding in writing, testing, and debugging code.
*   **Customization (Settings)**: Users can customize the setup to fit specific project requirements.

### How codx-junior Learns
The tool is designed to adapt dynamically. It learns from the projects it works on by analyzing profiles and unique styles and preferences of each repository owner, allowing it to produce code that aligns with established standards and visions. Furthermore, it can utilize multiple Large Language Model (LLM) models to enhance its capabilities and ensure optimal support.

***

## 🚀 Getting Started
Running codx-junior is straightforward using Docker:

**Prerequisites:** Requires Docker installed.

**Installation Steps:**
1. Access the directory containing the deployment files.
2. Run the following command in your terminal, specifying the public image configuration:
    ```bash
    docker-compose -f ./docker-compose-public.yaml up -d
    ```

> **Reference:** Users should check `docker-compose-public.yaml` for custom settings and configurations.

**Accessing the Tool:**
Once the service is running, access codx-junior by navigating to:
`http://localhost:19981` (or any other port specified in your `.env` file).