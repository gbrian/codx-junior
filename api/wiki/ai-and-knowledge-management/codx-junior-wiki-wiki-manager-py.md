# WikiManager Code Analysis

## Overview
This is a comprehensive **wiki management system** for the CODX project that automatically generates and maintains project documentation. It integrates AI, dependency analysis, and knowledge management to create organized wiki structures.

## Key Components

### Core Classes

1. **WikiCategory** (Pydantic Model)
   - Defines hierarchical wiki structure
   - Fields: id, title, path, description, keywords, children, files

2. **WikiSettings** (Pydantic Model)
   - Container for wiki configuration
   - Maintains list of categories

3. **WikiManager** (Main Class)
   - Central orchestrator for wiki lifecycle
   - ~600 lines managing creation, building, and compilation

### Primary Responsibilities

| Feature | Methods |
|---------|---------|
| **Initialization** | `__init__`, `_get_ai` |
| **Settings** | `save_wiki_settings`, `load_wiki_settings` |
| **Tree Building** | `create_wiki_tree` |
| **Document Generation** | `create_wiki_document`, `build_wiki_category`, `rebuild_wiki` |
| **Home Page** | `build_wiki_home` |
| **Compilation** | `compile_wiki`, `_update_mkdocs` |
| **Analysis** | `build_dependency_graph`, `build_domains`, `build_wiki_index` |
| **Helpers** | `_assign_category_to_file`, `_prepare_summary_prompt` |

## Workflow Architecture

```
┌─────────────────────────────────────────────────────┐
│ Project Files → Repository Analysis                 │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ AI-Driven Tree Creation (create_wiki_tree)          │
│ • Uses domain hints from dependency graph           │
│ • Prompts AI to organize files into categories      │
├─────────────────────────────────────────────────────┤
│ Saves: wiki_settings.json                           │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ Document Generation (create_wiki_document)          │
│ • Category assignment via AI                        │
│ • Content generation with AI chat                   │
│ • Dependency injection                              │
├─────────────────────────────────────────────────────┤
│ Outputs: {category}/{file}.md                       │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ Home Page Update (build_wiki_home)                  │
│ • Aggregates relevant content                       │
│ • AI determines page importance                     │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│ Wiki Compilation (_update_mkdocs)                   │
│ • Generates mkdocs.yml navigation                   │
│ • AI structures nav hierarchy                       │
└─────────────────────────────────────────────────────┘
```

## AI Integration Pattern

```python
def _ai_chat(self, prompt: str, tags: str = "", clean: bool = True):
    """Cached AI instance with standardized tagging"""
    tags = f"{tags},wiki" if tags else "wiki"
    headers = {"tags": tags}
    messages = self._get_ai().chat(prompt=prompt, headers=headers)
    # Optional markdown cleanup
    if clean and content.startswith("```"):
        content = "\n".join(content.split("\n")[1:-1])
    return messages
```

**AI is used for:**
- Category tree generation
- File-to-category assignment
- Wiki content generation
- Home page relevance filtering
- MkDocs navigation structure
- Domain detection

## Key Features

### 1. **Hierarchical Category System**
```python
category = {
    "title": "Authentication",
    "path": "auth",
    "description": "...",
    "keywords": ["login", "oauth", "jwt"],
    "children": [...],  # Subcategories
    "files": [{"name": "Login", "path": "src/auth.py"}]
}
```

### 2. **Dependency Graph Integration**
```python
def build_dependency_graph(self) -> DependencyGraph:
    graph = DependencyGraph(settings=self.settings)
    graph.build(file_paths)
    graph.save()
    return graph
```
- Used to hint category organization
- Injected into wiki documents
- Powers domain detection

### 3. **Concurrent Processing**
```python
with ThreadPoolExecutor() as executor:
    future_to_file = {
        executor.submit(self.create_wiki_document, f["path"], False): f["path"]
        for f in files
    }
    for future in as_completed(future_to_file):
        file_path = future_to_file[future]
        # Handle result/exception
```

### 4. **Multi-Format Support**
- **VitePress**: Default wiki framework
- **MkDocs**: Alternative with YAML-based configuration

### 5. **Knowledge Management Integration**
```python
self.db = KnowledgeDB(settings=settings)
self.loader = KnowledgeLoader(settings=settings)
```
- Connects to knowledge database
- Indexes wiki content to Milvus
- Supports semantic search

## Configuration Management

### Settings Persistence
```json
{
  "language": "English",
  "mode": "mkdocs",
  "prompt": "Custom wiki instructions",
  "categories": [
    {
      "title": "Core",
      "path": "core",
      "keywords": ["main", "engine"],
      "files": [...]
    }
  ]
}
```

### User Customization
- **Language**: Multi-language wiki support
- **Prompt**: Custom AI instructions
- **Structure**: Hierarchical categorization

## Notable Implementation Details

### File Organization
```python
def _determine_wiki_file_path(self, category, source):
    if category.get("single_file", False):
        return f"{wiki_path}/{category['path']}.md"  # Single file mode
    return f"{wiki_path}/{category['path']}/{slugified_name}.md"  # Multi-file
```

### Category Flattening
```python
def _get_all_categories(self, categories, flattened_list=None, parent=None):
    """Recursively flatten hierarchical tree with slug-based paths"""
    # Preserves parent_path/child_path structure
```

### Changeset Detection
```python
def _create_changeset_document(self, current, updated, source):
    """Summarize wiki changes for home page update"""
    prompt = f"<old_wiki>...{current}</old_wiki>\n<new_wiki>...{updated}</new_wiki>"
    changes = self._ai_chat(prompt=prompt)[-1].content
    return f'<wiki_changes source="{source}">{changes}</wiki_changes>'
```

## Potential Improvements

1. **Error Handling**: More granular exception recovery
2. **Caching**: Cache AI responses for identical prompts
3. **Rate Limiting**: Handle API throttling
4. **Async Operations**: Convert to async/await pattern
5. **Testing**: Add unit tests for category assignment logic
6. **Documentation**: Add docstrings to internal methods

## Dependencies

```
pathlib, slugify, pydantic, yaml, concurrent.futures, aiofiles
+ codx.junior: AI, settings, profiles, knowledge, events
```

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/utils/utils.py, codx/junior/wiki/model.py, codx/junior/ai/__init__.py, codx/junior/events/event_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_graph.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_index.py, codx/junior/model/model.py
**Imported by:** codx/junior/api/wiki.py, codx/junior/background.py, codx/junior/changes/change_manager.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_milvus.py, tests/wiki_manager/test_wiki_manager.py