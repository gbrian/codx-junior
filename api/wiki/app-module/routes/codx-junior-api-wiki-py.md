# Wiki API Documentation

This document provides a detailed guide on how to use the Wiki API endpoints within the `codx-api` project. The API is designed to manage and interact with wiki pages, build wiki configurations, rebuild wikis, and save/load wiki settings.

## Table of Contents
1. [Introduction](#introduction)
2. [Endpoints](#endpoints)
3. [Examples](#examples)
4. [Tips](#tips)

## Introduction
The Wiki API is part of the `codx-api` project and is responsible for handling various operations related to wiki pages. It includes endpoints for retrieving wiki pages, building and rebuilding wikis, and managing wiki settings.

## Endpoints

### 1. `/wiki/{project_name}/{wiki_path:path}`
**Description**: This endpoint retrieves a specific wiki page based on the project name and the path to the wiki file.
- **Parameters**:
  - `project_name`: The name of the project containing the wiki.
  - `wiki_path`: The path to the wiki file. If not provided, it defaults to `index.html`.
- **Response**:
  - Returns the content of the specified wiki file if it exists.
  - Returns a 404 Not Found status code if the file does not exist or the project has no wiki.

```python
@router.get("/wiki/{project_name}/{wiki_path:path}")
async def wiki_page(request: Request, project_name: str, wiki_path: str, response: Response):
    project = find_project_by_name(project_name)
    if not project or not project.project_wiki:
        raise Exception("Project has no wiki")

    if not wiki_path:
        wiki_path = "index.html"
    dist_path = CODXJuniorSession(settings=project).get_wiki().dist_dir
    
    file_path = f"{dist_path}/{wiki_path}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    response.status_code = status.HTTP_404_NOT_FOUND
```

### 2. `/wiki-engine/build`
**Description**: This endpoint builds different parts of the wiki based on the step parameter.
- **Parameters**:
  - `step`: Specifies the step in the build process. Valid values are:
    - `create_config`: Creates the initial configuration for the wiki.
    - `create_wiki_tree`: Creates the wiki tree structure.
    - `build_config_sidebar`: Builds the sidebar configuration.
    - `build_home`: Builds the home page.
    - `compile_wiki`: Compiles the entire wiki.
    - `create_wiki_document`: Creates a new wiki document at the specified file path.
- **Response**:
  - Returns the result of the specified build step.

```python
@router.get("/wiki-engine/build")
async def wiki_engine_build(request: Request):
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    step = request.query_params.get("step")
    file_path = request.query_params.get("file_path")
    if step == "create_config":
        return wiki_manager.create_config()
    if step == "create_wiki_tree":
        return wiki_manager.create_wiki_tree()
    if step == "build_config_sidebar":
        return wiki_manager.build_config_sidebar()
    if step == "build_home":
        return wiki_manager.build_home()
    if step == "compile_wiki":
        return wiki_manager.compile_wiki()
    if step == "create_wiki_document":
        return wiki_manager.create_wiki_document(file_path)
    return wiki_manager.build_wiki()
```

### 3. `/wiki-engine/rebuild`
**Description**: This endpoint rebuilds the entire wiki.
- **Response**:
  - Returns the result of the rebuild operation.

```python
@router.get("/wiki-engine/rebuild")
async def wiki_engine_rebuild(request: Request):
    codx_junior_session = request.state.codx_junior_session
    return codx_junior_session.get_wiki().rebuild_wiki()
```

### 4. `/wiki-engine/config`
**Description**: This endpoint loads the current wiki settings.
- **Response**:
  - Returns the loaded wiki settings.

```python
@router.get("/wiki-engine/config")
async def wiki_engine_config(request: Request):
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    return wiki_manager.load_wiki_settings()
```

### 5. `/wiki-engine`
**Description**: This endpoint saves the wiki settings.
- **Request Body**:
  - A JSON object containing the wiki settings to be saved.
- **Response**:
  - No content returned (HTTP 204 No Content).

```python
@router.put('/wiki-engine')
async def save_wiki_settings(request: Request):
    codx_junior_session = request.state.codx_junior_session
    wiki_manager = codx_junior_session.get_wiki()
    wiki_settings = await request.json()
    wiki_manager.save_wiki_settings(wiki_settings)
```

### 6. `codx-junior-wiki-rebuild`
**Description**: This WebSocket event handler rebuilds the wiki when triggered.
- **WebSocket Event**:
  - `codx-junior-wiki-rebuild`: Triggered by the client to initiate a wiki rebuild.
- **Response**:
  - Returns the result of the rebuild operation.

```python
@sio.on("codx-junior-wiki-rebuild")
@sio_api_endpoint
async def io_wiki_rebuild(sid, data: dict, codxjunior_session: CODXJuniorSession):
    return codxjunior_session.get_wiki().rebuild_wiki()
```

## Examples

### Example 1: Retrieving a Wiki Page
To retrieve a specific wiki page, you can make a GET request to the `/wiki/{project_name}/{wiki_path:path}` endpoint.

```bash
curl -X GET "http://localhost:8000/wiki/my-project/my-page.html"
```

### Example 2: Building a Wiki Configuration
To build the initial configuration for a wiki, you can make a GET request to the `/wiki-engine/build` endpoint with the `step` parameter set to `create_config`.

```bash
curl -X GET "http://localhost:8000/wiki-engine/build?step=create_config"
```

### Example 3: Rebuilding a Wiki
To rebuild the entire wiki, you can make a GET request to the `/wiki-engine/rebuild` endpoint.

```bash
curl -X GET "http://localhost:8000/wiki-engine/rebuild"
```

### Example 4: Loading Wiki Settings
To load the current wiki settings, you can make a GET request to the `/wiki-engine/config` endpoint.

```bash
curl -X GET "http://localhost:8000/wiki-engine/config"
```

### Example 5: Saving Wiki Settings
To save new wiki settings, you can make a PUT request to the `/wiki-engine` endpoint with the settings in the request body.

```bash
curl -X PUT "http://localhost:8000/wiki-engine" -H "Content-Type: application/json" -d '{"title": "My Wiki", "description": "A sample wiki"}'
```

### Example 6: WebSocket Event for Rebuilding a Wiki
To trigger a wiki rebuild via WebSocket, you can send an event named `codx-junior-wiki-rebuild`.

```javascript
const socket = io('http://localhost:8000');
socket.emit('codx-junior-wiki-rebuild', { /* data */ });
```

## Tips

1. **Error Handling**: Ensure that your requests handle errors gracefully, especially when dealing with non-existent files or projects without wikis.
2. **Security**: Use the `UserSecurityManager` and `get_authenticated_user` functions to secure your endpoints and ensure that only authenticated users can access them.
3. **Performance**: For large wikis, consider optimizing the build and rebuild processes to reduce latency and improve user experience.
4. **Testing**: Write unit tests for each endpoint to ensure they behave as expected under various conditions.
5. **Documentation**: Keep your documentation up-to-date with any changes in the API endpoints or their functionality.

By following these guidelines and examples, you should be able to effectively use the Wiki API within the `codx-api` project.