# Introduction
This API is the interface for Codx Junior, a tool that can be used for various tasks like code improvement, project management, file operations, and more. The documentation of this application will cover every aspect of its functionalities.



## Creating Projects
To create a new project, follow these steps:
*   Send a POST request to `/api/projects`
*   Include the `project_path` in the request body
*   This API uses Codx Junior's built-in project file to initialize the project



## Running Improvements on Existing Code
The following steps are involved in running improvements on existing code:
*   First, send a POST request to `/api/run/improve`
*   Include the `chat` from the API response body with any changes to be made
*   This will provide you with the improved chat content after processing the improvement



## Saving Chat Content as a New Chat
After modifications are completed the following is done:
*   Send a POST request to `/api/run/improve`
*   Include the `chat` in the API response body
*   After modification is done this saves the chats file using a hash.



## API Usage
### Getting Global Settings
To check the current global settings, send a GET request to `/api/global/settings`



### Writing Custom Global Settings
To set new global settings for the application follow these steps:
*   Send a POST request to `/api/global/settings`
*   Include the custom global settings in the request body
*   This will save and update all custom global configurations based on user input.



## Image Operations
The following APIs provide image operations:

### Uploading Images
To upload an image, send a POST request to `/api/images`

### Sending A Picture Across Channels
You can share images from your chat by sending it via the endpoint `sio.socket.emit("message", message)`

## Dependencies
**Imports from:** codx/junior/ai/__init__.py, codx/junior/sio/sio.py, codx/junior/sio/session_channel.py, codx/junior/profiling/profiler.py, codx/junior/api/chatGPTLikeApi.py, codx/junior/api/users.py, codx/junior/api/wiki.py, codx/junior/api/github.py, codx/junior/api/file_finder.py, codx/junior/api/db_router.py, codx/junior/api/global_settings.py, codx/junior/api/project_search.py, codx/junior/api/knowledge.py, codx/junior/api/chat.py, codx/junior/api/views.py, codx/junior/api/analytics.py, codx/junior/api/logs.py, codx/junior/api/projects.py, codx/junior/security/user_management.py, codx/junior/chat/chat_export.py, codx/junior/globals.py, codx/junior/db.py, codx/junior/model/model.py, codx/junior/settings.py, codx/junior/global_settings.py, codx/junior/engine.py, codx/junior/project/project_discover.py, codx/junior/project/project_manager.py, codx/junior/utils/utils.py, codx/junior/background.py, codx/junior/tools/__init__.py
**Imported by:** codx/junior/main.py