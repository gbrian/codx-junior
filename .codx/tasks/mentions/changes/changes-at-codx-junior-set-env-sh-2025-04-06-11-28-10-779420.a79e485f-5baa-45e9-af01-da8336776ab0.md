# [[{"id": "a79e485f-5baa-45e9-af01-da8336776ab0", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": ["skip_knowledge"], "file_list": [], "profiles": [], "name": "changes-at-codx-junior-set-env-sh-2025-04-06-11-28-10-779420", "created_at": "2025-04-06 10:17:15.936542", "updated_at": "2025-04-06T11:28:15.186794", "mode": "chat", "kanban_id": "", "column_id": "", "board": "mentions", "column": "changes", "chat_index": 0, "live_url": "", "branch": "", "file_path": "", "model": ""}]]
## [[{"doc_id": "a2f2122b-e8c4-4db8-b3d5-314e706da8fa", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-06 10:17:15.934335", "updated_at": "2025-04-06 10:17:15.934379", "images": [], "files": [], "meta_data": {}, "profiles": []}]]

                      ```
                      # API virtual env
export CODX_JUNIOR_API_VENV=/tmp/.venv_codx_junior_api
# Browser virtual env
export BROWSER_VENV=/tmp/.venv_codx_junior_browser
# codx-junior API port
if [ -z "$CODX_JUNIOR_API_PORT" ];then 
  export CODX_JUNIOR_API_PORT=19980
fi
@codx-ok, please-wait...: change the inline variable check by the if then form
[ -z "$CODX_JUNIOR_API_URL" ] && export CODX_JUNIOR_API_URL=http://0.0.0.0:${CODX_JUNIOR_API_PORT}
# codx-junior web port
[ -z "$CODX_JUNIOR_WEB_PORT" ] && export CODX_JUNIOR_WEB_PORT=19981
# codx-junior code-server port
[ -z "$CODX_JUNIOR_CODER_PORT" ] && export CODX_JUNIOR_CODER_PORT=19982
# Desktop port
[ -z "$CODX_JUNIOR_NOVNC_PORT" ] && export CODX_JUNIOR_NOVNC_PORT=19983
# codx-junior API background port
[ -z "$CODX_JUNIOR_API_PORT_BACKGROUND" ] && export CODX_JUNIOR_API_PORT_BACKGROUND=19984
# llmfactory server port
[ -z "$CODX_JUNIOR_LLMFACTORY_PORT" ] && export CODX_JUNIOR_LLMFACTORY_PORT=19985
[ -z "$CODX_JUNIOR_LLMFACTORY_URL" ] && export CODX_JUNIOR_LLMFACTORY_URL=http://0.0.0.0:${CODX_JUNIOR_LLMFACTORY_PORT}
# codx-junior preview display
[ -z "$CODX_JUNIOR_DISPLAY" ] && export CODX_JUNIOR_DISPLAY=:55
# Serving client from API
[ -z "$CODX_SUPERVISOR_LOG_FOLDER" ] && export CODX_SUPERVISOR_LOG_FOLDER=/var/log/codx-junior-supervisor

### OLLAMA
[ -z "$CODX_JUNIOR_EMBEDDINGS_MODEL" ] && export CODX_JUNIOR_EMBEDDINGS_MODEL=nomic-embed-text

# Miscellaneous
export DEBIAN_FRONTEND=noninteractive
# Locales
export LANG=en_US.UTF-8  
export LANGUAGE=en_US:en  
export LC_ALL=en_US.UTF-8
                      ```
                      
                      User commented in line 8: change the inline variable check by the if then form
                      
## [[{"doc_id": "bd48fc6f-93d9-4133-bff1-57d71448032b", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-06 10:17:15.934335", "updated_at": "2025-04-06 10:17:15.934379", "images": [], "files": [], "meta_data": {}, "profiles": []}]]

              Rewrite full file content replacing codx instructions with the minimum changes as possible.
              Return only the file content without any further decoration or comments.
              Do not surround response with '```' marks, just content:
              # API virtual env
export CODX_JUNIOR_API_VENV=/tmp/.venv_codx_junior_api
# Browser virtual env
export BROWSER_VENV=/tmp/.venv_codx_junior_browser
# codx-junior API port
if [ -z "$CODX_JUNIOR_API_PORT" ];then 
  export CODX_JUNIOR_API_PORT=19980
