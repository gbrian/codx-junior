# SmolAgent Package

## Overview

The SmolAgent package provides a small, async-only, easy-to-maintain OpenAI chat agent implementation. It is designed to support streaming and tool integration with built-in protections against stuck tool-call loops.

## Public API

### SmolAgent

The main chat agent class that enables:
- Streaming responses
- Tool support for extended functionality
- Async-only operation for modern Python applications

### ToolLoopError

An exception raised when a stuck tool-call loop is detected, providing safety mechanisms to prevent infinite loops during agent execution.

## Features

- **Lightweight Design**: Small, maintainable codebase optimized for ease of use
- **Async-First**: Built entirely around async/await patterns
- **OpenAI Integration**: Direct integration with OpenAI's chat models
- **Tool Support**: Extensible tool system for agent capabilities
- **Loop Protection**: Automatic detection and handling of stuck tool loops