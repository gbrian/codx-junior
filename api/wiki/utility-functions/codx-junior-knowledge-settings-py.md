This document defines mappings between file extensions and their corresponding programming languages or content types, primarily for use in a code parsing or language identification context.

## Language Mapping

The `LANGUAGE_FROM_EXTENSION` dictionary provides a mapping from common file extensions to their associated language identifiers. This can be used to determine the programming language of a file based on its extension.

```python /codx/junior/knowledge/settings.py
LANGUAGE_FROM_EXTENSION = {
    "py": "python",
    "java": "java",
    "js": "js",
    "cpp": "cpp",
    "go": "go",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin",
    "rs": "rust",
    "sh": "shell",
    "r": "r",
    "pl": "perl",
    "scala": "scala",
    "ts": "ts",
    "md": "markdown",
    "txt": "text",
    "html": "html",
    "cs": "csharp",
    "cshtml": "html",
    "json": "js",
}
```

## Code Parser Mapping

Similarly, the `CODE_PARSER_FROM_EXTENSION` dictionary maps file extensions to identifiers suitable for code parsers. While largely overlapping with `LANGUAGE_FROM_EXTENSION`, there are slight differences (e.g., "typescript" for `.ts` files).

```python /codx/junior/knowledge/settings.py
CODE_PARSER_FROM_EXTENSION = {
    "py": "python",
    "java": "java",
    "js": "js",
    "cpp": "cpp",
    "go": "go",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin",
    "rs": "rust",
    "sh": "shell",
    "r": "r",
    "pl": "perl",
    "scala": "scala",
    "ts": "typescript",
    "md": "markdown",
    "txt": "text",
    "html": "html",
    "cs": "csharp",
    "cshtml": "html",
    "json": "js",
}
```