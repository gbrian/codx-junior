# Profile Manager

The ProfileManager class handles the lifecycle of user profiles in the CODX Junior system, including loading, saving, deleting, and organizing profiles with support for both legacy and modern file structures.

## Overview

The ProfileManager is responsible for managing profiles across multiple locations:
- Project-level profiles
- Parent project profiles
- Built-in base profiles from source code

It supports both flat (legacy) and folder-based (modern) profile structures, with automatic migration capabilities.

## Key Components

### Profile Storage Structure

Profiles are stored in two formats:

**Modern Format (Recommended):**
```
profiles/
├── profile_name/
│   ├── profile_name.profile (JSON metadata)
│   └── profile_name.md (markdown content)
```

**Legacy Format (Deprecated):**
```
profiles/
└── profile_name.profile
```

### Class Methods

#### Initialization
`__init__(settings: CODXJuniorSettings)`

Initializes the ProfileManager with:
- Settings from CODXJuniorSettings
- Profile paths configuration
- Base profiles directory resolution

#### Profile Discovery

**`base_profiles()`**
Returns a list of built-in profiles included with the source code. These profiles are found recursively in the base profiles directory.

**`project_profile_paths()`**
Locates all profiles in the current project, supporting both new folder-based and legacy flat formats for backward compatibility.

**`list_profiles()`**
Returns Profile objects for all profiles in the current project. Invalid profiles are filtered out.

**`list_all_profiles()`**
Retrieves profiles from multiple sources in priority order:
1. Parent project profiles
2. CODX-Junior project profiles
3. Current project profiles (can override parents)
4. Built-in base profiles (only if not already defined)

Returns a merged list with duplicates resolved by profile name.

#### Profile Operations

**`read_profile(profile_name) -> Profile`**
Retrieves a specific profile by name from the current project.

**`load_profile(profile_path) -> Profile`**
Loads a profile from disk, including:
- JSON metadata parsing
- Associated markdown content (if available)
- Graceful fallback for invalid JSON or empty files
- Avatar initialization with Gravatar defaults

**`save_profile(profile: Profile)`**
Persists a profile to disk in the modern folder structure:
- Creates profile folder if needed
- Saves JSON metadata (excluding content)
- Saves markdown content separately
- Automatically migrates legacy format profiles

**`delete_profile(profile_name)`**
Removes a profile completely, handling both modern and legacy formats for backward compatibility.

#### Profile Matching and Filtering

**`is_profile_match(profile: Profile, file_path: str) -> bool`**
Checks if a file path matches the profile's `file_match` regex pattern.

**`get_file_profiles_by_file_path(file_path: str)`**
Returns all profiles whose regex patterns match the given file path, with deduplication of linked profiles.

**`get_profiles_by_name(profiles: [])`**
Filters profiles by a list of profile names.

#### Profile Linking and Context

**`get_all_linked_profiles(profile: Profile, seen: set = None) -> List[Profile]`**
Recursively retrieves all profiles linked to a given profile through the `profiles` property, preventing circular references and maintaining order.

**`reduce_linked_profiles(profiles: List[Profile]) -> List[Profile]`**
Deduplicates a list of profiles that may contain linked profiles, ensuring each profile appears only once while preserving order.

**`get_profile_content_context(profile: Profile)`**
Returns a dictionary of context variables available for template substitution in profile content (e.g., project path, project name).

**`get_profile_With_content(profile: Profile)`**
Processes profile content to replace template variables in the format `{{ variable_name }}` with actual values from the profile context.

#### Migration

**`_migrate_profile_to_folder(profile_name: str, old_profile_path: str)`**
Automatically migrates profiles from legacy flat structure to modern folder-based structure, including:
- Moving the profile JSON file
- Moving associated markdown content files

## Utility Functions

### generate_llm_tree()

Generates a text-based directory tree representation for LLM consumption. Features:
- Recursive directory traversal
- Configurable ignore list (`.git`, `__pycache__`, `.vscode`, etc.)
- Sorted output (directories first, then files)
- Files are currently commented out in output

**Parameters:**
- `root_path`: Starting directory path
- `indent`: Current indentation level
- `is_last`: Whether the current item is last in its group
- `ignore_list`: Set of directory/file names to exclude

## Error Handling

The ProfileManager implements graceful error handling:
- Invalid JSON in profile files returns a minimal default Profile with the filename as the name
- Empty profile files are logged as warnings and use defaults
- Missing markdown content files don't cause failures
- File operation exceptions are caught and logged with detailed context

## Profile Model

Profiles extend the `Profile` model from `codx.junior.model.model`, which includes properties such as:
- `name`: Profile identifier
- `content`: Markdown content (stored separately)
- `parsed_content`: Content with template variables resolved
- `file_match`: Regex pattern for file matching
- `profiles`: List of linked profile names
- `avatar`: User avatar URL
- `project_id`: Associated project identifier
- `path`: File system path to the profile

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py, codx/junior/utils/utils.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/api/chatGPTLikeApi.py, codx/junior/chat/chat_engine.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/session.py, codx/junior/mentions/mention_manager.py, codx/junior/wiki/wiki_manager.py