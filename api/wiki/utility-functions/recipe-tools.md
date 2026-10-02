# Recipe Tools Documentation

## Overview

The recipe tools module provides utilities for discovering, instantiating, and managing recipes within codx-junior. Recipes encompass tutorials, automations, workflows, and playbooks that guide users through structured tasks.

## Available Functions

### list_recipes

Discover and filter available recipe templates.

**Parameters:**
- `recipe_type` (optional): Filter by recipe type — valid values are `'tutorial'`, `'automation'`, `'workflow'`, or `'playbook'`
- `tags` (optional): Comma-separated tags to narrow down results

**Returns:**
- `ToolResponse` containing a formatted list of matching recipes with names, types, IDs, descriptions, goals, step counts, versions, and tags

**Usage Example:**
```
list_recipes(recipe_type='automation', tags='integration,api')
```

**Notes:**
- Returns a descriptive message when no recipes match the filter criteria
- The response includes metadata for each recipe to help users identify the right template

---

### start_recipe

Create a live recipe instance from a template.

**Parameters:**
- `recipe_id` (required): The template recipe ID to instantiate

**Returns:**
- `ToolResponse` confirming successful instance creation with the new instance ID, recipe type, step count, and a detailed list of all steps with their names, types, and chat IDs

**Usage Example:**
```
start_recipe(recipe_id='tutorial-api-setup')
```

**Notes:**
- Automatically associates the recipe instance with the current user
- Each step is initialized with an empty (⬜) status icon
- Raises an error if the specified template does not exist

---

### get_recipe_progress

Retrieve progress information for an active recipe instance.

**Parameters:**
- `recipe_id` (required): The instance recipe ID to check

**Returns:**
- `ToolResponse` with completion percentage, step counts (completed, total, failed), and a detailed breakdown of each step showing its status icon, name, type, and message count

**Usage Example:**
```
get_recipe_progress(recipe_id='instance-abc123')
```

**Status Icons:**
- `✅` — Completed
- `🔄` — In progress
- `⏭️` — Skipped
- `❌` — Failed
- `⬜` — Not started

---

### complete_recipe_step

Mark a recipe step as completed.

**Parameters:**
- `recipe_id` (required): The instance recipe ID
- `step_index` (required): The zero-based index of the step to mark complete

**Returns:**
- `ToolResponse` confirming the step completion and providing updated overall recipe progress percentage

**Usage Example:**
```
complete_recipe_step(recipe_id='instance-abc123', step_index=0)
```

**Notes:**
- Validates that both the recipe instance and step index exist before updating
- Returns error details if the operation fails
- Updates recipe metrics automatically upon successful completion

---

## Error Handling

All functions perform validation on input parameters and dependencies:
- Missing or invalid project settings raise an exception
- Invalid recipe or step IDs return error responses in both user and LLM formats
- ValueError and IndexError exceptions are caught and communicated clearly to the user