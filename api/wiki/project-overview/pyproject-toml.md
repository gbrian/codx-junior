# Project Overview

## Project Information

**CODX Junior** is an AI coding assistant project built with Python. The project is currently in beta development status and is licensed under the MIT License.

### Version and Requirements

- **Current Version**: 0.1.0
- **Python Support**: Python 3.11 to <4.0
- **Status**: Development Status :: 4 - Beta

## Core Dependencies

The project utilizes a comprehensive set of dependencies organized into several functional areas:

### AI and Language Processing
- OpenAI integration (>=2.24.0)
- LangChain framework (>=1.1.0) with community extensions (>=0.4.1)
- LangChain Text Splitters (>=1.0.0)
- LLaMA Index (>=0.9.42)
- vLLM (>=0.5.0)
- Sentence Transformers (>=5.6.0)
- PyTorch (>=2.4.0)

### Web Framework and API
- FastAPI (>=0.122.0)
- FastAPI SocketIO (>=0.0.10)
- Flask (>=2.0.2)
- Uvicorn (>=0.38.0)

### Data Processing and Storage
- Milvus vector database (>=2.4.0)
- BeautifulSoup4 for HTML parsing
- Pytesseract for OCR functionality
- Pillow for image processing
- Markdownify and HTML2Text for content conversion
- Pypandoc (>=1.16) for document conversion

### Security
- PyJWT (>=2.10.1) for JWT authentication
- Bcrypt (>=4.3.0) for password hashing

### Utilities
- Python Slugify (>=8.0.1) for URL slug generation
- Watchfiles (>=1.0.4) and Watchdog for file monitoring
- Jinja2 (>=3.0.3) for templating
- Aiofiles (>=24.1.0) for asynchronous file operations
- Python Multipart (>=0.0.20) for form data handling
- Pathspec (>=1.1.1) for path patterns
- FFmpeg (>=1.4) for media processing

### Development and Testing
- Pytest (>=7.3.1) available as optional test dependency

## Build Configuration

The project uses setuptools and wheel for building. The main package is organized under the `codx` namespace with an entry point script `codx-junior` that points to `codx.app:app`.

### Code Quality Standards

The project enforces code quality through Ruff with the following rules:
- F (Pyflakes errors)
- E (Pyright errors)
- W (Warnings)
- I001 (Import sorting)
- Maximum line length: 100 characters
- Target Python version: 3.11

## PyTorch Configuration

The project includes special handling for PyTorch dependencies, configured to use the CPU-only distribution from the official PyTorch index to optimize for environments where GPU support is not required.