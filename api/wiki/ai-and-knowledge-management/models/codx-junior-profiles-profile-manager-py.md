# Profile Manager Documentation

## Overview

The Profile Manager is a comprehensive system for managing user profiles within the CODX Junior framework. It handles profile discovery, loading, saving, and linking across multiple project hierarchies.

## Core Components

### ProfileManager Class

The main class responsible for all profile management operations.

#### Initialization

```python
def __init__(self, settings: CODXJuniorSettings)
```

Initializes the ProfileManager with project settings and establishes two key paths:
- `profiles_path`: User-defined profiles directory within the CODX project
- `base_profiles_path`: Built-in base profiles directory from source code

#### Profile Discovery Methods

**base_profiles()**
Returns a list of all built-in base profile paths from the source code directory.

**project_profile_paths()**
Returns a list of all profile paths in the current project's profiles directory.

**list_profiles()**
Loads and returns all valid profiles for the current project, filtering out any profiles that fail to load.

**list_all_profiles()**
Provides a comprehensive profile listing that includes:
1. Profiles from parent projects
2. Profiles from the codx-junior project
3. Current project profiles (which can override parent profiles)
4. Built-in base profiles (only if not already defined)

Returns profiles with full content parsed and ready for use.

### Profile Loading and Storage

**load_profile(profile_path: str) -> Profile**
Loads a profile from a file path with comprehensive error handling:
- Validates JSON content
- Sets default avatar using Gravatar if not specified
- Handles legacy profile content stored in separate `.md` files
- Returns a minimal valid profile on error rather than raising exceptions

**save_profile(profile: Profile)**
Persists a profile to disk as JSON format. Clears parsed content before saving to ensure consistency.

**read_profile(profile_name: str) -> Profile**
Retrieves a single profile by name from the current project's profiles.

**delete_profile(profile_name: str)**
Removes a profile file from the project.

### Profile Matching and Filtering

**is_profile_match(profile: Profile, file_path: str) -> bool**
Determines if a profile's file match pattern applies to a given file path using regex matching.

**get_file_profiles_by_file_path(file_path: str)**
Returns all profiles that match a specific file path pattern.

**get_profiles_by_name(profiles: list)**
Filters and returns profiles from all available profiles by name.

### Content Processing

**get_profile_With_content(profile: Profile)**
Processes profile content by replacing template variables in the format `{{ variable_name }}` with actual values. Supports:
- `{{ project_path }}`: Absolute project path
- `{{ project_name }}`: Project name
- Additional variables can be extended via `get_profile_content_context()`

**get_profile_content_context(profile: Profile)**
Provides a dictionary of available context variables for content template processing.

### Profile Linking

**get_all_linked_profiles(profile: Profile, seen: set = None) -> List[Profile]**
Recursively retrieves all profiles linked to a given profile, including:
- The profile itself
- Direct neighbor profiles referenced in the profile's `profiles` field
- Nested linked profiles

Prevents infinite recursion by tracking previously seen profiles.

**reduce_linked_profiles(profiles: List[Profile]) -> List[Profile]**
Deduplicates a list of profiles while preserving order and maintaining all linked relationships across multiple top-level profiles.

## Utility Functions

**generate_llm_tree(root_path, indent="", is_last=True, ignore_list=None)**
Generates a tree representation of a directory structure suitable for LLM processing. Ignores common directories by default including:
- `.git`, `__pycache__`, `.vscode`, `.DS_Store`, `node_modules`, `venv`

Directories are listed before files and sorted alphabetically within their respective categories.

## Profile Hierarchy

The profile system follows a hierarchical priority:
1. Current project profiles (highest priority)
2. Parent project profiles
3. CODX Junior project profiles
4. Built-in base profiles (lowest priority)

Higher priority profiles override lower priority profiles with the same name.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py, codx/junior/utils/utils.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/api/chatGPTLikeApi.py, codx/junior/chat/chat_engine.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/wiki/wiki_manager.py