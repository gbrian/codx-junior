# Profile Manager

The `ProfileManager` class is responsible for managing user profiles within the CODX Junior system. It handles profile discovery, loading, saving, and linking across projects.

## Overview

The `ProfileManager` provides functionality to:
- Discover and load profiles from multiple sources (current project, parent projects, and built-in profiles)
- Save and delete profiles with support for both flat and folder-based structures
- Match profiles to files based on regex patterns
- Link profiles together and resolve profile dependencies
- Parse profile content with template variable substitution

## Core Components

### Initialization

```python
def __init__(self, settings: CODXJuniorSettings)
```

Creates a new `ProfileManager` instance with the following setup:
- Initializes the profiles path from settings (`{codx_path}/profiles`)
- Creates the profiles directory if it doesn't exist
- Sets the base profiles path to the module's directory for built-in profiles

### Profile Discovery

#### `list_all_profiles()`

Retrieves all available profiles from three sources in priority order:
1. Parent project and codx-junior profiles (lowest priority)
2. Current project profiles (can override parent profiles)
3. Built-in base profiles from source code (highest priority - only if not already defined)

Returns a list of profiles enriched with parsed content.

#### `list_profiles()`

Returns only the profiles from the current project directory.

#### `project_profile_paths()`

Discovers profile file paths supporting both:
- **New format**: `[profile_name]/[profile_name].profile` (folder-based)
- **Old format**: `*.profile` (flat structure - for backward compatibility)

#### `base_profiles()`

Returns paths to built-in profile files included with the source code.

### Profile Operations

#### `load_profile(profile_path)`

Loads a profile from a JSON file with the following behavior:
- Reads the `.profile` JSON file
- Attempts to parse JSON content; falls back to default values if parsing fails
- Loads optional markdown content from `[profile_name].md` in the same directory
- Sets a default Gravatar avatar if none is provided
- Assigns the current project ID to the profile

Returns a `Profile` object or a minimal valid profile if an error occurs.

#### `read_profile(profile_name)`

Retrieves a specific profile by name from the current project.

#### `save_profile(profile)`

Saves a profile to the new folder-based structure:
- Creates a folder named after the profile
- Saves profile JSON to `[profile_name]/[profile_name].profile`
- Saves profile content to `[profile_name]/[profile_name].md` if content exists
- Automatically migrates old flat-format profiles to the new structure

#### `delete_profile(profile_name)`

Deletes a profile and its associated content:
- Removes the profile folder (new format)
- Handles old flat-format files (backward compatibility)
- Cleans up related markdown files

### Profile Matching and Filtering

#### `is_profile_match(profile, file_path)`

Determines if a file matches a profile's file matching pattern using regex.

#### `get_file_profiles_by_file_path(file_path)`

Returns all profiles applicable to a given file path, with linked profiles resolved and deduplicated.

#### `get_profiles_by_name(profiles)`

Retrieves specific profiles by their names from all available profiles.

### Profile Linking

#### `get_all_linked_profiles(profile, seen)`

Recursively retrieves a profile and all profiles linked to it through the `profiles` property. Maintains a `seen` list to prevent infinite recursion.

#### `reduce_linked_profiles(profiles)`

Deduplicates a list of profiles while preserving order. Resolves all linked profiles for each input profile and returns a single deduplicated list.

### Content Parsing

#### `get_profile_content_context(profile)`

Provides a context dictionary for template variable substitution with available functions:
- `project_path`: Returns the absolute project path
- `project_name`: Returns the project name

#### `get_profile_With_content(profile)`

Parses profile content by substituting template variables using the pattern `{{ variable_name }}`. Variables are resolved from the context, with original text preserved if a variable is not found.

## Profile File Structure

### New Format (Folder-Based)

```
profiles/
└── profile_name/
    ├── profile_name.profile    (JSON metadata)
    └── profile_name.md         (Markdown content)
```

### Old Format (Flat - Deprecated)

```
profiles/
├── profile_name.profile
└── profile_name.md.profile
```

## Utility Functions

### `generate_llm_tree(root_path, indent, is_last, ignore_list)`

Generates a tree representation of a directory structure for LLM consumption. Filters out common directories (`.git`, `__pycache__`, `.vscode`, `node_modules`, `venv`, `.DS_Store`). Currently excludes files from the output.

## Migration Strategy

The `ProfileManager` supports automatic migration from the old flat profile structure to the new folder-based structure through the `_migrate_profile_to_folder()` method. Migration occurs automatically when saving profiles that exist in the old format.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py, codx/junior/utils/utils.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/api/chatGPTLikeApi.py, codx/junior/chat/chat_engine.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/wiki/wiki_manager.py