### Getting Started with codx-junior

Welcome to the `codx-junior` project! This document will guide you through the setup and initial configuration of the project. Follow these steps to get started:

#### 1. Clone the Repository
First, clone the repository from GitHub to your local machine.

```sh
git clone https://github.com/gbrian/codx-junior.git
cd codx-junior
```

#### 2. Setup Docker Compose
Create a `docker-compose.yaml` file in the root directory of the project. This file will define the services required to build and run the `codx-junior` application.

```yaml
version: '3.8'

services:
  codx-junior-build:
    #####################################
    ## BUILD codx-junior IMAGE         ##
    ## it takes time up to 5-8 min     ##
    #####################################
    image: codx-junior:latest
    build: 
      context: .
      # User permissions
      args:
        - USER_GID=${USER_GID:-1001}
        - USER_UID=${USER_UID:-1001}
    environment:
      # Basic
      - CODX_JUNIOR_APPS=client api llm-factory
      
      # With docker in docker, remember to set "privileged=true" in the containers
      # - CODX_JUNIOR_APPS=client api llm-factory docker
    volumes:
      - .:/home/codx-junior/codx-junior
    command: echo "Done"
  
  codx-junior-all:
    # Build image first with "codx-junior-build"
    image: codx-junior:latest
    container_name: codx-junior-all
    shm_size: 4gb
    # Set to true if you want to use docker inside codx-junior
    privileged: true
    environment:
      # Settings file
      - CODX_JUNIOR_GLOBAL_SETTINGS_PATH=/home/codx-junior/.codx-junior/.global_settings.json
      # LLM Settings (Use any OpenAI compatible)
      - CODX_JUNIOR_LLMFACTORY_API=https://api.openai.com/v1
      - CODX_JUNIOR_LLMFACTORY_KEY=sk-********
      - CODX_JUNIOR_LLMFACTORY_KNOWLEDGE_MODEL=gpt-4o
      - CODX_JUNIOR_LLMFACTORY_EMBEDDINGS_MODEL=text-embedding-3-small
    volumes:
      # Keep global settings
      - codx-junior:/home/codx-junior/.codx-junior
      - .:/home/codx-junior/codx-junior
    ports:
      # CODX_JUNIOR_WEB_PORT
      - 8080:19981
      # Reserved ports to expose internal projects
      - 29000-29100:9000-9100
    networks:
      - codx-junior

volumes:
  codx-junior:

networks:
  codx-junior:
```

#### 3. Build the Docker Image
Build the `codx-junior` image using Docker Compose. This step may take some time, typically around 5-8 minutes.

```sh
docker-compose build codx-junior-build
```

#### 4. Run the Application
Once the image is built, you can start the `codx-junior` application.

```sh
docker-compose up -d codx-junior-all
```

### Conclusion
By following these steps, you should be able to set up and run the `codx-junior` project smoothly. If you encounter any issues or have questions, feel free to reach out to the project maintainers or community.

Happy coding!