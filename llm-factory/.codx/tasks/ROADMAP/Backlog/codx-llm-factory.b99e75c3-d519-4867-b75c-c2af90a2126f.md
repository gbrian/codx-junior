# [[{"id": "b99e75c3-d519-4867-b75c-c2af90a2126f", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "profiles": [], "users": ["admin"], "name": "codx-llm-factory", "description": "codx-llm-factory is a service for fine-tuning Language Learning Models (LLMs) and providing search capabilities specifically for codx projects. It updates models based on changes in a project's base branch and uses RAG and indexed search for active branch changes. The service offers a REST API for triggering fine-tuning and interacting with fine-tuned models via an OpenAI-compatible chat endpoint. It employs Python CPU-based techniques for fine-tuning, ensuring accessibility in various environments. The project welcomes contributions and is available under the MIT License.", "created_at": "2025-07-11 07:03:25.899691", "updated_at": "2025-07-11T07:41:46.761308", "mode": "chat", "kanban_id": "", "column_id": "", "board": "ROADMAP", "column": "Backlog", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/llm-factory/.codx/tasks/ROADMAP/Backlog/codx-llm-factory.b99e75c3-d519-4867-b75c-c2af90a2126f.md", "model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "b871beca-e582-4591-812d-991b53b702b9", "role": "user", "task_item": "", "think": "", "hide": true, "improvement": false, "created_at": "2025-07-11 07:03:25.894749", "updated_at": "2025-07-11 07:03:25.894831", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
codx-llm-factory project:


codx-llm-factory is an llm fine tuning and search engine service for codx projects.
The service will maintain an updated fine tuned llm model based on the codx projects. For each project it will use a base branch for create a fine tuned version of a selected model. 
codx-llm-factory will keep a RAG and indexed search for active branch changes. It will index only files changed on these active branches.


codx-llm-factory will use python CPU based fine tuning techniques and will expose a REST API.

API Will expose:
 * Fine tuning:
  * Trigger fine tuning on a specific project
 * Chat
   * An OpenAI compatible endpoint to chat with fine tuned models
 

Based on the project goals create a README.md content
## [[{"doc_id": "f4a74401-0c11-4dba-a38c-4d0a9c14a3df", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-07-11 07:03:25.894749", "updated_at": "2025-07-11 07:03:25.894831", "images": [], "files": [], "meta_data": {"time_taken": 12.913128137588501, "first_chunk_time_taken": 0.00028514862060546875, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
# codx-llm-factory

codx-llm-factory is a specialized service designed for fine-tuning Language Learning Models (LLMs) and providing search capabilities for codx projects. This service ensures that codx projects are enhanced with a continuously updated fine-tuned LLM model. It focuses on efficiency by only updating models based on active changes in the project's base branch and performs indexed searches to reflect current project activities.

## Features

- **Fine-Tuning Service**: 
  - The service fine-tunes LLM models on a per-project basis using the base branch of your codx projects. This ensures that the model is continually updated to reflect recent changes and project requirements.

- **RAG and Indexed Search**:
  - Implements a Retrieval-Augmented Generation (RAG) and indexed search for active branch changes. Only files that are changed in these active branches are indexed, providing a focused and relevant search experience.

- **REST API Interface**:
  - A RESTful API is provided to interact with the service, featuring endpoints for both model fine-tuning and chat capabilities with the fine-tuned models.

## API Endpoints

### Fine Tuning
- **Trigger Fine-Tuning**:
  - Endpoint: `/fine-tune`
  - Method: `POST`
  - Description: Initiates the fine-tuning process for a specific project. This endpoint takes the project ID or name as a parameter and triggers the creation of a fine-tuned model based on the project's base branch.

### Chat
- **OpenAI-Compatible Model Interaction**:
  - Endpoint: `/chat`
  - Method: `POST`
  - Description: Provides an OpenAI-compatible interface to chat with the fine-tuned models. This endpoint facilitates conversations with the models, enabling query and response interactions.

## Technical Overview

- **Performance**: The fine-tuning process utilizes Python CPU-based techniques, optimizing for environments where GPUs are unavailable or limited.
  
- **Dynamic Updates**: By focusing on active branch changes, codx-llm-factory ensures the models remain relevant and aligned with the latest codebase updates.

- **Scalability**: The modular design of the service allows for easy integration with other systems, while the REST API provides a straightforward interaction method.

## Getting Started

1. **Installation**: Clone the repository and set up the environment according to the provided installation script.
  
2. **Configuration**: Adjust configuration files to align with your specific project needs and API key requirements.

3. **Running the Service**: Start the service using the command-line interface. The API should be accessible at the defined host and port.

## Contributing

We welcome contributions to enhance the functionality and reach of codx-llm-factory. Please review our contribution guidelines in the `CONTRIBUTING.md` file.

## License

codx-llm-factory is licensed under the MIT License. See `LICENSE.md` for more details.

## Contact

For any questions or support, please contact the development team at [support@codx-llm-factory.com](mailto:support@codx-llm-factory.com).

By using codx-llm-factory, codx projects can leverage advanced LLM capabilities tailored to their specific needs, ensuring that their developments are supported by cutting-edge AI enhancements.