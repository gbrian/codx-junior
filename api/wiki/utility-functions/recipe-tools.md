# Recipe Tools

Provides tools for discovering, instantiating, and managing recipes (tutorials, automations, workflows, playbooks) in codx-junior.

## Overview

The recipe tools module enables users to work with recipe templates and instances. It supports listing available recipes, creating live instances, tracking progress, and marking steps as complete.

## Functions

### list_recipes

List available recipe templates with optional filtering.

**Parameters:**
- `recipe_type` (optional): Filter by type — `'tutorial'`, `'automation'`, `'workflow'`, or `'playbook'`
- `tags` (optional): Comma-separated tags to filter results

**Returns:**
- `ToolResponse` containing formatted recipe list with details for each match

**Details:**
When recipes are found, the response includes the recipe name, type, ID, description, goal (if available), step count, version, and associated tags.

### start_recipe

Create a live recipe instance from a template.

**Parameters:**
- `recipe_id`: The template recipe ID to instantiate

**Returns:**
- `ToolResponse` confirming instance creation with step details

**Details:**
Creates a new instance with a unique ID and displays all steps with their names, types, and chat IDs. Each step starts with an unfilled status icon (⬜).

### get_recipe_progress

Retrieve progress summary for an active recipe instance.

**Parameters:**
- `recipe_id`: The instance recipe ID

**Returns:**
- `ToolResponse` with completion percentage and step-by-step status

**Details:**
Displays overall completion percentage, step counters (completed, total, failed), and individual step status with message counts. Status indicators:
- ✅ Completed
- 🔄 In progress
- ⏭️ Skipped
- ❌ Failed
- ⬜ Not started

### complete_recipe_step

Mark a recipe step as completed.

**Parameters:**
- `recipe_id`: The instance recipe ID
- `step_index`: The step number to complete (0-based indexing)

**Returns:**
- `ToolResponse` confirming step completion with updated progress percentage

**Details:**
Updates the step status and recalculates overall recipe completion percentage if metrics are available.

## Error Handling

All functions handle errors gracefully:
- Missing or invalid settings raise an `Exception`
- Recipe/step not found returns error in both user and LLM responses
- ValueError and IndexError are caught during step completion