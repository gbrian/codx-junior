# Recipe Manager Documentation

## Overview

The Recipe Manager is a utility for managing reusable, ordered sets of steps to accomplish goals within the codx-junior system. It supports multiple recipe types including tutorials, automations, workflows, playbooks, and custom use cases.

## Core Concepts

### Recipe Lifecycle

Recipes follow a four-stage lifecycle:

1. **Template Creation**: An author creates an immutable recipe template (`is_template=True`)
2. **Instantiation**: A user or system creates a live instance from the template (deep copy with `is_template=False`)
3. **Execution**: Steps are executed and progressed, with metrics updated at each step
4. **Tracking**: The instance tracks progress and can be resumed or archived

### Recipe Types

- **Tutorial**: Educational content for learning (e.g., "Learn FastAPI")
- **Automation**: Automated tasks with auto-execution enabled (e.g., "Keep project docs in sync")
- **Workflow**: Step-by-step checklists (e.g., "Code review checklist")
- **Playbook**: Diagnostic and troubleshooting guides (e.g., "Debug high memory usage")

## Template Management

### Creating Templates

Templates are immutable recipe blueprints created by authors.

```python
create_template(
    name: str,
    recipe_type: str = "workflow",
    description: str = "",
    goal: Optional[str] = None,
    tags: Optional[List[str]] = None,
    owner: Optional[str] = None
) -> Recipe
```

**Parameters:**
- `name`: Recipe identifier
- `recipe_type`: Classification type ('tutorial', 'automation', 'workflow', etc.)
- `description`: What the recipe accomplishes
- `goal`: High-level success target
- `tags`: Categorization labels
- `owner`: Creator identifier

### Adding Steps to Templates

Extend templates with ordered steps using `add_step_to_template()`:

```python
add_step_to_template(
    recipe_id: str,
    name: str,
    description: str = "",
    step_type: str = "action",
    is_required: bool = True,
    success_criteria: Optional[str] = None,
    estimated_duration_seconds: Optional[int] = None,
    meta_data: Optional[Dict[str, Any]] = None
) -> Recipe
```

**Step Types:**
- `instruction`: Informational guidance
- `exercise`: Practical tasks
- `validation`: Quality checks
- `action`: Executable operations

### Discovering Templates

List available templates with optional filtering:

```python
list_templates(
    recipe_type: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> List[Dict[str, Any]]
```

Retrieve a specific template by ID:

```python
get_template(recipe_id: str) -> Optional[Recipe]
```

## Instance Management

### Creating Instances

Instantiate a live recipe from a template:

```python
create_instance(
    template_id: str,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None
) -> Recipe
```

The system automatically:
- Deep-copies the template
- Creates a dedicated Chat for each RecipeStep
- Initializes progress metrics
- Sets `is_template=False` and `template_id`

### Retrieving Instances

Get a specific instance:

```python
get_instance(recipe_id: str) -> Optional[Recipe]
```

List instances with optional filtering:

```python
list_instances(
    user_id: Optional[str] = None,
    template_id: Optional[str] = None,
    recipe_type: Optional[str] = None
) -> List[Dict[str, Any]]
```

## Step Progress Tracking

### Step Status Constants

- `None` (COMPLETION_NOT_STARTED): Not yet initiated
- `"in_progress"` (COMPLETION_IN_PROGRESS): Currently executing
- `"completed"` (COMPLETION_DONE): Successfully finished
- `"skipped"` (COMPLETION_SKIPPED): Intentionally bypassed
- `"failed"` (COMPLETION_FAILED): Execution error occurred

### Updating Step Status

**Mark step as in-progress:**
```python
start_step(recipe_id: str, step_index: int) -> Recipe
```

**Mark step as completed:**
```python
complete_step(
    recipe_id: str,
    step_index: int,
    notes: Optional[str] = None
) -> Recipe
```

**Skip an optional step:**
```python
skip_step(
    recipe_id: str,
    step_index: int,
    reason: Optional[str] = None
) -> Recipe
```

*Note: Required steps cannot be skipped; raises ValueError if attempted.*

**Mark step as failed:**
```python
fail_step(
    recipe_id: str,
    step_index: int,
    error: Optional[str] = None
) -> Recipe
```

### Progress Monitoring

Get comprehensive progress snapshot:

```python
get_progress(recipe_id: str) -> Dict[str, Any]
```

Returns:
- Recipe metadata (ID, name, type, template source)
- Aggregated metrics (completion percentage, step counts)
- Step-by-step details (status, message count, requirements)

## Metrics System

RecipeMetrics tracks instance progress:

- `total_steps`: Count of all steps
- `completed_steps`: Successfully finished steps
- `skipped_steps`: Intentionally bypassed steps
- `failed_steps`: Steps with errors
- `completion_percent`: Completion percentage (0-100)
- `last_completed_step_index`: Most recent completed step
- `updated_at`: Last metrics refresh timestamp

Metrics are automatically recalculated when step statuses change via `_update_metrics()`.

## Architecture

### Dependencies

- **Settings**: CODXJuniorSettings for configuration
- **Chat Manager**: ChatManager for step-level conversation management
- **Database Models**: Recipe, RecipeStep, RecipeMetrics, Chat, Message

### Kanban Organization

Recipes use a kanban board system for organization:

- **Board**: "recipes"
- **Template Column**: "templates"
- **Active Column**: "active" (running instances)
- **Archived Column**: "archived" (completed/inactive instances)

### Storage Integration

Template and instance recipes persist to database via `_persist_recipe()`. Each step maintains a reference to its associated Chat for conversation history and messaging.