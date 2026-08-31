# Project Structure Tool

## Overview

The Project Structure Tool is a utility function that provides comprehensive information about the project's file and folder organization. It helps developers understand the project layout and locate components by generating a tree-like representation of all indexed files and folders.

## Features

- **Hierarchical Display**: Presents files and folders in a clear tree structure with visual indicators
- **Flexible Filtering**: Supports maximum depth constraints to limit traversal depth
- **File Metadata**: Optional file size information in human-readable format
- **Detailed Analysis**: Can include additional metadata like file counts per folder
- **Smart Icons**: Uses emoji/file type indicators for quick visual identification
- **Knowledge Base Integration**: Works with the project's knowledge base to access indexed sources

## Main Function

### `project_structure()`

Retrieves and formats the complete project structure with customizable options.

**Parameters:**
- `include_details` (bool, default: False) - Adds additional metadata like file counts
- `max_depth` (Optional[int], default: None) - Limits folder traversal depth (None = unlimited)
- `include_file_sizes` (bool, default: False) - Includes file sizes in bytes for each file
- `settings` (Optional[CODXJuniorSettings]) - Configuration instance injected by SmolAgent runtime

**Returns:**
- Formatted project structure as a string with tree-like representation

**Raises:**
- `ValueError` - If settings parameter is not provided
- `RuntimeError` - If project context or active session is unavailable

**Example Usage:**
```python
result = project_structure(include_details=True)
print(result)
```

Output format:
```
# Project Structure

**Root**: `/path/to/project`

📁 **src**/
├── 📁 **components**/
│   ├── ⚛️ Button.tsx (2.5 KB)
│   └── ⚛️ Card.tsx (1.8 KB)
└── 📁 **utils**/
    └── 📘 helpers.ts (3.2 KB)
📁 **tests**/
└── ⚛️ Button.test.tsx (4.1 KB)
```

## Internal Functions

### `_build_structure()`

Constructs the tree-like representation by accessing the knowledge base and organizing files hierarchically.

**Process Flow:**
1. Retrieves all valid indexed sources from the knowledge base
2. Builds folder tree structure with relative paths
3. Filters results by maximum depth if specified
4. Formats output as tree representation
5. Adds metadata if requested

### `_add_to_tree()`

Adds individual file paths to the tree structure, maintaining the folder hierarchy. Optionally retrieves and stores file size information.

### `_format_tree()`

Converts the tree dictionary into a formatted string representation using tree-drawing characters (├──, └──, │) and appropriate icons for visual clarity.

### `_get_file_icon()`

Returns emoji/icon representations based on file extensions. Supports common file types including:
- Programming languages: Python 🐍, JavaScript 📜, TypeScript 📘, Rust 🦀, Go 🐹
- Frontend: React ⚛️, HTML 🌐, CSS 🎨
- Data: JSON 📦, SQL 🗄️
- Configuration: YAML ⚙️, Dockerfile 🐳
- Documentation: Markdown 📝
- Other files: 📄 (default)

### `_format_file_size()`

Converts byte values into human-readable format (B, KB, MB, GB, TB) with one decimal place precision.

## Requirements

- **Settings Parameter**: The function requires a valid CODXJuniorSettings instance
- **Active Session**: Must have an active SmolAgent runtime session context
- **Knowledge Base**: Project must have indexed sources in the knowledge base

## Error Handling

The tool includes comprehensive error handling:
- Validates settings and session availability
- Gracefully handles missing files or permission issues
- Logs warnings for files where size cannot be determined
- Provides informative error messages for troubleshooting