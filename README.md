# codx-junior
Your junior assistant for Full Stack Developers... without too much time to lose ;)

## Motivation

As a Full Stack Developer working for different customers, I'm supposed to be able to deal with everything, know everything, and fix everything... ASAP!
> From front, to back, to database, cloud, DevOps...

and don't get me wrong, I love it! but it's a titan task, don't you? 

So I started developing codx-junior to have an AI that can manage all tedious and repetitive tasks in software development and IT. 

I want codx-junior to help me deal with projects I don't know and situations where `"the last developer left yesterday and there's no doc."` 

I want codx-junior to write better `code` than me, better `tests` than me, and, of course, keep `documentation` updated.

### Hello codx-junior

![image](https://github.com/user-attachments/assets/025b7177-3db8-4d6b-886d-4bb9fb037f77)

## PNRL: Play now read later

Default setup will run a docker container with codx-junior and will map codx-junior repo parent's path to connect with host's projects. 

### dev environment

#### docker
```sh
  git clone https://github.com/gbrian/codx-junior.git
  cd codx-junior
  # change `.env.dev` as needed
  # Set HOST_PROJECTS_ROOT_PATH to your host project's path
  ########################################### 
  ## It's important have same path between 
  ## host project's and container 
  ###########################################
  HOST_PROJECTS_ROOT_PATH="$(dirname $PWD)" \
  HOST_USER="$(id -u):$(id -g)" \
  docker-compose -f docker-compose.dev.yaml up -d
```

#### bash
```sh
  git clone https://github.com/gbrian/codx-junior.git
  cd codx-junior
  # change `.env.dev` as needed
  source .env.dev
  bash installer.sh
  bash run_client.sh &
  bash run_api.sh &
```

After you should be able to access codx-junior at: 
http://localhost:9983

## codx-junior builtin features

### Knowledge
codx-junior uses RAG techniques to find relevant parts of the code for your tasks or giving support

![image](https://github.com/user-attachments/assets/fbbd1591-586b-47dc-9991-b7e392b8d38f)

### Tasks
codx-junior is agile and task based. Create task and polish it with codx-junior until you are ready to generate code

![image](https://github.com/user-attachments/assets/64aa5c7c-6c40-41bc-abdc-2f93a84b60c0)

### Wiki
Documentation is always the first part that gets outdated... not anymore. codx-junior will take care and keep it updated for you.

![image](https://github.com/user-attachments/assets/0e29b06f-94af-4177-bf31-038370e910c3)

### Personalize
Define how do you want codx-junior to perform, code styling, ...

#### Settings
![image](https://github.com/user-attachments/assets/d767b29b-f014-4d65-b351-c83aed40d622)

#### Profiles
![image](https://github.com/user-attachments/assets/60911bd2-d26f-4e82-bc32-a77c1b0c105e)

### Mentions (aka copilot)

Mentions allow you to reference specific parts of your project or codebase for easier management and collaboration. Below is a demonstration video on how to use mentions effectively:

To use mentions, simply name codx as in any other platform `@codx` tag followed by the specific instruction or note you want to add. For example:
```markdown
`@codx`: --knowledge @codx-junior-api Add a link to webm video from "assets/codx_mentions_demo.webm". And explain about mentions and how to use it
```
This will notify the system to process the mention and make the necessary changes or additions.

### Code generation
Ofc... we are here for this :) so just press "code" button or use mentions to create code

```           _                 _   _             
          (_)               | | (_)            
 _ __ ___  _  __ _ _ __ __ _| |_ _ _ __   __ _ 
| '_ ` _ \| |/ _` | '__/ _` | __| | '_ \ / _` |
| | | | | | | (_| | | | (_| | |_| | | | | (_| |
|_| |_| |_|_|\__, |_|  \__,_|\__|_|_| |_|\__, |
              __/ |                       __/ |
             |___/                       |___/ 
```

This project initially branched from [gpt-engineer](https://github.com/gpt-engineer-org/gpt-engineer), but it has since evolved independently. Below is a list of open-source projects utilized in `codx-junior`:

- **mypy**: A static type checker for Python.
- **openai**: Provides access to OpenAI's GPT models.
- **pre-commit**: A framework for managing and maintaining multi-language pre-commit hooks.
- **pytest**: A framework for writing simple and scalable test cases.
- **termcolor**: For ANSI color formatting for terminal output.
- **rudder-sdk-python**: A Python SDK for RudderStack.
- **dataclasses-json**: A simple library to serialize Python dataclasses into JSON.
- **python-dotenv**: Reads key-value pairs from a `.env` file and set them as environment variables.
- **langchain**: A library for building language models.
- **agent-protocol**: A protocol library for building agent-based systems.
- **tk**: Toolkit for creating GUIs.
- **flask**: A web framework for building APIs.
- **Werkzeug**: A utility library for WSGI applications in Python.
- **gunicorn**: A Python WSGI HTTP Server for UNIX.
- **chromadb**: A vector database for machine learning applications.
- **esprima**: A JavaScript syntax parser.
- **python-slugify**: A library to generate slugs from strings.
- **httpx**: A next-generation HTTP client for Python.
- **llama-index**: A library for building and querying data indexes.
- **langchain-community**: Community extensions for Langchain.
- **tree_sitter**: A parser generator tool and an incremental parsing library.
- **apscheduler**: A library for scheduling Python jobs.
- **uvicorn**: A lightning-fast ASGI server implementation, using `uvloop` and `httptools`.
- **pexpect**: A library for controlling and automating applications.
- **langchain-anthropic**: Tools for language generation with Anthropic models.
- **fastapi_socketio**: A FastAPI extension for real-time communication using WebSockets.
- **pytesseract**: A Python wrapper for Google's Tesseract-OCR Engine.
- **pillow**: A Python Imaging Library.
- **helium**: A Python library for Selenium-based browser automation.
- **beautifulsoup4**: A library for parsing HTML and XML documents.
- **markdownify**: A library to convert HTML to Markdown.
- **pymilvus**: A Python SDK for Milvus, a vector database.