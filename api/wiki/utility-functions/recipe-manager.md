# Recipe Manager Documentation

## Overview

The Recipe Manager is a utility module for managing reusable, ordered sets of steps to accomplish specific goals. It supports various use cases including tutorials, automations, workflows, playbooks, and custom implementations.

## Core Concept

Recipes operate on a two-phase lifecycle:

1. **Template Phase**: An immutable template is created by an author (is_template=True)
2. **Instance Phase**: Users instantiate templates into mutable instances (is_template=False) that track progress

Each template can be instantiated multiple times, with each instance maintaining independent progress metrics and step chats.

## Recipe Types

Recipes can be categorized by type:
- **Tutorial**: Educational content ("Learn FastAPI")
- **Automation**: Auto-executed background processes ("Keep project docs in sync")
- **Workflow**: Structured checklists ("Code review checklist")
- **Playbook**: Troubleshooting guides ("Debug high memory usage")
- **Custom**: User-defined types

## Template Management

### Creating Templates

Templates are created as immutable blueprints that define the structure and steps:

```python
recipe = recipe_manager.create_template(
    name="API Integration Guide",
    recipe_type="tutorial",
    description="Learn to integrate with REST APIs",
    goal="Successfully create and test API endpoints",
    tags=["api", "integration"],
    owner="author_id"
)
```

**Parameters:**
- `name` (str): Recipe name
- `recipe_type` (str): Type classification
- `description` (str): What the recipe accomplishes
- `goal` (str, optional): High-level success target
- `tags` (List[str], optional): Categorization tags
- `owner` (str, optional): Creator identifier

### Adding Steps to Templates

Steps are ordered instructions added sequentially to templates:

```python
recipe_manager.add_step_to_template(
    recipe_id="template_id",
    name="Setup Environment",
    description="Install required dependencies",
    step_type="action",
    is_required=True,
    success_criteria="All packages installed without errors",
    estimated_duration_seconds=300
)
```

**Step Parameters:**
- `name` (str): Step identifier
- `description` (str): Detailed purpose and instructions
- `step_type` (str): One of 'instruction', 'exercise', 'validation', 'action'
- `is_required` (bool): Must complete to proceed
- `success_criteria` (str, optional): Defines completion condition
- `estimated_duration_seconds` (int, optional): Expected time
- `meta_data` (Dict, optional): Custom configuration

### Listing Templates

Filter and discover available templates:

```python
templates = recipe_manager.list_templates(
    recipe_type="tutorial",
    tags=["api", "integration"]
)
```

**Filters:**
- `recipe_type` (str, optional): Filter by type
- `tags` (List[str], optional): Must have ALL specified tags

## Instance Management

### Creating Instances

Instantiate a template to create a live, executable recipe:

```python
instance = recipe_manager.create_instance(
    template_id="template_id",
    user_id="user_id",
    project_id="project_id"
)
```

**Actions during instantiation:**
- Deep-copies all template data
- Creates a dedicated Chat for each step
- Initializes progress metrics
- Sets is_template=False and template_id reference

**Parameters:**
- `template_id` (str): Source template ID
- `user_id` (str, optional): Instance owner
- `project_id` (str, optional): Associated project

### Listing Instances

Retrieve active instances with optional filtering:

```python
instances = recipe_manager.list_instances(
    user_id="user_id",
    template_id="template_id",
    recipe_type="workflow"
)
```

**Available Filters:**
- `user_id` (str, optional): Filter by owner
- `template_id` (str, optional): Filter by source template
- `recipe_type` (str, optional): Filter by type

## Step Execution & Progress Tracking

### Step Status Lifecycle

Steps transition through completion states:

- **COMPLETION_NOT_STARTED** (None): Initial state
- **COMPLETION_IN_PROGRESS**: Step actively being worked on
- **COMPLETION_DONE**: Successfully completed
- **COMPLETION_SKIPPED**: Intentionally skipped (optional steps only)
- **COMPLETION_FAILED**: Step did not complete successfully

### Updating Step Status

#### Start a Step
```python
recipe_manager.start_step(recipe_id="instance_id", step_index=0)
```

#### Complete a Step
```python
recipe_manager.complete_step(
    recipe_id="instance_id",
    step_index=0,
    notes="Setup completed successfully"
)
```

#### Skip a Step
```python
recipe_manager.skip_step(
    recipe_id="instance_id",
    step_index=1,
    reason="Environment already configured"
)
```
*Note: Only optional steps (is_required=False) can be skipped*

#### Mark Step as Failed
```python
recipe_manager.fail_step(
    recipe_id="instance_id",
    step_index=0,
    error="Dependency installation failed"
)
```

### Progress Tracking

Get comprehensive progress information:

```python
progress = recipe_manager.get_progress(recipe_id="instance_id")
```

**Returns:**
- Overall completion percentage
- Counts: completed, skipped, failed steps
- Step-by-step details including status and message count
- Last completed step index
- Updated timestamp

## Metrics

Recipe instances track the following metrics:

| Metric | Description |
|--------|-------------|
| `total_steps` | Total number of steps |
| `completed_steps` | Number of successfully completed steps |
| `skipped_steps` | Number of skipped steps |
| `failed_steps` | Number of failed steps |
| `completion_percent` | Overall completion percentage (0-100) |
| `last_completed_step_index` | Index of most recently completed step |

Metrics are automatically updated whenever step status changes via `_update_metrics()`.

## Data Persistence

### Storage Architecture

Recipes utilize a kanban board structure for organization:

| Component | Board | Column |
|-----------|-------|--------|
| Templates | "recipes" | "templates" |
| Active Instances | "recipes" | "active" |
| Archived Instances | "recipes" | "archived" |

### Chat Integration

Each step in an instance maintains an associated Chat object:
- Stores step-specific messages and context
- Tracks step status independently
- Maintains message history for auditing
- Linked via `chat_id` on RecipeStep

## Implementation Notes

### TODO Items

The current implementation includes placeholder methods for data persistence:

- `_load_all_recipes()`: Requires implementation of recipe-specific storage queries
- `_persist_recipe()`: Requires implementation of recipe storage mechanism

Production implementation should replace these with database queries (MongoDB, PostgreSQL, etc.).

### Error Handling

- Invalid template/recipe IDs raise `ValueError`
- Attempting to skip required steps raises `ValueError`
- Operations validate recipe existence before execution

## Storage Relationships

```
Recipe (template=True)
├── RecipeStep[]
│   └── meta_data (custom config)
└── tags[]

Recipe (template=False, instance)
├── RecipeStep[]
│   └── Chat (step-specific conversation)
│       └── Message[]
├── RecipeMetrics
└── template_id (reference to source template)
```