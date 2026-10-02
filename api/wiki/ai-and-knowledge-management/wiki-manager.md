# Wiki Manager Analysis

This is a comprehensive wiki management system for the CODX project. Here's a breakdown of its key components:

## Core Responsibilities

### 1. **Wiki Lifecycle Management**
- **Initialize & Configure**: Manages wiki settings (categories, language, mode)
- **Build & Rebuild**: Creates/updates wiki documents from source files
- **Compile**: Generates final wiki output (MkDocs support)

### 2. **Category System**
- Hierarchical category structure with nested support
- Auto-assignment of files to categories using AI
- Category-level metadata (title, description, keywords)

### 3. **Document Generation**
- Converts source files to wiki markdown via AI summarization
- Updates existing wiki content incrementally
- Generates dependency sections from code analysis
- Creates domain-based documentation pages

### 4. **Home Page Management**
- Intelligently decides what content should appear on landing page
- Maintains coherent high-level overview without implementation details

### 5. **Wiki Compilation**
- MkDocs YAML configuration generation
- AI-powered navigation structure creation
- Automatic sync between file system and config

### 6. **Advanced Features**
- **Dependency Graph**: Builds and analyzes code dependencies
- **Domain Detection**: Groups related files into logical domains
- **Wiki Indexing**: Creates searchable index with vector embeddings
- **Module Documentation**: Generates per-file module pages

## Key Methods

| Method | Purpose |
|--------|---------|
| `create_wiki_tree()` | AI-driven category structure creation |
| `create_wiki_document()` | Generate wiki for single source file |
| `build_wiki_category()` | Bulk generate docs for category (threaded) |
| `rebuild_wiki()` | Full wiki regeneration |
| `build_wiki_home()` | Update landing page |
| `compile_wiki()` | Generate final output |

## Security & Validation

- **Path validation** (`_is_valid_source_path`, `_is_valid_wiki_file_path`)
- **Filename sanitization** (prevents invalid characters, length limits)
- **Path traversal protection** (rejects `..` patterns)
- **Safe file operations** (error handling, logging)

## AI Integration

- Cached AI instance for efficiency
- Configurable language/instructions
- Prompt engineering for documentation quality
- JSON extraction for structured responses

## Threading & Performance

- `ThreadPoolExecutor` for parallel document generation
- Event-based progress tracking
- Efficient caching patterns

This is a well-architected system for maintaining living documentation synchronized with codebase changes.

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/utils/utils.py, codx/junior/wiki/model.py, codx/junior/ai/__init__.py, codx/junior/events/event_manager.py, codx/junior/profiles/profile_manager.py, codx/junior/knowledge/knowledge_db.py, codx/junior/knowledge/knowledge_loader.py, codx/junior/knowledge/knowledge_graph.py, codx/junior/wiki/wiki_domains.py, codx/junior/wiki/wiki_index.py, codx/junior/model/model.py
**Imported by:** codx/junior/api/wiki.py, codx/junior/background.py, codx/junior/changes/change_manager.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_milvus.py, tests/wiki_manager/test_wiki_manager.py