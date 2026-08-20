# Profile Manager Documentation

## Overview

The Profile Manager is a component responsible for managing user profiles within the CODX Junior system. It handles loading, saving, listing, and organizing profiles across multiple project hierarchies while supporting profile inheritance and content templating.

## Core Components

### ProfileManager Class

The main class that manages all profile-related operations.

#### Initialization

```python
def __init__(self, settings: CODXJuniorSettings):
```

Initializes the ProfileManager with:
- `settings`: CODX Junior configuration settings
- `profiles_path`: Directory path where project profiles are stored
- `base_profiles_path`: Path to built-in base profiles from source code

The constructor automatically creates the profiles directory if it doesn't exist.

## Profile Discovery and Listing

### list_all_profiles()

Retrieves all available profiles from multiple sources in the following priority order:

1. **Parent Project Profiles**: Profiles from parent projects in the hierarchy
2. **CODX-Junior Project Profiles**: Profiles from the codx-junior project itself
3. **Current Project Profiles**: Can override parent profiles with the same name
4. **Built-in Base Profiles**: Source code profiles used only if not already defined

Returns a list of profiles with parsed content.

### list_profiles()

Returns profiles specific to the current project by loading all `.profile` files from the project's profiles path.

### base_profiles()

Discovers and returns all built-in base profile file paths from the source code directory using glob pattern matching for `**/*.profile` files.

### project_profile_paths()

Returns file paths of all profiles in the current project's profiles directory.

## Profile Operations

### read_profile(profile_name)

Retrieves a single profile by name.

- **Parameters**: `profile_name` - Name of the profile to retrieve
- **Returns**: Profile object or None if not found

### load_profile(profile_path)

Loads a profile from disk with comprehensive error handling.

**Features**:
- Reads profile JSON content from file
- Validates non-empty content
- Handles JSON parsing errors gracefully
- Manages legacy profile content format (`.profile.md` files)
- Sets default avatar using Gravatar if not specified
- Associates profile with current project

**Error Handling**: Returns a minimal valid Profile object with defaults if loading fails.

### save_profile(profile)

Persists a profile to disk.

- **Parameters**: `profile` - Profile object to save
- **Behavior**: 
  - Validates profile has a name
  - Writes profile as JSON with 2-space indentation
  - Clears parsed content before saving

### delete_profile(profile_name)

Removes a profile file from the current project's profiles directory.

- **Parameters**: `profile_name` - Name of the profile to delete

## Profile Filtering and Matching

### is_profile_match(profile, file_path)

Checks if a file path matches a profile's file matching pattern.

- **Parameters**:
  - `profile`: Profile object containing regex pattern
  - `file_path`: File path to test
- **Returns**: Boolean indicating if regex pattern matches
- **Error Handling**: Returns False if regex fails

### get_file_profiles_by_file_path(file_path)

Finds all profiles that match a given file path pattern.

- **Parameters**: `file_path` - Path to match against profile patterns
- **Returns**: Deduplicated list of matching profiles with linked profiles

### get_profiles_by_name(profiles)

Retrieves profiles from all available profiles by name.

- **Parameters**: `profiles` - List of profile names to retrieve
- **Returns**: List of matching Profile objects

## Content Processing

### get_profile_content_context(profile)

Provides template variables for profile content substitution.

**Available Variables**:
- `project_path`: Returns the absolute project path
- `project_name`: Returns the project name

### get_profile_With_content(profile)

Processes profile content by replacing template variables with actual values.

**Template Syntax**: `{{ variable_name }}`

**Features**:
- Uses regex pattern matching for template variables
- Supports optional whitespace around variable names
- Preserves original text if variable not found
- Returns profile with `parsed_content` populated

## Profile Linking

### get_all_linked_profiles(profile, seen=None)

Recursively retrieves all linked profiles including the profile itself and its dependencies.

**Features**:
- Maintains traversal order
- Prevents infinite loops with `seen` tracking
- Uses list-based deduplication for O(1) lookups
- Supports nested profile relationships

### reduce_linked_profiles(profiles)

Deduplicates a list of profiles while respecting linked profile dependencies.

- **Parameters**: `profiles` - List of profiles to deduplicate
- **Returns**: Flattened, deduplicated list of all profiles and their linked dependencies
- **Note**: Each top-level profile starts with fresh dependency resolution

## Utility Functions

### generate_llm_tree(root_path, indent="", is_last=True, ignore_list=None)

Generates a tree representation of directory structure suitable for LLM consumption.

**Features**:
- Excludes common development directories (`.git`, `__pycache__`, `.vscode`, `node_modules`, `venv`, `.DS_Store`)
- Sorts items with directories first, then files alphabetically
- Uses tree-style ASCII connectors
- Returns string representation or "Invalid Path" for non-existent paths

**Note**: File listing is currently disabled (commented out).

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py, codx/junior/utils/utils.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/api/chatGPTLikeApi.py, codx/junior/chat/chat_engine.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/wiki/wiki_manager.py