fi
@codx-ok, please-wait...: change the inline variable check by the if then form
[ -z "$CODX_JUNIOR_API_URL" ] && export CODX_JUNIOR_API_URL=http://0.0.0.0:${CODX_JUNIOR_API_PORT}
# codx-junior web port
[ -z "$CODX_JUNIOR_WEB_PORT" ] && export CODX_JUNIOR_WEB_PORT=19981
# codx-junior code-server port
[ -z "$CODX_JUNIOR_CODER_PORT" ] && export CODX_JUNIOR_CODER_PORT=19982
# Desktop port
[ -z "$CODX_JUNIOR_NOVNC_PORT" ] && export CODX_JUNIOR_NOVNC_PORT=19983
# codx-junior API background port
[ -z "$CODX_JUNIOR_API_PORT_BACKGROUND" ] && export CODX_JUNIOR_API_PORT_BACKGROUND=19984
# llmfactory server port
[ -z "$CODX_JUNIOR_LLMFACTORY_PORT" ] && export CODX_JUNIOR_LLMFACTORY_PORT=19985
[ -z "$CODX_JUNIOR_LLMFACTORY_URL" ] && export CODX_JUNIOR_LLMFACTORY_URL=http://0.0.0.0:${CODX_JUNIOR_LLMFACTORY_PORT}
# codx-junior preview display
[ -z "$CODX_JUNIOR_DISPLAY" ] && export CODX_JUNIOR_DISPLAY=:55
# Serving client from API
[ -z "$CODX_SUPERVISOR_LOG_FOLDER" ] && export CODX_SUPERVISOR_LOG_FOLDER=/var/log/codx-junior-supervisor

### OLLAMA
[ -z "$CODX_JUNIOR_EMBEDDINGS_MODEL" ] && export CODX_JUNIOR_EMBEDDINGS_MODEL=nomic-embed-text

# Miscellaneous
export DEBIAN_FRONTEND=noninteractive
# Locales
export LANG=en_US.UTF-8  
export LANGUAGE=en_US:en  
export LC_ALL=en_US.UTF-8
              
## [[{"doc_id": "e2473997-5b2c-4b46-bf73-e56beec87731", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-04-06 10:17:15.934335", "updated_at": "2025-04-06 10:17:15.934379", "images": [], "files": [], "meta_data": {"time_taken": 4.4069342613220215, "first_chunk_time_taken": 2.6388163566589355, "model": "gpt-4o"}, "profiles": []}]]
# API virtual env
export CODX_JUNIOR_API_VENV=/tmp/.venv_codx_junior_api
# Browser virtual env
export BROWSER_VENV=/tmp/.venv_codx_junior_browser
# codx-junior API port
if [ -z "$CODX_JUNIOR_API_PORT" ];then 
  export CODX_JUNIOR_API_PORT=19980
fi
# codx-junior API URL
if [ -z "$CODX_JUNIOR_API_URL" ]; then
  export CODX_JUNIOR_API_URL=http://0.0.0.0:${CODX_JUNIOR_API_PORT}
fi
# codx-junior web port
if [ -z "$CODX_JUNIOR_WEB_PORT" ]; then
  export CODX_JUNIOR_WEB_PORT=19981
fi
# codx-junior code-server port
if [ -z "$CODX_JUNIOR_CODER_PORT" ]; then
  export CODX_JUNIOR_CODER_PORT=19982
fi
# Desktop port
if [ -z "$CODX_JUNIOR_NOVNC_PORT" ]; then
  export CODX_JUNIOR_NOVNC_PORT=19983
fi
# codx-junior API background port
if [ -z "$CODX_JUNIOR_API_PORT_BACKGROUND" ]; then
  export CODX_JUNIOR_API_PORT_BACKGROUND=19984
fi
# llmfactory server port
if [ -z "$CODX_JUNIOR_LLMFACTORY_PORT" ]; then
  export CODX_JUNIOR_LLMFACTORY_PORT=19985
fi
if [ -z "$CODX_JUNIOR_LLMFACTORY_URL" ]; then
  export CODX_JUNIOR_LLMFACTORY_URL=http://0.0.0.0:${CODX_JUNIOR_LLMFACTORY_PORT}
fi
# codx-junior preview display
if [ -z "$CODX_JUNIOR_DISPLAY" ]; then
  export CODX_JUNIOR_DISPLAY=:55
fi
# Serving client from API
if [ -z "$CODX_SUPERVISOR_LOG_FOLDER" ]; then
  export CODX_SUPERVISOR_LOG_FOLDER=/var/log/codx-junior-supervisor
fi

### OLLAMA
if [ -z "$CODX_JUNIOR_EMBEDDINGS_MODEL" ]; then
  export CODX_JUNIOR_EMBEDDINGS_MODEL=nomic-embed-text
fi

# Miscellaneous
export DEBIAN_FRONTEND=noninteractive
# Locales
export LANG=en_US.UTF-8  
export LANGUAGE=en_US:en  
export LC_ALL=en_US.UTF-8