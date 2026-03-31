from pydantic import BaseModel, Field
from typing import List, Optional
import yaml
import os
import json
import jinja2 

from codx.junior.settings import (
  CODXJuniorSettings,
)

from codx.junior.global_settings import (
  read_global_settings, 
  write_global_settings
)

from codx.junior.model.model import (
    CodxUser,
    Plugin,
    PluginArgument
)

# Define the PluginManager class
class PluginManager:
    def __init__(self, project_settings: CODXJuniorSettings = None, user: CodxUser = None):
        global_settings = read_global_settings()
        self.plugins = global_settings.plugins
        self.env = {
          **global_settings.env,
          **(user.env if user else {})
        }
        self.project_settings = project_settings
        self.user = user

    def save_plugins_to_settings(self):
        """Save plugins to global settings."""
        settings = read_global_settings()
        settings.plugins = [plugin.dict(by_alias=True) for plugin in self.plugins]
        write_global_settings(settings)

    def add_plugin(self, plugin: Plugin):
        """Add a new plugin or update an existing plugin by plugin_id."""
        existing_plugin = next((p for p in self.plugins if p.plugin_id == plugin.plugin_id), None)
        if existing_plugin:
            # Update existing plugin
            existing_plugin.name = plugin.name
            existing_plugin.description = plugin.description
            existing_plugin.module_path = plugin.module_path
            existing_plugin.plugin_path = plugin.plugin_path
            existing_plugin.method = plugin.method
            existing_plugin.arguments = plugin.arguments
            existing_plugin.roles = plugin.roles
            existing_plugin.extends = plugin.extends
            existing_plugin.image = plugin.image
            existing_plugin.async_ = plugin.async_
        else:
            # Add new plugin
            self.plugins.append(plugin)
        self.save_plugins_to_settings()

    def remove_plugin(self, plugin_id: str):
        """Remove a plugin by plugin_id."""
        self.plugins = [plugin for plugin in self.plugins if plugin.plugin_id != plugin_id]
        self.save_plugins_to_settings()

    def list_plugins(self) -> List[Plugin]:
        """List all plugins."""
        return self.plugins

    def load_from_file(self, file_path: str):
        """Load a plugin from a file path with a plugin.json file."""
        if not os.path.exists(file_path):
            print(f"Plugin configuration file not found at {file_path}")
            return

        with open(file_path, 'r') as file:
            plugin_data = json.load(file)
            plugin_data['plugin_path'] = os.path.dirname(file_path)  # Set the plugin_path to the file's directory
            self.add_plugin(Plugin(**plugin_data))

    async def exec_plugin(self, plugin_id: str, context: dict = {}):
        """
        Execute a plugin method asynchronously using context to process arguments.
        
        :param plugin: Plugin instance to execute.
        :param context: Context dictionary for jinja2 processing of arguments.
        :return: Return value from the plugin method.
        """
        plugin = next((p for p in self.plugins if p.plugin_id == plugin_id), None)
        
        # Create a Jinja2 environment
        env = jinja2.Environment(loader=jinja2.BaseLoader())

        context["user"] = self.user or CodxUser()
        context["project_settings"] = self.settings
        context["get_env"] = lambda env_name: self.env.get(env_name)
        # Process arguments using jinja2 templates
        processed_args = {}
        for arg in plugin.arguments:
            template = env.from_string(arg.default_value)
            processed_args[arg.name] = template.render(context)

        # Dynamically import the module and method
        module = __import__(plugin.module_path, fromlist=[plugin.method])
        method = getattr(module, plugin.method)

        # Call the method with the processed arguments
        return await method(**processed_args) if plugin.async_ else method(**processed_args)