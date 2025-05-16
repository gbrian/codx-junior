This document outlines the steps required to set up and run the `codx-junior` project locally using Docker Compose.

## Clone the Repository

Clone the repository from GitHub and navigate into the project directory:

```sh
git clone https://github.com/gbrian/codx-junior.git
cd codx-junior
```

## Review `docker-compose.yaml`

Review the `docker-compose.yaml` file in the root of the project and adapt to your needs. 
This file defines the services necessary to build and run the `codx-junior` application.

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

## Build the Docker Image

Use Docker Compose to build the `codx-junior` image. This process typically takes 5–8 minutes.

```sh
docker-compose build codx-junior-build
```

## Run the Application

Start the application with the following command:

```sh
docker-compose up -d codx-junior-all
```

This will run `codx-junior` in the background. Once running, you can access the application at `http://localhost:19981`.

## Notes

- Make sure Docker is installed and running.
- Set a valid OpenAI-compatible API key in `CODX_JUNIOR_LLMFACTORY_KEY`.
- If you need Docker-in-Docker support, ensure `privileged: true` is set (as shown).

## Conclusion

After completing these steps, `codx-junior` should be up and running. If you encounter issues, consult the repository README or contact the maintainers.

Happy coding!