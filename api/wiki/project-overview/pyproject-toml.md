# Project Overview

## Project Information

**codx-junior** is an AI coding assistant project, currently in beta development status. The project is built with Python and requires Python version 3.11 or higher (and below 4.0).

**Version:** 0.1.0

## Core Dependencies

The project utilizes a comprehensive stack of dependencies organized into several functional areas:

### AI and Language Model Components
- **OpenAI** (>=2.24.0) - Integration with OpenAI's API
- **LangChain** (>=1.1.0) - Framework for language model chains
- **LangChain Community** (>=0.4.1) - Community extensions for LangChain
- **LangChain Text Splitters** (>=1.0.0) - Text processing utilities
- **LLaMA Index** (>=0.9.42) - Indexing and retrieval framework
- **vLLM** (>=0.5.0) - Large language model inference
- **Sentence Transformers** (>=5.6.0) - Embedding models
- **Torch** (>=2.4.0) - Deep learning framework

### Web Framework and API
- **FastAPI** (>=0.122.0) - Modern web framework for APIs
- **Flask** (>=2.0.2) - Lightweight web framework
- **Uvicorn** (>=0.38.0) - ASGI server implementation
- **Python SocketIO** (>=5.9.0) - WebSocket support

### Data Processing and Storage
- **Pymilvus** (>=2.4.0) - Vector database client
- **BeautifulSoup4** - HTML/XML parsing
- **Markdownify** - Convert HTML to Markdown
- **html2text** - HTML to text conversion
- **PyTesseract** - Optical character recognition
- **Pillow** - Image processing
- **Pypandoc** (>=1.16) - Document conversion

### Utilities
- **Python Slugify** (>=8.0.1) - URL-friendly slug generation
- **PyJWT** (>=2.10.1) - JWT token handling
- **Bcrypt** (>=4.3.0) - Password hashing
- **Watchfiles** (>=1.0.4) - File system monitoring
- **Watchdog** - File system event monitoring
- **Aiofiles** (>=24.1.0) - Asynchronous file operations
- **Jinja2** (>=3.0.3) - Templating engine
- **Pathspec** (>=1.1.1) - Path pattern matching
- **ffmpeg** (>=1.4) - Multimedia processing
- **Python Multipart** (>=0.0.20) - Multipart form data parsing

## Testing Dependencies

Optional test dependencies include:
- **pytest** (>=7.3.1)
- **pytest-mock** (>=3.11.1)
- **pytest-asyncio** (>=0.21.1)

## Build Configuration

- **Build System:** setuptools and wheel
- **Python Target Version:** 3.11
- **Code Quality Tool:** Ruff (with F, E, W, I001 rules enabled)
- **Line Length:** 100 characters

## Package Configuration

The main package entry point is configured as:
```
codx-junior = 'codx.app:app'
```

## Special Dependencies

The project includes a custom PyTorch configuration using the CPU variant from the official PyTorch index to optimize package downloads and installation.