# Workspace Model Compatibility Shim

## Overview

This module serves as a compatibility shim, re-exporting workspace-related models that have been moved to `codx.junior.workspaces.model`. It ensures backward compatibility for any code that imports from the original location.

---

## Imported Models

The following models are imported from `codx.junior.workspaces.model` and made available through this module:

| Model | Description |
|---|---|
| `Workspace` | Core workspace data model |
| `WorkspaceApp` | Represents an application within a workspace |
| `WorkspaceResources` | Defines resources associated with a workspace |
| `WorkspaceStatus` | Represents the status of a workspace |

---

## Default Workspace

A pre-configured default workspace instance is exposed as `DEFAULT_WORKSPACE`. It is constructed using the `Workspace` model with the following configuration:

### General Properties

| Property | Value |
|---|---|
| `name` | `codx-junior` |
| `description` | Default codx-junior workspace |
| `folder_path` | `codx-junior-workspace-default` |
| `template` | `custom` |
| `project_ids` | `["*"]` (applies to all projects) |

### Included Applications

The default workspace includes three pre-configured applications:

#### 1. Coder
| Property | Value |
|---|---|
| `icon` | `fa-solid fa-code` |
| `name` | Coder |
| `description` | Coder coding environment |
| `path` | `/workspace-default/coder/` |
| `roles` | `["admin"]` |

#### 2. Desktop
| Property | Value |
|---|---|
| `icon` | `fa-solid fa-desktop` |
| `name` | Desktop |
| `description` | Virtual desktop |
| `path` | `/workspace-default/preview/index.html` |
| `roles` | `["admin"]` |

#### 3. LiteLLM
| Property | Value |
|---|---|
| `icon` | External image URL (Framer) |
| `name` | LiteLLM |
| `description` | LiteLLM Models manager |
| `path` | `/litellm/ui` |
| `roles` | `["admin"]` |

---

## Notes

- All applications within the default workspace are restricted to the `admin` role.
- The `project_ids` value of `["*"]` indicates this workspace applies to all projects.
- The actual model definitions reside in `codx.junior.workspaces.model`; this file only re-exports them for backward compatibility.