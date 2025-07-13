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