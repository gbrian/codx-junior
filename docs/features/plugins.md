# Plugins

Plugins extend codx-junior with your own Python code.

## Managing plugins

Admins manage plugins in **Global settings → Plugins**: load a plugin from a file, edit its definition, run it, or remove it.

A plugin definition includes:

| Field | Description |
| --- | --- |
| `name`, `description`, `image` | How the plugin appears in the UI. |
| `module_path`, `plugin_path`, `method` | The Python entry point to run. |
| `arguments` | Named arguments with descriptions and default values. |
| `roles` | Who can run it. |
| `extends` | The parts of the UI it extends. |
| `async` | Whether it runs asynchronously. |

## Included examples

The `plugins/` folder of the repository contains:

* **azuredevops**: list and review Azure DevOps pull requests.
* **image_editor**: an image editing service.
* **guide-model**: a lightweight service that answers questions about a project from a guide document using small models.
* **claude**: a Docker setup to run an external coding agent container next to codx-junior.
