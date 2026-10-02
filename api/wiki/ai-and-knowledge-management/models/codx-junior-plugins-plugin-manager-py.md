## PluginManager

The `PluginManager` class is responsible for managing plugins within the CODX Junior project. It allows for adding, removing, listing, and executing plugins.

### Initialization

The `PluginManager` can be initialized with optional `project_settings` and `user` objects. It loads global settings, including environment variables and existing plugins.

```python
def __init__(self, project_settings: CODXJuniorSettings = None, user: CodxUser = None):
```

### Saving Plugins

The `save_plugins_to_settings` method persists the current list of plugins to the global settings.

```python
def save_plugins_to_settings(self):
    """Save plugins to global settings."""
```

### Managing Plugins

*   **`add_plugin(self, plugin: Plugin)`**: Adds a new plugin or updates an existing one based on its `plugin_id`.
*   **`remove_plugin(self, plugin_id: str)`**: Removes a plugin from the manager using its `plugin_id`.
*   **`list_plugins(self) -> List[Plugin]`**: Returns a list of all currently managed plugins.

```python
def add_plugin(self, plugin: Plugin):
    """Add a new plugin or update an existing plugin by plugin_id."""

def remove_plugin(self, plugin_id: str):
    """Remove a plugin by plugin_id."""

def list_plugins(self) -> List[Plugin]:
    """List all plugins."""
```

### Loading Plugins from File

The `load_from_file` method allows loading plugin configurations from a `plugin.json` file located at a specified path.

```python
def load_from_file(self, file_path: str):
    """Load a plugin from a file path with a plugin.json file."""
```

### Executing Plugins

The `exec_plugin` method executes a specified plugin asynchronously. It uses Jinja2 templating to process plugin arguments based on the provided `context`, which includes user information and environment variables.

```python
async def exec_plugin(self, plugin_id: str, context: dict = {}):
    """
    Execute a plugin method asynchronously using context to process arguments.
    
    :param plugin: Plugin instance to execute.
    :param context: Context dictionary for jinja2 processing of arguments.
    :return: Return value from the plugin method.
    """
```

This method dynamically imports the plugin's module and calls the specified method, handling both synchronous and asynchronous plugin execution.